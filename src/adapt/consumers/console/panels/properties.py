# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""PropertiesPanel — right-dock panel showing selection/track summary."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QScrollArea, QWidget

from adapt.consumers.console.context import NavigationContext

__all__ = ["PropertiesPanel"]


class PropertiesPanel(QScrollArea):
    """Displays summary information for the active selection or focused track."""

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

        container = QWidget()
        self._layout = QFormLayout(container)
        self._layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._slug_label = QLabel("")
        self._run_label = QLabel("")
        self._count_label = QLabel("")

        self._layout.addRow("Selection:", self._slug_label)
        self._layout.addRow("Run:", self._run_label)
        self._layout.addRow("Tracks:", self._count_label)

        self.setWidget(container)
        self.setWidgetResizable(True)

        ctx.selection_activated.connect(self._on_selection)

    def show_selection(
        self,
        slug: str | None,
        run_id: str | None,
        track_count: int | None,
    ) -> None:
        self._slug_label.setText(slug or "")
        self._run_label.setText(run_id or "")
        self._count_label.setText(str(track_count) if track_count is not None else "")

    def _on_selection(self, slug: object) -> None:
        self._slug_label.setText(str(slug))
