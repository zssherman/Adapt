# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""WorkspaceExplorer — left-dock tree view for runs, selections, figures, movies."""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from adapt.consumers.console.context import NavigationContext

__all__ = ["WorkspaceExplorer"]

_RUNS = "Runs"
_SELECTIONS = "Selections"
_FIGURES = "Figures"
_MOVIES = "Movies"


class WorkspaceExplorer(QWidget):
    """Tree widget showing workspace contents: runs, selections, figures, movies."""

    def __init__(self, ctx: NavigationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Workspace"])

        self._runs_item = QStandardItem(_RUNS)
        self._selections_item = QStandardItem(_SELECTIONS)
        self._figures_item = QStandardItem(_FIGURES)
        self._movies_item = QStandardItem(_MOVIES)

        root = self._model.invisibleRootItem()
        for item in (self._runs_item, self._selections_item, self._figures_item, self._movies_item):
            item.setEditable(False)
            root.appendRow(item)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(False)
        self._tree.expandAll()
        self._tree.clicked.connect(self._on_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree)

    def model(self) -> QStandardItemModel:
        return self._model

    def set_runs(self, run_ids: list[str]) -> None:
        self._runs_item.removeRows(0, self._runs_item.rowCount())
        for rid in run_ids:
            item = QStandardItem(rid)
            item.setEditable(False)
            item.setData(rid, role=257)  # UserRole+1 for run_id
            self._runs_item.appendRow(item)
        self._tree.expand(self._model.indexFromItem(self._runs_item))

    def set_selections(self, slugs: list[str]) -> None:
        self._selections_item.removeRows(0, self._selections_item.rowCount())
        for slug in slugs:
            item = QStandardItem(slug)
            item.setEditable(False)
            item.setData(slug, role=256)  # UserRole
            self._selections_item.appendRow(item)
        self._tree.expand(self._model.indexFromItem(self._selections_item))

    def set_figures(self, slugs: list[str]) -> None:
        self._figures_item.removeRows(0, self._figures_item.rowCount())
        for slug in slugs:
            item = QStandardItem(slug)
            item.setEditable(False)
            self._figures_item.appendRow(item)
        self._tree.expand(self._model.indexFromItem(self._figures_item))

    def activate_run(self, run_id: str) -> None:
        self._ctx.run_activated.emit(run_id)

    def activate_selection(self, slug: str) -> None:
        self._ctx.selection_activated.emit(slug)

    def _on_clicked(self, index) -> None:
        parent = index.parent()
        if not parent.isValid():
            return
        parent_item = self._model.itemFromIndex(parent)
        item = self._model.itemFromIndex(index)
        if parent_item is self._runs_item:
            run_id = item.data(257)
            if run_id:
                self._ctx.run_activated.emit(run_id)
        elif parent_item is self._selections_item:
            slug = item.data(256)
            if slug:
                self._ctx.selection_activated.emit(slug)
