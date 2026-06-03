# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Derived variable evaluation — pure computation, no plotting, no I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

__all__ = [
    "DerivedVariableSpec",
    "evaluate",
    "validate_expression",
]

# Columns / pandas methods the evaluator allows.
# Restrict to pandas Series operations; no arbitrary Python.
_ALLOWED_METHODS = frozenset(
    ["diff", "rolling", "mean", "std", "sum", "shift", "cumsum", "abs", "min", "max"]
)


@dataclass(frozen=True)
class DerivedVariableSpec:
    """Specification for a user-defined computed column.

    Parameters
    ----------
    name:
        Identifier for the derived variable (used as column name).
    expression:
        Pandas expression referencing existing columns.
        Example: ``"area.diff() / 300"``
    description:
        Human-readable description.
    """

    name: str
    expression: str
    description: str


def validate_expression(
    expression: str,
    available_columns: list[str],
) -> list[str]:
    """Validate an expression without evaluating it.

    Parameters
    ----------
    expression:
        Expression string to validate.
    available_columns:
        Columns present in the target DataFrame.

    Returns
    -------
    list of str
        Error messages. Empty list means valid.
    """
    errors: list[str] = []

    if not expression or not expression.strip():
        errors.append("Expression must not be empty")
        return errors

    # Extract bare identifiers that look like column references
    # (not methods like .diff(), not numeric literals)
    # Strip method calls (.diff(), .rolling(3).mean(), etc.)
    stripped = re.sub(r"\.\w+\([^)]*\)", "", expression)
    # Strip leading dot references (chained methods)
    stripped = re.sub(r"\.\w+", "", stripped)
    # Extract word tokens (potential column names)
    tokens = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", stripped)
    # Filter out numeric-only artifacts and Python builtins
    _builtins = frozenset(["True", "False", "None", "and", "or", "not", "in", "is"])
    column_candidates = [t for t in tokens if t not in _builtins]

    for token in column_candidates:
        if token not in available_columns:
            errors.append(f"Unknown column: '{token}'")

    return errors


def evaluate(
    history_df: pd.DataFrame,
    spec: DerivedVariableSpec,
) -> pd.Series:
    """Evaluate a derived variable expression on a track history DataFrame.

    Parameters
    ----------
    history_df:
        Track history DataFrame (one row per scan).
    spec:
        Derived variable specification.

    Returns
    -------
    pd.Series of computed values, same index as *history_df*.

    Raises
    ------
    KeyError
        If the expression references a column not in *history_df*.
    """
    if not spec.expression.strip():
        raise ValueError(f"Empty expression for derived variable '{spec.name}'")

    # Build local namespace from DataFrame columns
    local_ns = {col: history_df[col] for col in history_df.columns}

    try:
        result = eval(spec.expression, {"__builtins__": {}}, local_ns)  # noqa: S307
    except KeyError as exc:
        raise KeyError(
            f"Derived variable '{spec.name}': column {exc} not found in history"
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Derived variable '{spec.name}': expression evaluation failed: {exc}"
        ) from exc

    if isinstance(result, pd.Series):
        return result
    # Scalar broadcast
    return pd.Series(result, index=history_df.index)
