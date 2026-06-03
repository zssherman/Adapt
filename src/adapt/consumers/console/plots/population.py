# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Population plot rendering — JointDist, histograms → PNG."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from adapt.consumers.analysis.population import JointDist
from adapt.consumers.console.plots.styles import get_style

matplotlib.use("Agg")

__all__ = ["render_scatter", "render_histogram"]


def render_scatter(
    joint: JointDist,
    output_path: Path,
    style: str = "screen",
) -> Path:
    """Render a 2D joint distribution (KDE) as a filled contour PNG.

    Parameters
    ----------
    joint:
        Result of :func:`adapt.consumers.analysis.population.joint_distribution`.
    output_path:
        Destination path.
    style:
        Style preset name.

    Returns
    -------
    Path
    """
    rc = get_style(style)
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(6, 5))

        xx, yy = joint.x_grid, joint.y_grid
        ax.contourf(xx, yy, joint.density, levels=12, cmap="Blues")
        ax.contour(xx, yy, joint.density, levels=12, colors="steelblue", linewidths=0.5, alpha=0.5)

        ax.set_xlabel(joint.x_variable)
        ax.set_ylabel(joint.y_variable)
        ax.set_title(f"{joint.x_variable} vs {joint.y_variable}")

        fig.savefig(output_path, dpi=rc.get("figure.dpi", 150))
        plt.close(fig)

    return output_path


def render_histogram(
    tracks_df: pd.DataFrame,
    variable: str,
    output_path: Path,
    style: str = "screen",
    bins: int = 30,
) -> Path:
    """Render a histogram of a single track-level variable.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame.
    variable:
        Column to histogram.
    output_path:
        Destination path.
    style:
        Style preset name.
    bins:
        Number of histogram bins.

    Returns
    -------
    Path
    """
    rc = get_style(style)
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(6, 4))

        col = tracks_df[variable].dropna()
        ax.hist(col, bins=bins, color="steelblue", edgecolor="white", linewidth=0.5)
        ax.set_xlabel(variable)
        ax.set_ylabel("Count")
        ax.set_title(f"Distribution of {variable} (n={len(col)})")

        fig.savefig(output_path, dpi=rc.get("figure.dpi", 150))
        plt.close(fig)

    return output_path
