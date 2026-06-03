# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""LogPanel — bottom status/log panel."""

from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

__all__ = ["LogPanel"]


class LogPanel(QListWidget):
    """Scrolling log panel for pipeline and render messages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumHeight(120)

    def append(self, message: str) -> None:
        self.addItem(QListWidgetItem(message))
        self.scrollToBottom()

    def clear_log(self) -> None:
        self.clear()
