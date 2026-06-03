# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""PopulationView — embedded matplotlib population scatter and histogram."""

from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from adapt.consumers.console.context import NavigationContext

matplotlib.use("Agg")

__all__ = ["PopulationView"]

# Numeric columns from cell_tracks that are useful for population plots
_TRACK_VARS = [
    "max_area_sqkm",
    "max_reflectivity",
    "n_scans",
]

# Labels shown in the combo box
_TRACK_VAR_LABELS = {
    "max_area_sqkm": "Max area (km²)",
    "max_reflectivity": "Max reflectivity (dBZ)",
    "n_scans": "Number of scans",
    "lifetime_s": "Lifetime (s)",
}


class PopulationView(QWidget):
    """Population scatter and histogram of track-level properties.

    Displays one point per track from the active selection or full run.
    Variable axes are configurable via combo boxes.
    """

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._df: pd.DataFrame | None = None

        # ── Controls bar ─────────────────────────────────────────────────────
        self._x_combo = QComboBox()
        self._y_combo = QComboBox()
        self._plot_btn = QPushButton("Plot")
        self._plot_btn.clicked.connect(self._replot)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(4, 2, 4, 2)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("X axis:", self._x_combo)
        form.addRow("Y axis:", self._y_combo)
        ctrl_layout.addLayout(form)
        ctrl_layout.addWidget(self._plot_btn)
        ctrl_layout.addStretch()

        # ── Canvas ────────────────────────────────────────────────────────────
        self._fig = Figure(figsize=(7, 5), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(ctrl_layout)
        layout.addWidget(self._canvas, stretch=1)

        self._draw_empty()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_tracks(self, df: pd.DataFrame) -> None:
        """Load a cell_tracks DataFrame and render the default scatter."""
        self._df = df
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        labels = [_TRACK_VAR_LABELS.get(c, c) for c in numeric_cols]

        self._x_combo.blockSignals(True)
        self._y_combo.blockSignals(True)
        self._x_combo.clear()
        self._y_combo.clear()
        for col, label in zip(numeric_cols, labels, strict=False):
            self._x_combo.addItem(label, userData=col)
            self._y_combo.addItem(label, userData=col)

        # Defaults: area vs reflectivity if available
        self._set_combo_default(self._x_combo, "max_area_sqkm")
        self._set_combo_default(self._y_combo, "max_reflectivity")

        self._x_combo.blockSignals(False)
        self._y_combo.blockSignals(False)
        self._replot()

    def load_scatter(self, joint) -> None:
        """Render a pre-computed JointDist (from consumers.analysis.population)."""
        self._ax.cla()
        self._ax.contourf(joint.x_grid, joint.y_grid, joint.density, levels=12, cmap="Blues")
        self._ax.set_xlabel(joint.x_variable)
        self._ax.set_ylabel(joint.y_variable)
        self._ax.set_title(f"{joint.x_variable} vs {joint.y_variable}")
        self._canvas.draw_idle()

    def load_histogram(self, tracks_df: pd.DataFrame, variable: str, bins: int = 30) -> None:
        """Render a histogram of *variable* from *tracks_df*."""
        self._ax.cla()
        col = tracks_df[variable].dropna()
        self._ax.hist(col, bins=bins, color="steelblue", edgecolor="white", linewidth=0.5)
        self._ax.set_xlabel(variable)
        self._ax.set_ylabel("Count")
        self._ax.set_title(f"Distribution of {variable}  (n={len(col)})")
        self._canvas.draw_idle()

    def clear(self) -> None:
        self._df = None
        self._ax.cla()
        self._draw_empty()
        self._canvas.draw_idle()

    # ── Private ───────────────────────────────────────────────────────────────

    def _set_combo_default(self, combo: QComboBox, col: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == col:
                combo.setCurrentIndex(i)
                return

    def _replot(self) -> None:
        if self._df is None or self._df.empty:
            self._draw_empty()
            self._canvas.draw_idle()
            return
        x_col = self._x_combo.currentData()
        y_col = self._y_combo.currentData()
        if not x_col or not y_col:
            return

        common = self._df[[x_col, y_col]].dropna()
        if common.empty:
            self._draw_empty()
            self._canvas.draw_idle()
            return

        self._ax.cla()

        # Scatter with colour by density
        from matplotlib.colors import Normalize

        xv = common[x_col].to_numpy(dtype=float)
        yv = common[y_col].to_numpy(dtype=float)

        # Colour points by local point density (2D histogram)
        if len(xv) > 4:
            h, xe, ye = np.histogram2d(xv, yv, bins=20)
            xi = np.clip(np.searchsorted(xe, xv) - 1, 0, h.shape[0] - 1)
            yi = np.clip(np.searchsorted(ye, yv) - 1, 0, h.shape[1] - 1)
            c = h[xi, yi]
        else:
            c = np.ones(len(xv))

        sc = self._ax.scatter(xv, yv, c=c, cmap="plasma", s=18, alpha=0.7, norm=Normalize(vmin=0))
        self._fig.colorbar(sc, ax=self._ax, label="point density")

        x_label = _TRACK_VAR_LABELS.get(x_col, x_col)
        y_label = _TRACK_VAR_LABELS.get(y_col, y_col)
        self._ax.set_xlabel(x_label)
        self._ax.set_ylabel(y_label)
        self._ax.set_title(f"{y_label} vs {x_label}  (n={len(common)})")
        self._canvas.draw_idle()

    def _draw_empty(self) -> None:
        self._ax.set_title("Population — no data")
        self._ax.text(
            0.5,
            0.5,
            "Click a run in the Workspace tree,\nthen open this view.",
            transform=self._ax.transAxes,
            ha="center",
            va="center",
            color="gray",
            fontsize=11,
        )
