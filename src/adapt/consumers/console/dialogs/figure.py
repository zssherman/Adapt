# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""FigureDialog — configure and create a FigureRecipe."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from adapt.consumers.console.workspace.models import FigureRecipe

__all__ = ["FigureDialog"]

_FIGURE_TYPES = [
    "lifecycle_composite",
    "lifecycle_heatmap",
    "population_scatter",
    "population_histogram",
    "comparison",
]

_STYLES = ["screen", "publication", "presentation", "ams", "agu"]


class FigureDialog(QDialog):
    """Configure a FigureRecipe for rendering."""

    def __init__(
        self,
        selection_slugs: list[str],
        available_variables: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Figure")
        self.setMinimumWidth(380)

        self._selection_slugs = selection_slugs
        self._available_variables = available_variables

        form = QFormLayout()

        self._type_combo = QComboBox()
        self._type_combo.addItems(_FIGURE_TYPES)

        self._selection_combo = QComboBox()
        self._selection_combo.addItems(selection_slugs)

        self._var_list = QListWidget()
        self._var_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._var_list.addItems(available_variables)
        if available_variables:
            self._var_list.item(0).setSelected(True)

        self._style_combo = QComboBox()
        self._style_combo.addItems(_STYLES)

        form.addRow("Figure type:", self._type_combo)
        form.addRow("Selection:", self._selection_combo)
        form.addRow("Variables:", self._var_list)
        form.addRow("Style:", self._style_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def current_recipe(self) -> FigureRecipe:
        selected_vars = (
            tuple(item.text() for item in self._var_list.selectedItems())
            or (self._available_variables[0],)
            if self._available_variables
            else ("area",)
        )

        return FigureRecipe(
            figure_type=self._type_combo.currentText(),
            selection_slug=self._selection_combo.currentText(),
            variables=selected_vars,
            options={},
            style=self._style_combo.currentText(),
        )
