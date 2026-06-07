# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for the cell_volume_stats output contract (empty-tolerant)."""

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

from adapt.contracts import ContractViolation, check_cell_volume_stats  # noqa: E402


def _valid_row() -> dict:
    return {
        "run_id": "R1",
        "scan_time": "2024-01-01T00:00:00Z",
        "cell_uid": "a",
        "cell_label": 1,
        "cell_area_km2": 25.0,
        "cell_volume_km3": 125.0,
        "dbz_max": 50.0,
        "dbz_mean": 40.0,
    }


class TestCellVolumeStatsContract:
    def test_passes_with_required_columns(self):
        check_cell_volume_stats(pd.DataFrame([_valid_row()]))

    def test_empty_dataframe_is_tolerated(self):
        # The no-cells / no-grid path returns an empty frame — must NOT raise (Fix B).
        check_cell_volume_stats(pd.DataFrame())

    def test_missing_required_column_raises(self):
        row = _valid_row()
        del row["cell_volume_km3"]
        with pytest.raises(ContractViolation, match="cell_volume_km3"):
            check_cell_volume_stats(pd.DataFrame([row]))
