# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""SelectionDialog — create/edit a FilterSpec interactively."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from adapt.api.selection import FilterSpec

__all__ = ["SelectionDialog"]

_UNSET = -1.0  # sentinel for "not set" in spinboxes


class SelectionDialog(QDialog):
    """Modal dialog for creating or editing a FilterSpec.

    Use :meth:`current_spec` to read the composed FilterSpec after
    the user accepts.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New / Edit Selection")
        self.setMinimumWidth(400)

        form = QFormLayout()

        self._lifetime_min = self._spin("s", minimum=0.0)
        self._lifetime_max = self._spin("s", minimum=0.0)
        self._n_scans_min = self._spin("", minimum=0.0, decimals=0)
        self._max_area_min = self._spin("km²", minimum=0.0)
        self._max_area_max = self._spin("km²", minimum=0.0)
        self._max_refl_min = self._spin("dBZ", minimum=-10.0, maximum=100.0)
        self._max_refl_max = self._spin("dBZ", minimum=-10.0, maximum=100.0)

        form.addRow("Lifetime min (s):", self._lifetime_min)
        form.addRow("Lifetime max (s):", self._lifetime_max)
        form.addRow("Min scans:", self._n_scans_min)
        form.addRow("Max area min (km²):", self._max_area_min)
        form.addRow("Max area max (km²):", self._max_area_max)
        form.addRow("Max refl min (dBZ):", self._max_refl_min)
        form.addRow("Max refl max (dBZ):", self._max_refl_max)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(
        suffix: str,
        minimum: float = _UNSET,
        maximum: float = 1e9,
        decimals: int = 1,
    ) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setSpecialValueText("—")
        sb.setMinimum(minimum)
        sb.setMaximum(maximum)
        sb.setDecimals(int(decimals))
        sb.setSuffix(f" {suffix}" if suffix else "")
        sb.setValue(minimum)  # default = "not set"
        return sb

    def current_spec(self) -> FilterSpec:
        """Return the FilterSpec described by the current widget values."""

        def _val(sb: QDoubleSpinBox) -> float | None:
            v = sb.value()
            return None if v == sb.minimum() else v

        n = _val(self._n_scans_min)
        return FilterSpec(
            lifetime_min_s=_val(self._lifetime_min),
            lifetime_max_s=_val(self._lifetime_max),
            n_scans_min=int(n) if n is not None else None,
            max_area_min_km2=_val(self._max_area_min),
            max_area_max_km2=_val(self._max_area_max),
            max_refl_min_dbz=_val(self._max_refl_min),
            max_refl_max_dbz=_val(self._max_refl_max),
        )

    def set_spec(self, spec: FilterSpec) -> None:
        """Populate dialog widgets from an existing FilterSpec."""
        self._set(self._lifetime_min, spec.lifetime_min_s)
        self._set(self._lifetime_max, spec.lifetime_max_s)
        self._set(self._n_scans_min, float(spec.n_scans_min) if spec.n_scans_min else None)
        self._set(self._max_area_min, spec.max_area_min_km2)
        self._set(self._max_area_max, spec.max_area_max_km2)
        self._set(self._max_refl_min, spec.max_refl_min_dbz)
        self._set(self._max_refl_max, spec.max_refl_max_dbz)

    def _set(self, sb: QDoubleSpinBox, value: float | None) -> None:
        sb.setValue(value if value is not None else sb.minimum())

    def reset(self) -> None:
        """Reset all fields to "not set"."""
        for sb in (
            self._lifetime_min,
            self._lifetime_max,
            self._n_scans_min,
            self._max_area_min,
            self._max_area_max,
            self._max_refl_min,
            self._max_refl_max,
        ):
            sb.setValue(sb.minimum())
