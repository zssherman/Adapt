# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Regression tests for missing declared dependencies.

Bug: duckdb was imported unconditionally in adapt.api.client but was absent
from pyproject.toml dependencies. A fresh `pip install arm-adapt` omitted it,
causing ModuleNotFoundError at dashboard startup.
"""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def _declared_deps() -> list[str]:
    with open(_PYPROJECT, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["dependencies"]


def test_duckdb_is_declared_dependency():
    """duckdb must be in pyproject.toml dependencies.

    adapt.api.client imports duckdb at module level; omitting it from
    the package metadata means pip install arm-adapt silently skips it
    and the dashboard fails with ModuleNotFoundError on first use.
    """
    deps = _declared_deps()
    declared_names = {d.split("[")[0].split(">=")[0].split("==")[0].strip().lower() for d in deps}
    assert "duckdb" in declared_names, (
        "duckdb is missing from pyproject.toml [project.dependencies]. "
        "adapt.api.client imports it unconditionally — it must be declared."
    )
