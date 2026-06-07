# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for the volume/reflectivity/polarimetric aggregate functions."""

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from adapt.modules.cell_volume_stats.module import (  # noqa: E402
    compute_polarimetric_statistics,
    compute_reflectivity_statistics,
    compute_volume_statistics,
)

Z10 = np.arange(10, dtype=float) * 500.0  # 0..4500 m, dz=500


class TestComputeVolumeStatistics:
    def test_full_cell_volume(self):
        # 25 pixels, 10 z-levels, all DBZ defined; dx=dy=1km, dz=500m
        # pixel_area = 1 km^2; voxel = 1 * 500/1000 = 0.5 km^3; total = 25*10*0.5 = 125
        dbz_vol = np.full((10, 25), 30.0)
        out = compute_volume_statistics(dbz_vol, Z10, npixels=25, dx_m=1000.0, dy_m=1000.0)
        assert out["cell_area_km2"] == pytest.approx(25.0)
        assert out["cell_volume_km3"] == pytest.approx(125.0)

    def test_volume_threshold_subset(self):
        # half the column ≥ 40 dBZ → vol_40dbz is half the defined volume
        dbz_vol = np.full((10, 25), 30.0)
        dbz_vol[:5, :] = 45.0  # lower 5 levels are 45 dBZ
        out = compute_volume_statistics(dbz_vol, Z10, npixels=25, dx_m=1000.0, dy_m=1000.0)
        assert out["vol_40dbz_km3"] == pytest.approx(62.5)  # 25*5*0.5


class TestComputeReflectivityStatistics:
    def test_basic_stats_ignore_nan(self):
        dbz_vol = np.array([[40.0, np.nan], [50.0, 30.0]])
        out = compute_reflectivity_statistics(dbz_vol)
        assert out["dbz_max"] == pytest.approx(50.0)
        assert out["dbz_min"] == pytest.approx(30.0)
        assert out["dbz_mean"] == pytest.approx(40.0)


class TestComputePolarimetricStatistics:
    def test_named_stats(self):
        vol = np.array([1.0, 2.0, 3.0])
        out = compute_polarimetric_statistics(vol, "zdr")
        assert out["zdr_mean"] == pytest.approx(2.0)
        assert out["zdr_max"] == pytest.approx(3.0)
        assert out["zdr_min"] == pytest.approx(1.0)
