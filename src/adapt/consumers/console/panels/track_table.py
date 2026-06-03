# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""TrackTableModel — QAbstractTableModel backed by a pandas DataFrame."""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

__all__ = ["TrackTableModel"]

_ROOT = QModelIndex()


class TrackTableModel(QAbstractTableModel):
    """Read-only table model wrapping a tracks DataFrame.

    Designed for the central track table. The DataFrame is held in memory;
    for large datasets the caller should materialise a page before passing it.
    """

    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self._df = df.reset_index(drop=True)

    def rowCount(self, parent: QModelIndex = _ROOT) -> int:
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent: QModelIndex = _ROOT) -> int:
        if parent.isValid():
            return 0
        return len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._df.iloc[index.row(), index.column()]
            if hasattr(val, "item"):
                val = val.item()
            return str(val) if val is not None else ""
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(section)

    def replace(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df.reset_index(drop=True)
        self.endResetModel()
