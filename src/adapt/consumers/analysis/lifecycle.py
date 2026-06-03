# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Lifecycle analysis — pure computation, no plotting, no I/O.

All functions accept pandas DataFrames and return plain data structures.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = [
    "LifecycleComposite",
    "normalize_time",
    "compute_composite",
    "compute_density",
    "cluster_lifecycles",
]


@dataclass(frozen=True)
class LifecycleComposite:
    """Result of computing a normalized lifecycle composite.

    Parameters
    ----------
    time_axis:
        Normalized time values in [0, 1], shape (n_steps,).
    mean:
        Mean variable value at each time step, shape (n_steps,).
    percentiles:
        Mapping {percentile_int: array of shape (n_steps,)}.
    n_tracks:
        Number of tracks that contributed.
    variable:
        Name of the variable that was composited.
    """

    time_axis: np.ndarray
    mean: np.ndarray
    percentiles: dict[int, np.ndarray]
    n_tracks: int
    variable: str


def normalize_time(
    history_df: pd.DataFrame,
    variable: str,
    alignment: str = "birth",
) -> pd.DataFrame:
    """Normalize the time axis of a track history to [0, 1].

    Parameters
    ----------
    history_df:
        DataFrame with columns ``scan_time`` and *variable*.
        May contain multiple tracks (identified by ``cell_uid``).
    variable:
        Column name to carry through (other columns are dropped).
    alignment:
        'birth' — 0 at first scan, 1 at last scan.

    Returns
    -------
    DataFrame with columns: ``cell_uid`` (if present), ``norm_time``, *variable*.
    """
    if history_df.empty:
        cols = ["norm_time", variable]
        if "cell_uid" in history_df.columns:
            cols = ["cell_uid"] + cols
        return pd.DataFrame(columns=cols)

    df = history_df.copy().sort_values("scan_time")

    if "cell_uid" in df.columns:
        groups = []
        for _uid, group in df.groupby("cell_uid", sort=False):
            group = group.sort_values("scan_time").copy()
            group["norm_time"] = _normalize_group_time(group)
            groups.append(group[["cell_uid", "norm_time", variable]])
        return pd.concat(groups, ignore_index=True)

    df["norm_time"] = _normalize_group_time(df)
    return df[["norm_time", variable]]


def _normalize_group_time(group: pd.DataFrame) -> pd.Series:
    times = pd.to_datetime(group["scan_time"])
    t0 = times.min()
    t1 = times.max()
    span = (t1 - t0).total_seconds()
    if span == 0:
        return pd.Series(np.zeros(len(group)), index=group.index)
    elapsed = (times - t0).dt.total_seconds()
    return elapsed / span


def compute_composite(
    normalized_df: pd.DataFrame,
    variable: str,
    percentiles: tuple[int, ...] = (10, 25, 50, 75, 90),
    n_time_bins: int = 20,
) -> LifecycleComposite:
    """Compute normalized lifecycle composite statistics.

    Parameters
    ----------
    normalized_df:
        Output of :func:`normalize_time`: must contain ``norm_time`` and *variable*.
    variable:
        Column to composite.
    percentiles:
        Integer percentiles to include in the result.
    n_time_bins:
        Number of evenly-spaced time bins across [0, 1].

    Returns
    -------
    LifecycleComposite
    """
    bin_edges = np.linspace(0.0, 1.0, n_time_bins + 1)
    bin_centres = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    norm_times = normalized_df["norm_time"].values
    values = normalized_df[variable].values

    bin_indices = np.digitize(norm_times, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_time_bins - 1)

    mean = np.full(n_time_bins, np.nan)
    pct_arrays: dict[int, np.ndarray] = {p: np.full(n_time_bins, np.nan) for p in percentiles}

    for i in range(n_time_bins):
        mask = bin_indices == i
        if mask.sum() == 0:
            continue
        bin_vals = values[mask]
        mean[i] = np.nanmean(bin_vals)
        for p in percentiles:
            pct_arrays[p][i] = np.nanpercentile(bin_vals, p)

    n_tracks = normalized_df["cell_uid"].nunique() if "cell_uid" in normalized_df.columns else 1

    return LifecycleComposite(
        time_axis=bin_centres,
        mean=mean,
        percentiles=pct_arrays,
        n_tracks=n_tracks,
        variable=variable,
    )


def compute_density(
    normalized_df: pd.DataFrame,
    variable: str,
    n_time_bins: int = 50,
    n_var_bins: int = 50,
) -> np.ndarray:
    """Compute 2D histogram (density) of normalized-time × variable.

    Parameters
    ----------
    normalized_df:
        Output of :func:`normalize_time`.
    variable:
        Column to bin on the variable axis.
    n_time_bins:
        Number of bins along the normalized-time axis.
    n_var_bins:
        Number of bins along the variable axis.

    Returns
    -------
    np.ndarray of shape (n_time_bins, n_var_bins).
        Each cell contains the count of data points in that bin.
    """
    norm_times = normalized_df["norm_time"].values
    values = normalized_df[variable].values

    mask = np.isfinite(norm_times) & np.isfinite(values)
    norm_times = norm_times[mask]
    values = values[mask]

    hist, _, _ = np.histogram2d(
        norm_times,
        values,
        bins=[n_time_bins, n_var_bins],
        range=[[0.0, 1.0], [np.nanmin(values), np.nanmax(values)]],
    )
    return hist


def cluster_lifecycles(
    normalized_df: pd.DataFrame,
    n_clusters: int = 5,
) -> pd.DataFrame:
    """Assign lifecycle cluster labels to tracks using k-means.

    Parameters
    ----------
    normalized_df:
        Output of :func:`normalize_time` with a ``cell_uid`` column.
    n_clusters:
        Number of k-means clusters.

    Returns
    -------
    DataFrame with columns: ``cell_uid``, ``cluster``.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    if "cell_uid" not in normalized_df.columns:
        raise ValueError("normalized_df must contain a 'cell_uid' column for clustering")

    # Pivot to one row per track: time bins as features
    pivot = (
        normalized_df.assign(time_bin=lambda df: pd.cut(df["norm_time"], bins=10, labels=False))
        .groupby(["cell_uid", "time_bin"])
        .agg(
            value=("area" if "area" in normalized_df.columns else normalized_df.columns[-1], "mean")
        )
        .unstack(fill_value=0.0)
    )
    uids = pivot.index.tolist()
    X = StandardScaler().fit_transform(pivot.values)
    labels = KMeans(n_clusters=n_clusters, random_state=0, n_init="auto").fit_predict(X)
    return pd.DataFrame({"cell_uid": uids, "cluster": labels})
