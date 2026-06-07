# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests that the 3D gridded NetCDF becomes a queryable catalog artifact.

The loader writes the 3D NetCDF to disk; the ingest node returns its path; the
processor registers it as a gridded3d artifact so enrich modules (via the
processor reader) can open it by scan_time.
"""

import queue
from datetime import UTC, datetime

import numpy as np
import pytest
import xarray as xr

from adapt.persistence.repository import ProductType
from adapt.runtime.processor import RadarProcessor

pytestmark = [pytest.mark.unit, pytest.mark.pipeline]


def _make_proc(pipeline_config, pipeline_output_dirs, test_repository):
    return RadarProcessor(
        queue.Queue(),
        pipeline_config,
        pipeline_output_dirs,
        repository=test_repository,
    )


def _write_grid_nc(path) -> None:
    ds = xr.Dataset(
        {"reflectivity": (("z", "y", "x"), np.zeros((3, 4, 4), dtype=np.float32))},
        coords={"z": [0, 1000, 2000], "y": range(4), "x": range(4)},
    )
    ds.to_netcdf(path)


class TestIngestDeclaresGridPath:
    def test_load_module_declares_grid_nc_path_output(self):
        from adapt.execution.nodes.ingest import LoadModule

        assert "grid_nc_path" in LoadModule.outputs


class TestProcessorRegistersGrid3D:
    def test_grid3d_registered_and_queryable(
        self, tmp_path, pipeline_config, pipeline_output_dirs, test_repository
    ):
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)

        nc_file = tmp_path / "scan_grid.nc"
        _write_grid_nc(nc_file)
        scan_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        proc._save_results({"grid_nc_path": str(nc_file)}, scan_time)

        artifacts = test_repository.query(
            product_type=ProductType.GRIDDED_NC, time_range=(scan_time, scan_time)
        )
        assert len(artifacts) == 1
        ds = test_repository.open_dataset(artifacts[0]["artifact_id"])
        assert "reflectivity" in ds.data_vars

    def test_missing_grid_file_is_skipped(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        scan_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Path points at a non-existent file → no registration, no crash
        proc._save_results({"grid_nc_path": "/nonexistent/grid.nc"}, scan_time)

        artifacts = test_repository.query(
            product_type=ProductType.GRIDDED_NC, time_range=(scan_time, scan_time)
        )
        assert artifacts == []
