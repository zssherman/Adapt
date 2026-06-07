# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests that ProjectionModule reads frame history from scan_history context key.

The old interface used dataset_history (list of (filepath, ds) tuples).
The new interface uses scan_history (list of context dicts, each with segmented_ds).
"""

from datetime import UTC, datetime

import numpy as np
import pytest
import xarray as xr

pytestmark = pytest.mark.unit


def _make_labeled_ds(t: str) -> xr.Dataset:
    data = np.array([[0, 40, 40, 0], [0, 40, 40, 0], [0, 0, 0, 0], [0, 0, 0, 0]], dtype=np.float32)
    labels = np.array([[0, 1, 1, 0], [0, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]], dtype=np.int32)
    ds = xr.Dataset(
        {"reflectivity": (("y", "x"), data), "cell_labels": (("y", "x"), labels)},
        coords={"y": range(4), "x": range(4)},
    )
    return ds.assign_coords(time=np.datetime64(t))


def _make_scan_ctx(t: str) -> dict:
    """Build a scan history entry as the processor would produce it."""
    return {
        "segmented_ds": _make_labeled_ds(t),
        "scan_time": datetime.fromisoformat(t).replace(tzinfo=UTC),
        "nexrad_file": f"KLOT_{t.replace(':', '').replace('-', '')}_V06",
    }


class TestProjectionNodeScanHistory:
    def test_projection_module_reads_scan_history_not_dataset_history(self, make_projection_config):
        """ProjectionModule.run() must accept scan_history, not dataset_history."""
        from adapt.execution.nodes.projection import ProjectionModule

        scan_history = [
            _make_scan_ctx("2024-01-01T00:00:00"),
            _make_scan_ctx("2024-01-01T00:05:00"),
        ]
        ctx = {
            "scan_history": scan_history,
            "segmented_ds": _make_labeled_ds("2024-01-01T00:05:00"),
            "projection_config": make_projection_config(),
        }

        module = ProjectionModule()
        result = module.run(ctx)

        assert "projected_ds" in result

    def test_projection_module_declares_scan_history_as_input(self):
        """ProjectionModule.inputs must list scan_history, not dataset_history."""
        from adapt.execution.nodes.projection import ProjectionModule

        assert "scan_history" in ProjectionModule.inputs
        assert "dataset_history" not in ProjectionModule.inputs

    def test_projection_module_validates_scan_history_input(self, make_projection_config):
        """ProjectionModule registers check_scan_history as an input contract."""
        from adapt.contracts import check_scan_history
        from adapt.execution.nodes.projection import ProjectionModule

        assert "scan_history" in ProjectionModule.input_contracts
        assert ProjectionModule.input_contracts["scan_history"] is check_scan_history

    def test_projection_module_raises_without_scan_history(self, make_projection_config):
        """ProjectionModule raises KeyError when scan_history missing from context."""
        from adapt.execution.nodes.projection import ProjectionModule

        ctx = {
            "segmented_ds": _make_labeled_ds("2024-01-01T00:05:00"),
            "projection_config": make_projection_config(),
            # scan_history intentionally omitted
        }
        module = ProjectionModule()
        with pytest.raises(KeyError):
            module.run(ctx)
