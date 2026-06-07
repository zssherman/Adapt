# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for scan_history contract.

Validates the rolling-window history list passed to multi-scan modules.
Each entry in scan_history is a context dict from a completed prior scan.
"""

from datetime import UTC, datetime

import numpy as np
import pytest
import xarray as xr

pytestmark = pytest.mark.unit

from adapt.contracts import ContractViolation, check_scan_history  # noqa: E402


def _valid_scan_ctx() -> dict:
    """Minimal valid scan context dict as stored in history."""
    ds = xr.Dataset(
        {"cell_labels": (("y", "x"), np.zeros((4, 4), dtype=np.int32))},
        coords={"x": range(4), "y": range(4)},
    )
    return {"segmented_ds": ds, "scan_time": datetime(2024, 1, 1, tzinfo=UTC)}


class TestScanHistoryContract:
    """check_scan_history validates the rolling scan history list."""

    def test_passes_with_single_valid_entry(self):
        """Contract passes with one well-formed scan context."""
        check_scan_history([_valid_scan_ctx()])

    def test_passes_with_two_valid_entries(self):
        """Contract passes with two well-formed scan contexts."""
        check_scan_history([_valid_scan_ctx(), _valid_scan_ctx()])

    def test_fails_on_empty_list(self):
        """Contract fails when history list is empty."""
        with pytest.raises(ContractViolation, match="non-empty"):
            check_scan_history([])

    def test_fails_when_not_a_list(self):
        """Contract fails when history is not a list."""
        with pytest.raises(ContractViolation, match="list"):
            check_scan_history("not a list")

    def test_fails_when_entry_is_not_dict(self):
        """Contract fails when a history entry is not a dict."""
        with pytest.raises(ContractViolation, match=r"scan_history\[0\].*dict"):
            check_scan_history(["not a dict"])

    def test_fails_when_segmented_ds_missing(self):
        """Contract fails when a history entry lacks segmented_ds."""
        ctx = _valid_scan_ctx()
        del ctx["segmented_ds"]
        with pytest.raises(ContractViolation, match="segmented_ds"):
            check_scan_history([ctx])

    def test_fails_when_scan_time_missing(self):
        """Contract fails when a history entry lacks scan_time."""
        ctx = _valid_scan_ctx()
        del ctx["scan_time"]
        with pytest.raises(ContractViolation, match="scan_time"):
            check_scan_history([ctx])

    def test_fails_on_second_entry_if_invalid(self):
        """Contract validates every entry, not just the first."""
        bad_ctx = _valid_scan_ctx()
        del bad_ctx["scan_time"]
        with pytest.raises(ContractViolation, match=r"scan_history\[1\]"):
            check_scan_history([_valid_scan_ctx(), bad_ctx])
