# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""NEXRAD pipeline assembly via ModuleRegistry + GraphBuilder.

This module shows how the controller builds the full processing pipeline
from registered modules. It is the bridge between the module system and
the graph execution engine.

The pipeline is assembled once at startup; the graph executor runs it
once per radar file.

Usage::

    pipeline = NexradPipeline(config)
    result = pipeline.process_file(nexrad_file_path, repository=repo)
    cells_df = result["cell_stats"]
"""

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

from adapt.execution.graph.builder import GraphBuilder
from adapt.execution.graph.executor import GraphExecutor
from adapt.execution.module_registry import registry

if TYPE_CHECKING:
    from adapt.configuration.schemas.internal import InternalConfig
    from adapt.persistence.repository import DataRepository

logger = logging.getLogger(__name__)

_DEFAULTS_YAML = Path(__file__).parent.parent / "configuration" / "defaults.yaml"


def _ensure_modules_registered(extensions: list[str] | None = None) -> None:
    """Import module files listed in config/defaults.yaml plus any user extensions.

    Each entry under ``pipeline.modules`` is a Python module path.
    Importing it triggers the ``registry.register()`` call at module level.
    To add a core module: add one line to defaults.yaml.
    To add an extension: pass its dotted import path via ``extensions``.
    """
    try:
        with open(_DEFAULTS_YAML) as f:
            cfg = yaml.safe_load(f)
        module_paths = cfg.get("pipeline", {}).get("modules", [])
    except Exception as e:
        logger.warning("Could not read defaults.yaml (%s); falling back to hardcoded list", e)
        module_paths = [
            "adapt.execution.nodes.ingest",
            "adapt.execution.nodes.detection",
            "adapt.execution.nodes.projection",
            "adapt.execution.nodes.analysis",
            "adapt.execution.nodes.tracking",
        ]

    for path in module_paths:
        try:
            importlib.import_module(path)
            logger.debug("Registered core module from: %s", path)
        except Exception as e:
            logger.error("Failed to import core module '%s': %s", path, e)

    for path in extensions or []:
        try:
            importlib.import_module(path)
            logger.info("Registered extension module from: %s", path)
        except Exception as e:
            raise ImportError(f"Failed to load extension module '{path}': {e}") from e


def resolve_enabled_modules(
    all_modules: list,
    modules: list[str] | None = None,
    only: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list:
    """Filter ``all_modules`` to the enabled set, preserving order.

    Precedence (CLI over file): start from every module; if ``modules`` (the config
    allowlist) is given, restrict to it; then ``only`` restricts further (exact set)
    or ``exclude`` subtracts. Every referenced name must be a real module. After
    filtering, validates that no enabled module needs an input produced solely by a
    disabled module — raising a clear error rather than failing opaquely at runtime.

    Parameters
    ----------
    all_modules : list
        All registered module instances (each with ``name``/``inputs``/``outputs``).
    modules, only, exclude : list[str], optional
        Config allowlist, ``--only`` set, and ``--not`` set respectively.
    """
    by_name = {m.name: m for m in all_modules}
    for label, names in (("modules", modules), ("--only", only), ("--not", exclude)):
        for n in names or []:
            if n not in by_name:
                raise ValueError(
                    f"Unknown module '{n}' in {label}. Available: {', '.join(by_name)}"
                )

    enabled = set(by_name)
    if modules is not None:
        enabled = set(modules)
    if only:
        enabled = set(only)
    elif exclude:
        enabled -= set(exclude)

    producer: dict[str, str] = {}
    for m in all_modules:
        for out in m.outputs:
            producer[out] = m.name
    for m in all_modules:
        if m.name not in enabled:
            continue
        for inp in m.inputs:
            src = producer.get(inp)
            if src is not None and src not in enabled:
                raise ValueError(
                    f"Module '{m.name}' needs input '{inp}' produced by disabled "
                    f"module '{src}'. Enable '{src}' or also disable '{m.name}'."
                )

    return [m for m in all_modules if m.name in enabled]


class NexradPipeline:
    """Graph-based NEXRAD processing pipeline.

    Assembles the execution graph from the module registry and runs it
    once per radar file. Module instances persist across files so that
    stateful modules (e.g. ProjectionModule with frame history) work
    correctly.

    Parameters
    ----------
    config : InternalConfig
        Runtime configuration forwarded to modules via the context dict.
    output_dirs : dict, optional
        Output directory mapping forwarded to modules via context.

    Example::

        pipeline = NexradPipeline(config, output_dirs=dirs)
        result = pipeline.process_file("KLOT20240518_123456_V06", repo)
        print(result["cell_stats"].head())
    """

    def __init__(
        self,
        config: "InternalConfig",
        output_dirs: dict | None = None,
    ) -> None:
        self.config = config
        self.output_dirs = output_dirs or {}

        _ensure_modules_registered()

        # Build a local registry with only NEXRAD pipeline modules
        # (avoids polluting the global registry if it already has modules)
        local_modules = registry.create_modules()
        self._nodes = GraphBuilder(local_modules).build()
        self._executor = GraphExecutor(self._nodes)
        logger.info(
            "NexradPipeline assembled: %s",
            " → ".join(n.name for n in self._nodes),
        )

    def process_file(
        self,
        nexrad_file: str,
        repository: Optional["DataRepository"] = None,
    ) -> dict:
        """Run the full processing graph for a single NEXRAD file.

        Parameters
        ----------
        nexrad_file : str
            Path to the NEXRAD Level-II file.
        repository : DataRepository, optional
            If provided, analysis results are persisted automatically.

        Returns
        -------
        dict
            Final context dict with keys: grid_ds, grid_ds_2d, segmented_ds,
            projected_ds, cell_stats, scan_time.
        """
        context = {
            "nexrad_file": nexrad_file,
            "config": self.config,
            "output_dirs": self.output_dirs,
        }
        if repository is not None:
            context["repository"] = repository

        return self._executor.run(context)
