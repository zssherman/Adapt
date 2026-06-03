# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""MovieDialog — configure and create a MovieRecipe."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from adapt.consumers.console.workspace.models import MovieRecipe

__all__ = ["MovieDialog"]

_MOVIE_TYPES = ["scan_loop", "track_evolution", "lifecycle_build"]


class MovieDialog(QDialog):
    """Configure a MovieRecipe for rendering."""

    def __init__(
        self,
        selection_slugs: list[str],
        available_variables: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Movie")
        self.setMinimumWidth(360)

        form = QFormLayout()

        self._type_combo = QComboBox()
        self._type_combo.addItems(_MOVIE_TYPES)

        self._selection_combo = QComboBox()
        self._selection_combo.addItems(selection_slugs)

        self._var_combo = QComboBox()
        self._var_combo.addItems(available_variables)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 60)
        self._fps_spin.setValue(8)
        self._fps_spin.setSuffix(" fps")

        self._before_spin = QSpinBox()
        self._before_spin.setRange(0, 20)
        self._before_spin.setValue(4)

        self._after_spin = QSpinBox()
        self._after_spin.setRange(0, 20)
        self._after_spin.setValue(4)

        form.addRow("Movie type:", self._type_combo)
        form.addRow("Selection:", self._selection_combo)
        form.addRow("Variable:", self._var_combo)
        form.addRow("FPS:", self._fps_spin)
        form.addRow("Frames before peak:", self._before_spin)
        form.addRow("Frames after peak:", self._after_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def current_recipe(self) -> MovieRecipe:
        return MovieRecipe(
            movie_type=self._type_combo.currentText(),
            selection_slug=self._selection_combo.currentText(),
            cell_uid=None,
            variable=(
                self._var_combo.currentText() if self._var_combo.count() > 0 else "reflectivity"
            ),
            fps=self._fps_spin.value(),
            n_frames_before=self._before_spin.value(),
            n_frames_after=self._after_spin.value(),
        )
