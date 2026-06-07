# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Unit tests for resolve_enabled_modules — pure module-selection logic."""

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

from adapt.execution.pipeline_builder import resolve_enabled_modules  # noqa: E402


def _mods():
    """A linear synthetic pipeline: a -> b -> c, plus an independent ext."""
    return [
        SimpleNamespace(name="a", inputs=["raw"], outputs=["x"]),
        SimpleNamespace(name="b", inputs=["x"], outputs=["y"]),
        SimpleNamespace(name="c", inputs=["y"], outputs=["z"]),
        SimpleNamespace(name="ext", inputs=["raw"], outputs=["w"]),
    ]


def _names(mods):
    return [m.name for m in mods]


def test_all_enabled_by_default():
    assert _names(resolve_enabled_modules(_mods())) == ["a", "b", "c", "ext"]


def test_modules_allowlist_restricts_and_preserves_order():
    out = resolve_enabled_modules(_mods(), modules=["ext", "a", "b", "c"])
    assert _names(out) == ["a", "b", "c", "ext"]  # original order, not arg order


def test_only_takes_exact_set():
    out = resolve_enabled_modules(_mods(), only=["a", "ext"])
    assert _names(out) == ["a", "ext"]


def test_exclude_subtracts():
    out = resolve_enabled_modules(_mods(), exclude=["ext"])
    assert _names(out) == ["a", "b", "c"]


def test_only_overrides_modules_allowlist():
    out = resolve_enabled_modules(_mods(), modules=["a", "b", "c", "ext"], only=["ext"])
    assert _names(out) == ["ext"]


def test_unknown_name_raises():
    for kwargs in ({"modules": ["nope"]}, {"only": ["nope"]}, {"exclude": ["nope"]}):
        with pytest.raises(ValueError, match="Unknown module 'nope'"):
            resolve_enabled_modules(_mods(), **kwargs)


def test_disabled_dependency_raises():
    # Disabling 'b' orphans 'c', which needs 'y' produced by 'b'.
    with pytest.raises(ValueError, match="'c' needs input 'y'.*disabled module 'b'"):
        resolve_enabled_modules(_mods(), exclude=["b"])


def test_disabling_leaf_is_allowed():
    # 'c' produces 'z' which nothing consumes → safe to disable.
    assert _names(resolve_enabled_modules(_mods(), exclude=["c"])) == ["a", "b", "ext"]
