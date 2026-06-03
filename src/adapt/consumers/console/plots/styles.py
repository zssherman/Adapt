# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Matplotlib rcParam style presets for the Console plot layer."""

from __future__ import annotations

__all__ = ["STYLES", "get_style"]

STYLES: dict[str, dict] = {
    "publication": {
        "figure.dpi": 300,
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.constrained_layout.use": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
    },
    "screen": {
        "figure.dpi": 150,
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.constrained_layout.use": True,
        "savefig.bbox": "tight",
    },
    "presentation": {
        "figure.dpi": 200,
        "font.family": "sans-serif",
        "font.size": 14,
        "axes.labelsize": 14,
        "axes.titlesize": 15,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 13,
        "figure.constrained_layout.use": True,
        "savefig.bbox": "tight",
    },
    "ams": {
        "figure.dpi": 300,
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.constrained_layout.use": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    },
    "agu": {
        "figure.dpi": 300,
        "font.family": "sans-serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.constrained_layout.use": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    },
}


def get_style(name: str) -> dict:
    """Return a copy of the named style dict.

    Raises
    ------
    KeyError
        If *name* is not a registered style.
    """
    if name not in STYLES:
        raise KeyError(f"Unknown plot style: '{name}'. Available: {sorted(STYLES)}")
    return dict(STYLES[name])
