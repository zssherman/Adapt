# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Unit tests for adapt.utils.time.normalize_time_scalar.

All tests use synthetic numpy/Python scalars — no radar files, no IO.
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from adapt.utils.time import (
    from_scan_iso,
    normalize_time_scalar,
    to_scan_iso,
    to_scan_unix,
)

pytestmark = pytest.mark.unit


class TestToScanIso:
    """Canonical scan-time string — the cross-table join key (matches _to_iso)."""

    def test_naive_datetime_treated_as_utc(self):
        assert to_scan_iso(datetime(2024, 1, 1, 12, 0, 0)) == "2024-01-01T12:00:00Z"

    def test_aware_utc_datetime(self):
        assert to_scan_iso(datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)) == "2024-01-01T12:00:00Z"

    def test_pandas_timestamp(self):
        assert to_scan_iso(pd.Timestamp("2024-01-01T12:00:00")) == "2024-01-01T12:00:00Z"

    def test_numpy_datetime64(self):
        assert to_scan_iso(np.datetime64("2024-01-01T12:00:00")) == "2024-01-01T12:00:00Z"


class TestFromScanIso:
    """Inverse of to_scan_iso — parse the canonical string back to a UTC datetime."""

    def test_parses_to_aware_utc(self):
        dt = from_scan_iso("2024-01-01T12:00:00Z")
        assert dt == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    def test_round_trips(self):
        original = datetime(2024, 6, 15, 8, 30, 0, tzinfo=UTC)
        assert from_scan_iso(to_scan_iso(original)) == original


class TestToScanUnix:
    """Machine-readable epoch seconds — the SAME instant as to_scan_iso, always."""

    def test_unix_seconds_for_known_utc(self):
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert to_scan_unix(dt) == int(dt.timestamp())

    def test_naive_treated_as_utc(self):
        assert to_scan_unix(datetime(2024, 1, 1, 12, 0, 0)) == int(
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC).timestamp()
        )

    def test_iso_and_unix_describe_same_instant(self):
        dt = datetime(2024, 6, 15, 8, 30, 0)
        assert from_scan_iso(to_scan_iso(dt)).timestamp() == to_scan_unix(dt)

    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2024-01-01T12:00:00")
        assert to_scan_unix(ts) == int(datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC).timestamp())


class TestNormalizeTimeScalar:
    def test_python_datetime_passthrough(self):
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = normalize_time_scalar(dt)
        assert result == dt

    def test_numpy_datetime64_unwrapped_to_python(self):
        val = np.datetime64("2025-06-15T08:00:00")
        result = normalize_time_scalar(val)
        # numpy datetime64.item() returns a Python datetime
        assert isinstance(result, datetime)

    def test_single_element_array_unwrapped(self):
        arr = np.array(["2025-03-01T06:00:00"], dtype="datetime64[s]")
        result = normalize_time_scalar(arr)
        assert not isinstance(result, np.ndarray)

    def test_size_1_array_with_ndim_gt_1(self):
        arr = np.array([["2025-01-01T00:00:00"]], dtype="datetime64[s]")
        result = normalize_time_scalar(arr)
        assert not isinstance(result, np.ndarray)

    def test_nat_returns_none(self):
        """NaT.item() returns None; normalize_time_scalar propagates that."""
        result = normalize_time_scalar(np.datetime64("NaT"))
        assert result is None

    def test_plain_integer_passthrough(self):
        result = normalize_time_scalar(42)
        assert result == 42

    def test_cftime_converted_to_datetime(self):
        """cftime objects are converted to Python datetime with UTC timezone."""
        pytest.importorskip("cftime")
        import cftime

        cf = cftime.DatetimeGregorian(2025, 6, 15, 10, 30, 0)
        result = normalize_time_scalar(cf)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_numpy_scalar_without_item_method(self):
        """Objects without .item() are returned as-is."""

        class FakeScalar:
            pass

        obj = FakeScalar()
        result = normalize_time_scalar(obj)
        assert result is obj
