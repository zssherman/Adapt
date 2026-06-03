# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""DerivedVariableDialog — expression editor for user-defined computed columns."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from adapt.consumers.analysis.derived import DerivedVariableSpec, validate_expression

__all__ = ["DerivedVariableDialog"]


class DerivedVariableDialog(QDialog):
    """Edit a DerivedVariableSpec (name, expression, description)."""

    def __init__(
        self,
        available_columns: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Derived Variable")
        self.setMinimumWidth(420)
        self._available_columns = available_columns

        form = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. growth_rate")

        self._expr_edit = QLineEdit()
        self._expr_edit.setPlaceholderText("e.g. area.diff() / 300")
        self._expr_edit.textChanged.connect(self._validate)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Optional description")

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")

        form.addRow("Name:", self._name_edit)
        form.addRow("Expression:", self._expr_edit)
        form.addRow("Description:", self._desc_edit)
        form.addRow("", self._error_label)

        available_hint = QLabel(f"Available: {', '.join(available_columns)}")
        available_hint.setStyleSheet("color: gray; font-size: 10px;")

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(available_hint)
        layout.addWidget(self._buttons)

    def set_name(self, name: str) -> None:
        self._name_edit.setText(name)

    def set_expression(self, expression: str) -> None:
        self._expr_edit.setText(expression)

    def current_spec(self) -> DerivedVariableSpec | None:
        name = self._name_edit.text().strip()
        expr = self._expr_edit.text().strip()
        if not name or not expr:
            return None
        return DerivedVariableSpec(
            name=name,
            expression=expr,
            description=self._desc_edit.text().strip(),
        )

    def _validate(self, expression: str) -> None:
        if not expression.strip():
            self._error_label.setText("")
            return
        errors = validate_expression(expression, self._available_columns)
        self._error_label.setText("; ".join(errors) if errors else "✓ Valid")
