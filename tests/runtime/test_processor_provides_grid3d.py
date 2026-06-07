# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests that the processor reads the 3D grid and injects it into the enrich
context only for modules that declare `grid_ds_3d` as an input.

Modules never touch storage — the processor reads the registered gridded3d
artifact and hands the dataset to enrich modules that need it.
"""

import queue
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from adapt.execution.module_registry import registry
from adapt.modules.base import BaseModule
from adapt.persistence.repository import ProductType
from adapt.runtime.processor import RadarProcessor

pytestmark = [pytest.mark.unit, pytest.mark.pipeline]


class _NeedsGrid3D(BaseModule):
    name = "needs_grid3d"
    pipeline_phase = 3
    inputs = ["run_id", "scan_time", "grid_ds_3d"]
    outputs = ["needs_grid3d_rows"]

    def run(self, context):
        return {"needs_grid3d_rows": pd.DataFrame()}


class _NoGrid3D(BaseModule):
    name = "no_grid3d"
    pipeline_phase = 3
    inputs = ["run_id", "scan_time"]
    outputs = ["no_grid3d_rows"]

    def run(self, context):
        return {"no_grid3d_rows": pd.DataFrame()}


def _register_grid3d(repository, scan_time, tmp_path):
    nc = tmp_path / "g.nc"
    xr.Dataset(
        {"reflectivity": (("z", "y", "x"), np.zeros((2, 3, 3), dtype=np.float32))},
        coords={"z": [0, 2000], "y": range(3), "x": range(3)},
    ).to_netcdf(nc)
    repository.register_artifact(
        product_type=ProductType.GRIDDED_NC,
        file_path=str(nc),
        scan_time=scan_time,
        producer="ingest",
    )


def _make_proc(pipeline_config, pipeline_output_dirs, test_repository):
    return RadarProcessor(
        queue.Queue(), pipeline_config, pipeline_output_dirs, repository=test_repository
    )


class TestProcessorProvidesGrid3D:
    def test_injects_grid_ds_3d_when_module_declares_it(
        self, tmp_path, pipeline_config, pipeline_output_dirs, test_repository
    ):
        registry.register(_NeedsGrid3D)
        try:
            proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
            scan_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            _register_grid3d(test_repository, scan_time, tmp_path)

            ctx = proc._build_enrich_context({}, scan_time)
            assert "grid_ds_3d" in ctx
            assert "reflectivity" in ctx["grid_ds_3d"].data_vars
        finally:
            registry.unregister("needs_grid3d")

    def test_grid_found_when_artifact_aware_but_context_scan_time_naive(
        self, tmp_path, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """Production case: _save_results registers the artifact with a tz-aware
        scan_time (+00:00); the enrich read must still find it when handed the
        original naive scan_time. Both sides normalize to UTC."""
        registry.register(_NeedsGrid3D)
        try:
            proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
            aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            _register_grid3d(test_repository, aware, tmp_path)  # stored as +00:00

            naive = datetime(2024, 1, 1, 12, 0, 0)  # what process_file passed pre-fix
            ctx = proc._build_enrich_context({}, naive)
            assert "grid_ds_3d" in ctx
        finally:
            registry.unregister("needs_grid3d")

    def test_no_grid_ds_3d_when_not_declared(
        self, tmp_path, pipeline_config, pipeline_output_dirs, test_repository
    ):
        registry.register(_NoGrid3D)
        try:
            # Disable the default grid-consuming module so the only enabled phase-3
            # module is _NoGrid3D, which does not declare grid_ds_3d.
            cfg = pipeline_config.model_copy(update={"exclude_modules": ["cell_volume_stats"]})
            proc = _make_proc(cfg, pipeline_output_dirs, test_repository)
            scan_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            _register_grid3d(test_repository, scan_time, tmp_path)

            ctx = proc._build_enrich_context({}, scan_time)
            assert "grid_ds_3d" not in ctx
        finally:
            registry.unregister("no_grid3d")

    def test_no_crash_when_grid_missing_but_declared(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        registry.register(_NeedsGrid3D)
        try:
            proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
            scan_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            # No gridded3d registered → no key, no crash
            ctx = proc._build_enrich_context({}, scan_time)
            assert "grid_ds_3d" not in ctx
        finally:
            registry.unregister("needs_grid3d")
