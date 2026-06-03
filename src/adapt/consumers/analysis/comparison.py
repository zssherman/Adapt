# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Population and lifecycle comparison — pure computation, no plotting, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy import stats

from adapt.consumers.analysis.population import summary_stats

__all__ = [
    "ComparisonResult",
    "compare_populations",
]


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing two track populations.

    Parameters
    ----------
    summary_a:
        Summary statistics for population A (from :func:`summary_stats`).
    summary_b:
        Summary statistics for population B.
    ks_pvalues:
        Kolmogorov-Smirnov test p-values per variable.
        Small p-value → distributions differ significantly.
    variables:
        Variables included in the comparison.
    """

    summary_a: dict
    summary_b: dict
    ks_pvalues: dict[str, float]
    variables: list[str]


def compare_populations(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    variables: list[str],
) -> ComparisonResult:
    """Compare two track-level populations.

    Parameters
    ----------
    df_a:
        Track DataFrame for population A.
    df_b:
        Track DataFrame for population B.
    variables:
        Column names to compare.

    Returns
    -------
    ComparisonResult
    """
    summary_a = summary_stats(df_a, variables)
    summary_b = summary_stats(df_b, variables)

    ks_pvalues: dict[str, float] = {}
    for var in variables:
        a_vals = df_a[var].dropna().values
        b_vals = df_b[var].dropna().values
        if len(a_vals) >= 2 and len(b_vals) >= 2:
            _, pvalue = stats.ks_2samp(a_vals, b_vals)
        else:
            pvalue = float("nan")
        ks_pvalues[var] = pvalue

    return ComparisonResult(
        summary_a=summary_a,
        summary_b=summary_b,
        ks_pvalues=ks_pvalues,
        variables=variables,
    )
