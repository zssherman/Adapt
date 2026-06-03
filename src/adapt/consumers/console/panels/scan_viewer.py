# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""ScanViewer — panel for displaying a radar scan at a given time."""

from __future__ import annotations

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from adapt.consumers.console.context import NavigationContext

matplotlib.use("Agg")

__all__ = ["ScanViewer"]


class ScanViewer(QWidget):
    """Displays a radar scan image.

    Responds to :attr:`NavigationContext.scan_requested` — requests
    a ScanBundle from the caller and renders it. In this implementation
    the scan rendering is placeholder-based; full integration with
    :class:`adapt.visualization.plotter.RadarPlotter` is wired in
    Phase 8 integration work.
    """

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

        self._fig = Figure(figsize=(6, 5), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)

        self._status = QLabel("No scan loaded")
        self._status.setMaximumHeight(20)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        layout.addWidget(self._status)

        self.show_placeholder("No scan loaded")

        ctx.scan_requested.connect(self._on_scan_requested)

    def show_placeholder(self, message: str) -> None:
        self._ax.cla()
        self._ax.set_title(message)
        self._ax.text(
            0.5,
            0.5,
            message,
            transform=self._ax.transAxes,
            ha="center",
            va="center",
            color="gray",
        )
        self._status.setText(message)
        self._canvas.draw_idle()

    def _on_scan_requested(self, run_id: str, cell_uid: str, scan_time: object) -> None:
        self.show_placeholder(f"Loading scan at {scan_time} …")
        # Full ScanBundle loading via RepositoryClient wired by MainWindow
        # in Phase 8 integration.
