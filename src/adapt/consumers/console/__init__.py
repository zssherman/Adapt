# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""ADAPT Console — scientific analysis workbench (PySide6).

Install requirements::

    pip install adapt[console]

Usage::

    adapt console [--workspace /path/to/workspace]
"""

from __future__ import annotations

__all__ = ["main"]


def main(workspace: str | None = None) -> None:
    """Launch the ADAPT Console application.

    Raises
    ------
    ImportError
        If PySide6 is not installed.
    """
    try:
        import PySide6  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "ADAPT Console requires PySide6. Install it with:\n\n"
            "    pip install adapt[console]\n\n"
            "or:\n\n"
            "    pip install PySide6>=6.6\n"
        ) from exc

    from adapt.consumers.console.app import run_console

    run_console(workspace=workspace)
