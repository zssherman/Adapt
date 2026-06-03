# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Export utilities — write materialised selections to CSV or Parquet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

__all__ = ["export_csv", "export_parquet"]


def export_csv(tracks_df: pd.DataFrame, output_path: Path) -> Path:
    """Write *tracks_df* to a CSV file.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame to export.
    output_path:
        Destination path (must end in .csv or similar).

    Returns
    -------
    Path
        Same as *output_path*.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tracks_df.to_csv(output_path, index=False)
    return output_path


def export_parquet(tracks_df: pd.DataFrame, output_path: Path) -> Path:
    """Write *tracks_df* to a Parquet file.

    Parameters
    ----------
    tracks_df:
        Track-level DataFrame to export.
    output_path:
        Destination path (must end in .parquet or similar).

    Returns
    -------
    Path
        Same as *output_path*.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tracks_df.to_parquet(output_path, index=False)
    return output_path
