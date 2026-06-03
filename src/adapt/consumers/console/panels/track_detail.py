# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""TrackDetailView — timeline plot for a single track."""

from __future__ import annotations

import matplotlib
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from adapt.api.client import RepositoryClient
from adapt.consumers.console.context import NavigationContext

matplotlib.use("Agg")

__all__ = ["TrackDetailView"]


class TrackDetailView(QWidget):
    """Displays area, reflectivity, and other variables over a track's lifetime.

    Responds to :attr:`NavigationContext.track_focused` — clears itself
    when a new track is focused (the caller must supply history data via
    :meth:`load_history`).
    """

    def __init__(
        self,
        ctx: NavigationContext,
        client: RepositoryClient | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._client: RepositoryClient | None = client
        self._run_id: str | None = None
        self._cell_uid: str | None = None

        self._fig = Figure(figsize=(8, 3), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._draw_empty()

        ctx.track_focused.connect(self._on_track_focused)

    def load_history(
        self,
        run_id: str,
        cell_uid: str,
        history: pd.DataFrame,
    ) -> None:
        """Render the track timeline for *cell_uid*."""
        self._run_id = run_id
        self._cell_uid = cell_uid
        self._fig.clear()

        cols = [c for c in history.columns if c != "scan_time"]
        n = len(cols)
        if n == 0:
            self._draw_empty()
            self._canvas.draw_idle()
            return

        axes = self._fig.subplots(1, n, sharey=False)
        if n == 1:
            axes = [axes]

        times = pd.to_datetime(history["scan_time"])
        for ax, col in zip(axes, cols, strict=False):
            ax.plot(times, history[col], color="steelblue", linewidth=1.2)
            ax.set_title(col, fontsize=9)
            ax.tick_params(axis="x", labelrotation=30, labelsize=7)

        self._fig.suptitle(f"Track {cell_uid}", fontsize=10)
        self._canvas.draw_idle()

    def clear(self) -> None:
        self._run_id = None
        self._cell_uid = None
        self._fig.clear()
        self._draw_empty()
        self._canvas.draw_idle()

    def _draw_empty(self) -> None:
        ax = self._fig.add_subplot(111)
        ax.set_title("No track selected")
        ax.text(
            0.5,
            0.5,
            "Click a track to view its timeline",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color="gray",
        )

    def set_client(self, client: RepositoryClient | None) -> None:
        self._client = client

    def _on_track_focused(self, run_id: str, cell_uid: str) -> None:
        if run_id == self._run_id and cell_uid == self._cell_uid:
            return
        self.clear()
        if self._client is None:
            return
        try:
            history = self._client.track_history(run_id, cell_uid)
            self.load_history(run_id, cell_uid, history)
        except Exception:
            pass
