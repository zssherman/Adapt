# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Lifecycle plot rendering — LifecycleComposite → PNG."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from adapt.consumers.analysis.lifecycle import LifecycleComposite
from adapt.consumers.console.plots.styles import get_style

matplotlib.use("Agg")

__all__ = ["render_composite", "render_heatmap"]


def render_composite(
    composite: LifecycleComposite,
    output_path: Path,
    style: str = "screen",
) -> Path:
    """Render a lifecycle composite to a PNG file.

    Parameters
    ----------
    composite:
        Result of :func:`adapt.consumers.analysis.lifecycle.compute_composite`.
    output_path:
        Destination path (parent directory must exist).
    style:
        Name of the style preset from :mod:`styles`.

    Returns
    -------
    Path
        Same as *output_path*.
    """
    rc = get_style(style)
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(7, 4))

        t = composite.time_axis
        ax.plot(t, composite.mean, color="black", linewidth=1.5, label="mean")

        pct_pairs = [(10, 90), (25, 75)]
        alphas = [0.15, 0.25]
        for (lo, hi), alpha in zip(pct_pairs, alphas, strict=True):
            if lo in composite.percentiles and hi in composite.percentiles:
                ax.fill_between(
                    t,
                    composite.percentiles[lo],
                    composite.percentiles[hi],
                    alpha=alpha,
                    color="steelblue",
                )
        if 50 in composite.percentiles:
            ax.plot(
                t,
                composite.percentiles[50],
                color="steelblue",
                linewidth=1.0,
                linestyle="--",
                label="median",
            )

        ax.set_xlabel("Normalized time")
        ax.set_ylabel(composite.variable)
        ax.set_title(f"Lifecycle composite — {composite.variable} (n={composite.n_tracks})")
        ax.set_xlim(0, 1)
        ax.legend(loc="best", frameon=False)

        fig.savefig(output_path, dpi=rc.get("figure.dpi", 150))
        plt.close(fig)

    return output_path


def render_heatmap(
    density: np.ndarray,
    variable: str,
    output_path: Path,
    style: str = "screen",
) -> Path:
    """Render a lifecycle density (2D histogram) as a heatmap PNG.

    Parameters
    ----------
    density:
        2D array of shape (n_time_bins, n_var_bins), from
        :func:`adapt.consumers.analysis.lifecycle.compute_density`.
    variable:
        Variable name used for the y-axis label.
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
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.imshow(
            density.T,
            origin="lower",
            aspect="auto",
            extent=(0, 1, 0, density.shape[1]),
            cmap="viridis",
        )
        ax.set_xlabel("Normalized time")
        ax.set_ylabel(variable)
        ax.set_title(f"Lifecycle density — {variable}")

        fig.savefig(output_path, dpi=rc.get("figure.dpi", 150))
        plt.close(fig)

    return output_path
