# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Architecture tests: enforce module-independence without hardcoding module names.

These tests discover adapt.modules subpackages at runtime and verify that
no scientific module imports from any other scientific module. New modules
are picked up automatically — no test edits required.

Run: pytest tests/test_architecture.py
"""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

# Skip the entire file gracefully if adapt is not installed in this environment.
# This prevents VSCode pytest discovery errors when the wrong interpreter is active.
adapt_modules = pytest.importorskip(
    "adapt.modules",
    reason="adapt not installed in this Python environment — activate adapt_env",
)


def _discover_module_packages() -> list[str]:
    """Return all immediate subpackage names under adapt.modules."""
    return [
        f"adapt.modules.{info.name}"
        for info in pkgutil.iter_modules(adapt_modules.__path__)
        if info.ispkg
    ]


def _source_files(package_name: str) -> list[Path]:
    """Return all .py files belonging to a package."""
    mod = importlib.import_module(package_name)
    assert mod.__file__ is not None
    pkg_dir = Path(mod.__file__).parent
    return list(pkg_dir.rglob("*.py"))


def _imported_adapt_modules(py_file: Path) -> set[str]:
    """Parse a .py file and return the set of adapt.modules.* names it imports."""
    try:
        tree = ast.parse(py_file.read_text())
    except SyntaxError:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("adapt.modules."):
                    imports.add(alias.name)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("adapt.modules.")
        ):
            imports.add(node.module)
    return imports


# Build the test matrix at collection time — works for any future module.
_PACKAGES = _discover_module_packages()
_SKIP = {"adapt.modules.base"}  # base.py is shared infrastructure, not a science module


@pytest.mark.parametrize("pkg", [p for p in _PACKAGES if p not in _SKIP])
def test_module_does_not_import_other_modules(pkg: str) -> None:
    """Scientific module must not import from any other adapt.modules subpackage.

    This test is parameterised over every subpackage discovered under adapt.modules.
    Adding a new module directory makes it appear here automatically.
    """
    files = _source_files(pkg)
    violations: list[str] = []

    for py_file in files:
        for imported in _imported_adapt_modules(py_file):
            # Allow self-imports (within the same subpackage)
            if not imported.startswith(pkg):
                violations.append(f"  {py_file.name}: imports {imported!r}")

    assert not violations, (
        f"\n{pkg} imports from other scientific modules — "
        "shared types belong in adapt.contracts:\n" + "\n".join(violations)
    )


@pytest.mark.parametrize("pkg", [p for p in _PACKAGES if p not in _SKIP])
def test_module_does_not_import_execution_or_runtime(pkg: str) -> None:
    """Scientific module must not import from adapt.execution or adapt.runtime."""
    forbidden_prefixes = ("adapt.execution", "adapt.runtime", "adapt.persistence")
    files = _source_files(pkg)
    violations: list[str] = []

    for py_file in files:
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(name.startswith(p) for p in forbidden_prefixes):
                    violations.append(f"  {py_file.name}: imports {name!r}")

    assert not violations, (
        f"\n{pkg} imports from layers above it — "
        "modules must only depend on contracts/ and utils/:\n" + "\n".join(violations)
    )


# ── Canonical scan-time serialization (single source of truth) ────────────────
# scan_time is the cross-table join key: cells_by_scan and every derived module
# table must store the identical string, or joins silently fail. The format lives
# in exactly one function — adapt.utils.time.to_scan_iso. This fitness function
# fails if any other code formats scan-time independently (drift = broken joins).

_SCAN_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_SRC_ADAPT = Path(__file__).parents[1] / "src" / "adapt"


def test_scan_time_format_is_defined_in_exactly_one_place() -> None:
    """The scan-time join-key format may appear only in adapt.utils.time."""
    offenders: list[str] = []
    for py_file in _SRC_ADAPT.rglob("*.py"):
        if _SCAN_TIME_FORMAT in py_file.read_text():
            offenders.append(str(py_file.relative_to(_SRC_ADAPT)))

    assert offenders == ["utils/time.py"], (
        "scan-time format must be centralized in adapt.utils.time.to_scan_iso — "
        f"found the literal {_SCAN_TIME_FORMAT!r} in: {offenders}. "
        "Serialize scan_time via to_scan_iso (or let ModuleOutputWriter do it); "
        "never hardcode the format, or derived tables will not join cells_by_scan."
    )
