# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Dynamic default-config assembly from the module registry.

The complete default configuration is built bottom-up at runtime:

- shared / core defaults come from ``ParamConfig`` (global section + the five
  legacy core module sections), and
- each registered **extension** module (``pipeline_phase >= 3``) contributes its
  own owned params under ``module_params[name]`` via ``module.default_params()``.

A new module added the standard way (an extension declaring ``config_class``)
therefore appears in the generated config automatically — no edit to any central
file. Core (phase-0) modules stay represented as ``ParamConfig`` sections in this
stage; migrating them out is a separate, behaviour-preserving step.
"""

import typing
from typing import Any

from pydantic import BaseModel

from adapt.configuration.schemas.param import ParamConfig
from adapt.execution.module_registry import registry
from adapt.execution.pipeline_builder import _ensure_modules_registered

# Modules at or above this phase configure themselves through ``module_params``
# rather than a hand-written ParamConfig section.
_DYNAMIC_PHASE = 3


def assemble_default_config(extensions: list[str] | None = None) -> dict[str, Any]:
    """Assemble the complete default config for a pipeline.

    Imports the pipeline's modules (core from ``defaults.yaml`` plus any
    ``extensions``), then unions ``ParamConfig`` defaults with each extension's
    owned ``default_params()``.

    Parameters
    ----------
    extensions : list[str], optional
        Dotted import paths of extension module nodes to include.

    Returns
    -------
    dict
        Default config dict (``by_alias`` so ``global`` not ``global_``), with
        ``module_params[name]`` populated for every registered extension that
        declares owned params, and ``extensions`` echoed back when provided.
    """
    _ensure_modules_registered(extensions)

    base: dict[str, Any] = ParamConfig().model_dump(by_alias=True)

    module_params: dict[str, dict[str, Any]] = {}
    for name in registry.list_modules():
        module = registry.get(name)
        if module.pipeline_phase < _DYNAMIC_PHASE:
            continue
        params = module.default_params()
        if params:
            module_params[name] = params

    if module_params:
        base["module_params"] = module_params
    if extensions:
        base["extensions"] = list(extensions)

    # Surface the full pipeline as a visible, commentable module list (node names
    # in registration order). All run by default; commenting a line skips that stage.
    return {"modules": registry.list_modules(), **base}


def assemble_descriptions(extensions: list[str] | None = None) -> dict[str, Any]:
    """Description tree mirroring ``assemble_default_config`` for YAML comments.

    Core descriptions come from ``ParamConfig`` ``Field`` metadata (recursively);
    ``module_params[name]`` comes from each extension's ``param_descriptions()``.
    """
    _ensure_modules_registered(extensions)

    desc: dict[str, Any] = _model_descriptions(ParamConfig)

    module_desc: dict[str, dict[str, str]] = {}
    for name in registry.list_modules():
        module = registry.get(name)
        if module.pipeline_phase < _DYNAMIC_PHASE:
            continue
        d = {k: v for k, v in module.param_descriptions().items() if v}
        if d:
            module_desc[name] = d

    if module_desc:
        desc["module_params"] = module_desc

    # Per-module comments for the ``modules:`` list, plus a leading header block.
    # ``_header`` is a reserved key consumed by the YAML writer (not a module name).
    desc["modules"] = {
        "_header": (
            "Pipeline modules — all run by default, in dependency order.\n"
            "Comment out a line (or use --not NAME) to skip that stage;\n"
            "use --only A,B to run just a subset."
        ),
        **{name: registry.get(name).module_summary() for name in registry.list_modules()},
    }

    return desc


def _nested_model(annotation: Any) -> type[BaseModel] | None:
    """Return the nested pydantic model in an annotation (unwrapping Optional)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def _model_descriptions(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Recursively map a model's fields to descriptions, keyed by alias."""
    out: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        key = field.alias or name
        nested = _nested_model(field.annotation)
        if nested is not None:
            out[key] = _model_descriptions(nested)
        elif field.description:
            out[key] = field.description
    return out
