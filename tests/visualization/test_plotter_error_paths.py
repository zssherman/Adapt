# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Regression tests for plotter error-path bugs.

Bug 1: plot_from_netcdf raised AttributeError: 'NoneType' object has no attribute
'data_vars' when a file could not be opened after all retries, because seg_ds
stayed None and the assert was absent. Now raises FileNotFoundError/RuntimeError
with a clear message.
"""

import pytest

pytestmark = pytest.mark.unit


def test_plot_from_netcdf_raises_file_not_found_for_missing_file(tmp_path):
    """plot_from_netcdf must raise FileNotFoundError — not AttributeError — for a
    path that never exists.  Before the assert-guard fix, reaching the data_vars
    access on a None seg_ds gave AttributeError with no useful context."""
    import matplotlib

    matplotlib.use("Agg")
    from adapt.visualization.plotter import RadarPlotter

    plotter = RadarPlotter()
    missing = tmp_path / "nonexistent.nc"

    with pytest.raises(FileNotFoundError):
        plotter.plot_from_netcdf(missing)


def test_plot_from_netcdf_raises_runtime_error_for_corrupt_file(tmp_path):
    """A file that exists but cannot be opened as NetCDF raises RuntimeError
    (not AttributeError from a None seg_ds)."""
    import matplotlib

    matplotlib.use("Agg")
    from adapt.visualization.plotter import RadarPlotter

    bad_nc = tmp_path / "bad.nc"
    bad_nc.write_bytes(b"not a netcdf file")

    plotter = RadarPlotter()
    with pytest.raises(RuntimeError, match="Failed to open NetCDF"):
        plotter.plot_from_netcdf(bad_nc)
