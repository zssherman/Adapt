# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""LifecycleView — lifecycle composite plot with variable selector."""

from __future__ import annotations

import matplotlib
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from adapt.consumers.analysis.lifecycle import LifecycleComposite
from adapt.consumers.console.context import NavigationContext

matplotlib.use("Agg")

__all__ = ["LifecycleView"]

# cells_by_scan numeric variables useful for lifecycle analysis
_HISTORY_VARS = [
    ("cell_area_sqkm", "Area (km²)"),
    ("radar_reflectivity_max", "Reflectivity max (dBZ)"),
    ("radar_reflectivity_mean", "Reflectivity mean (dBZ)"),
    ("radar_differential_reflectivity_max", "ZDR max (dB)"),
    ("radar_differential_reflectivity_mean", "ZDR mean (dB)"),
    ("radar_velocity_mean", "Velocity mean (m/s)"),
    ("radar_spectrum_width_mean", "Spectrum width mean (m/s)"),
    ("radar_cross_correlation_ratio_mean", "CCR mean"),
    ("area_40dbz_km2", "40 dBZ core area (km²)"),
    ("n_adjacent_cells", "Adjacent cells"),
]


class LifecycleView(QWidget):
    """Lifecycle composite (mean ± percentile bands) over normalised time.

    Requires track histories to be passed via :meth:`load_histories`.
    Variable is selectable from a combo box.
    """

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._histories: pd.DataFrame | None = None

        # ── Controls ─────────────────────────────────────────────────────────
        self._var_combo = QComboBox()
        for col, label in _HISTORY_VARS:
            self._var_combo.addItem(label, userData=col)

        self._status_label = QLabel("No data loaded")
        self._plot_btn = QPushButton("Plot")
        self._plot_btn.clicked.connect(self._replot)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(4, 2, 4, 2)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Variable:", self._var_combo)
        ctrl_layout.addLayout(form)
        ctrl_layout.addWidget(self._plot_btn)
        ctrl_layout.addWidget(self._status_label)
        ctrl_layout.addStretch()

        # ── Canvas ─────────────────────────────────────────────────────────
        self._fig = Figure(figsize=(7, 4), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(ctrl_layout)
        layout.addWidget(self._canvas, stretch=1)

        self._draw_empty()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_histories(self, histories: pd.DataFrame, n_tracks: int) -> None:
        """Load concatenated cells_by_scan histories for all tracks.

        Parameters
        ----------
        histories:
            Long-form DataFrame: one row per (cell_uid, scan_time).
            Must contain ``cell_uid``, ``scan_time``, and at least
            one numeric column.
        n_tracks:
            Number of unique tracks contributing to *histories*.
        """
        self._histories = histories
        self._n_tracks = n_tracks
        self._status_label.setText(f"{n_tracks} tracks loaded — press Plot")

        # Enable only variables present in the data
        available = set(histories.columns)
        for i in range(self._var_combo.count()):
            col = self._var_combo.itemData(i)
            enabled = col in available
            flags = self._var_combo.model().item(i).flags()
            from PySide6.QtCore import Qt

            if enabled:
                self._var_combo.model().item(i).setFlags(flags | Qt.ItemFlag.ItemIsEnabled)
            else:
                self._var_combo.model().item(i).setFlags(flags & ~Qt.ItemFlag.ItemIsEnabled)

        self._replot()

    def load_composite(self, composite: LifecycleComposite | None) -> None:
        """Render a pre-computed LifecycleComposite directly."""
        self._ax.cla()
        if composite is None:
            self._draw_empty()
            self._canvas.draw_idle()
            return
        self._render_composite(composite)
        self._canvas.draw_idle()

    def clear(self) -> None:
        self._histories = None
        self._ax.cla()
        self._draw_empty()
        self._canvas.draw_idle()

    # ── Private ───────────────────────────────────────────────────────────────

    def _replot(self) -> None:
        if self._histories is None or self._histories.empty:
            self._draw_empty()
            self._canvas.draw_idle()
            return
        variable = self._var_combo.currentData()
        if not variable or variable not in self._histories.columns:
            self._draw_empty("Variable not available in loaded data")
            self._canvas.draw_idle()
            return
        try:
            from adapt.consumers.analysis.lifecycle import compute_composite, normalize_time

            normed = normalize_time(self._histories, variable)
            composite = compute_composite(normed, variable)
            self._ax.cla()
            self._render_composite(composite)
            self._canvas.draw_idle()
        except Exception as exc:
            self._draw_empty(str(exc))
            self._canvas.draw_idle()

    def _render_composite(self, composite: LifecycleComposite) -> None:
        t = composite.time_axis
        self._ax.plot(t, composite.mean, color="black", linewidth=1.5, label="mean")
        if 50 in composite.percentiles:
            self._ax.plot(
                t,
                composite.percentiles[50],
                color="steelblue",
                linewidth=1.0,
                linestyle="--",
                label="median",
            )
        for lo, hi, alpha in ((25, 75, 0.25), (10, 90, 0.12)):
            if lo in composite.percentiles and hi in composite.percentiles:
                self._ax.fill_between(
                    t,
                    composite.percentiles[lo],
                    composite.percentiles[hi],
                    alpha=alpha,
                    color="steelblue",
                )
        self._ax.set_xlabel("Normalised lifetime (0 = initiation, 1 = termination)")
        label = next(
            (lbl for col, lbl in _HISTORY_VARS if col == composite.variable), composite.variable
        )
        self._ax.set_ylabel(label)
        self._ax.set_title(f"Lifecycle: {label}  (n={composite.n_tracks} tracks)")
        self._ax.set_xlim(0, 1)
        self._ax.legend(loc="best", frameon=False)

    def _draw_empty(self, msg: str = "Click a run → create a selection → open this view") -> None:
        self._ax.cla()
        self._ax.set_xlabel("Normalised lifetime")
        self._ax.set_ylabel("Variable")
        self._ax.set_title("Lifecycle — no data")
        self._ax.text(
            0.5,
            0.5,
            msg,
            transform=self._ax.transAxes,
            ha="center",
            va="center",
            color="gray",
            fontsize=10,
            wrap=True,
        )
