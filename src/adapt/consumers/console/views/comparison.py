# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""ComparisonView — side-by-side population comparison panel."""

from __future__ import annotations

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from adapt.consumers.analysis.comparison import ComparisonResult
from adapt.consumers.console.context import NavigationContext

matplotlib.use("Agg")

__all__ = ["ComparisonView"]


class ComparisonView(QWidget):
    """Displays a comparison between two track populations."""

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

        self._fig = Figure(figsize=(8, 4), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._draw_empty()

    def load_result(self, result: ComparisonResult) -> None:
        """Render summary statistics comparison bar chart."""
        self._fig.clear()
        n = len(result.variables)
        axes = self._fig.subplots(1, max(n, 1))
        if n == 1:
            axes = [axes]

        for ax, var in zip(axes, result.variables, strict=False):
            stats_a = result.summary_a.get(var, {})
            stats_b = result.summary_b.get(var, {})
            means = [stats_a.get("mean", 0), stats_b.get("mean", 0)]
            ax.bar(["A", "B"], means, color=["steelblue", "coral"])
            pval = result.ks_pvalues.get(var, float("nan"))
            ax.set_title(f"{var}\n(KS p={pval:.3f})")
            ax.set_ylabel("mean")

        self._canvas.draw_idle()

    def clear(self) -> None:
        self._fig.clear()
        self._draw_empty()
        self._canvas.draw_idle()

    def _draw_empty(self) -> None:
        ax = self._fig.add_subplot(111)
        ax.set_title("No comparison data")
        ax.text(
            0.5,
            0.5,
            "Select two populations to compare",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color="gray",
        )
