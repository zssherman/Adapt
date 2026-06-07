# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Synthetic 3D radar dataset factory for cell_volume_stats tests."""

import numpy as np
import pytest
import xarray as xr


def make_3d_ds(nz=10, ny=5, nx=5, z_spacing_m=500.0, dx_m=1000.0, dy_m=1000.0):
    """Minimal synthetic 3D radar dataset; reflectivity all-NaN by default."""
    z = np.arange(nz, dtype=float) * z_spacing_m
    y = np.arange(ny, dtype=float) * dy_m
    x = np.arange(nx, dtype=float) * dx_m
    dbz = np.full((nz, ny, nx), np.nan, dtype=float)
    labels = np.zeros((ny, nx), dtype=np.int32)
    return xr.Dataset(
        {"reflectivity": (["z", "y", "x"], dbz), "cell_labels": (["y", "x"], labels)},
        coords={"z": z, "y": y, "x": x},
    )


@pytest.fixture
def make_ds():
    return make_3d_ds
