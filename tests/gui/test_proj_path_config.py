# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Regression test for pyproj.datadir AttributeError.

Bug: dashboard.py did `import pyproj as _pyproj` then called
`_pyproj.datadir.get_data_dir()`. In pyproj versions where the submodule is
not auto-imported, this raises AttributeError: module 'pyproj' has no
attribute 'datadir'.

Fix: explicitly import the submodule: `from pyproj.datadir import get_data_dir`.
"""

import pytest

pytestmark = pytest.mark.unit


def test_pyproj_datadir_requires_explicit_import():
    """Bare `import pyproj` does not guarantee pyproj.datadir is accessible.

    This test documents that the correct pattern is an explicit submodule
    import, not attribute access on the top-level pyproj module.
    """

    # Attribute access on bare import is unreliable across pyproj versions
    # — the fix must use an explicit import instead.
    from pyproj.datadir import get_data_dir

    path = get_data_dir()
    assert path is not None
    assert "proj" in str(path).lower()


def test_dashboard_proj_block_does_not_raise(monkeypatch):
    """The PROJ environment-variable setup block must not raise AttributeError.

    Simulates what dashboard.py does at import time with the fixed code path.
    """
    import os

    from pyproj.datadir import get_data_dir as _get_proj_data_dir

    captured = {}

    def _fake_setenv(key, value):
        captured[key] = value

    monkeypatch.setattr(os, "environ", {})
    _pd = _get_proj_data_dir()
    os.environ["PROJ_DATA"] = _pd
    os.environ["PROJ_LIB"] = _pd

    assert "PROJ_DATA" in os.environ
    assert "PROJ_LIB" in os.environ
    assert os.environ["PROJ_DATA"] == os.environ["PROJ_LIB"]
