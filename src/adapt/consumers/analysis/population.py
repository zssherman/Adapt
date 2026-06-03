# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Population analysis — pure computation, no plotting, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

__all__ = [
    "JointDist",
    "summary_stats",
    "joint_distribution",
    "correlation_matrix",
]


@dataclass(frozen=True)
class JointDist:
    """Result of a 2D kernel density estimation.

    Parameters
    ----------
    x_grid:
        Evaluation points on the x axis, shape (n,).
    y_grid:
        Evaluation points on the y axis, shape (m,).
    density:
        KDE density values, shape (n, m).
    x_variable:
        Name of the x variable.
    y_variable:
        Name of the y variable.
    """

    x_grid: np.ndarray
    y_grid: np.ndarray
    density: np.ndarray
    x_variable: str
    y_variable: str


def summary_stats(
    tracks_df: pd.DataFrame,
    variables: list[str],
) -> dict[str, dict]:
    """Compute descriptive statistics for each variable.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame (one row per track).
    variables:
        Column names to summarise.

    Returns
    -------
    dict mapping variable name → dict of statistics:
    count, mean, std, min, p25, p50, p75, max.
    """
    result: dict[str, dict] = {}
    for var in variables:
        col = tracks_df[var].dropna()
        result[var] = {
            "count": int(len(col)),
            "mean": float(col.mean()),
            "std": float(col.std()),
            "min": float(col.min()),
            "p25": float(col.quantile(0.25)),
            "p50": float(col.quantile(0.50)),
            "p75": float(col.quantile(0.75)),
            "max": float(col.max()),
        }
    return result


def joint_distribution(
    tracks_df: pd.DataFrame,
    x: str,
    y: str,
    bandwidth: str | float = "scott",
    n_grid: int = 50,
) -> JointDist:
    """Estimate the 2D joint distribution of two track-level variables.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame.
    x:
        Column name for the x axis.
    y:
        Column name for the y axis.
    bandwidth:
        KDE bandwidth selector ('scott', 'silverman', or a scalar).
    n_grid:
        Number of grid points per axis.

    Returns
    -------
    JointDist
    """
    data = tracks_df[[x, y]].dropna()
    x_vals = data[x].values
    y_vals = data[y].values

    x_grid = np.linspace(x_vals.min(), x_vals.max(), n_grid)
    y_grid = np.linspace(y_vals.min(), y_vals.max(), n_grid)
    xx, yy = np.meshgrid(x_grid, y_grid)

    kernel = stats.gaussian_kde(np.vstack([x_vals, y_vals]), bw_method=bandwidth)
    density = kernel(np.vstack([xx.ravel(), yy.ravel()])).reshape(n_grid, n_grid)

    return JointDist(
        x_grid=x_grid,
        y_grid=y_grid,
        density=density,
        x_variable=x,
        y_variable=y,
    )


def correlation_matrix(
    tracks_df: pd.DataFrame,
    variables: list[str],
) -> pd.DataFrame:
    """Compute the Pearson correlation matrix for the given variables.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame.
    variables:
        Column names to include.

    Returns
    -------
    DataFrame with variables as both index and columns.
    """
    return tracks_df[variables].corr(method="pearson")
