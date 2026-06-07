# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for the per-profile (1D column) science functions. Hand-calculated."""

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from adapt.modules.cell_volume_stats.module import (  # noqa: E402
    analyze_profile,
    compute_region_score,
    find_connected_regions,
    merge_vertical_gaps,
    select_dominant_region,
)

# z at 0, 500, 1000, 1500, 2000, 2500 m
Z6 = np.arange(6, dtype=float) * 500.0


class TestMergeVerticalGaps:
    def test_gap_within_tolerance_is_bridged(self):
        # one False level (500 m gap) between two True regions, tol 500 → merged
        mask = np.array([True, False, True, False, False, False])
        out = merge_vertical_gaps(mask, Z6, gap_tolerance_m=500.0)
        assert out[1]  # the single-level gap is filled

    def test_gap_beyond_tolerance_preserved(self):
        # two False levels (1000 m gap) between True regions, tol 500 → not merged
        mask = np.array([True, False, False, True, False, False])
        out = merge_vertical_gaps(mask, Z6, gap_tolerance_m=500.0)
        assert not out[1] and not out[2]


class TestFindConnectedRegions:
    def test_single_run_one_region(self):
        mask = np.array([False, True, True, False, False, False])
        labels = find_connected_regions(mask)
        assert labels.max() == 1

    def test_two_runs_two_regions(self):
        mask = np.array([True, True, False, True, True, False])
        labels = find_connected_regions(mask)
        assert labels.max() == 2


class TestComputeRegionScore:
    def test_score_sum_excess_times_dz(self):
        # DBZ 35 at two levels, threshold 30, dz 500 → (5*500)+(5*500) = 5000
        dbz = np.array([np.nan, 35.0, 35.0, np.nan, np.nan, np.nan])
        region = np.array([False, True, True, False, False, False])
        score = compute_region_score(dbz, region, Z6, threshold=30.0)
        assert score == pytest.approx(5000.0)


class TestSelectDominantRegion:
    def test_picks_higher_score_region(self):
        # region A (label 1): two levels of 35 dBZ (score 5000)
        # region B (label 2): one level of 45 dBZ (score (45-30)*500 = 7500) → dominant
        dbz = np.array([35.0, 35.0, np.nan, 45.0, np.nan, np.nan])
        labels = np.array([1, 1, 0, 2, 0, 0])
        assert select_dominant_region(dbz, labels, Z6, threshold=30.0) == 2

    def test_returns_zero_when_no_regions(self):
        dbz = np.full(6, np.nan)
        labels = np.zeros(6, dtype=int)
        assert select_dominant_region(dbz, labels, Z6, threshold=30.0) == 0


class TestAnalyzeProfile:
    def test_single_layer_top_bottom(self):
        # DBZ above threshold at z=500 and z=1000
        dbz = np.array([np.nan, 40.0, 40.0, np.nan, np.nan, np.nan])
        out = analyze_profile(dbz, Z6, threshold=30.0, gap_tolerance_m=0.0)
        assert out["bottom_height"] == pytest.approx(500.0)
        assert out["top_height"] == pytest.approx(1000.0)
        assert out["nlayers"] == 1
        assert out["multilayer"] is False

    def test_multilayer(self):
        # two separated regions (gap of 1000 m, no bridging)
        dbz = np.array([40.0, np.nan, np.nan, 40.0, np.nan, np.nan])
        out = analyze_profile(dbz, Z6, threshold=30.0, gap_tolerance_m=0.0)
        assert out["nlayers"] == 2
        assert out["multilayer"] is True

    def test_no_echo_returns_nan(self):
        dbz = np.array([10.0, 10.0, 10.0, np.nan, np.nan, np.nan])
        out = analyze_profile(dbz, Z6, threshold=30.0, gap_tolerance_m=0.0)
        assert out["nlayers"] == 0
        assert out["multilayer"] is False
        assert np.isnan(out["top_height"])
        assert np.isnan(out["depth"])
