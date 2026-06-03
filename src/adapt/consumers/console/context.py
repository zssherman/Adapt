# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""NavigationContext — cross-panel signal bus."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

__all__ = ["NavigationContext"]


class NavigationContext(QObject):
    """Central signal bus that coordinates cross-panel navigation.

    One instance per application. Injected into every panel and view.
    All cross-panel communication flows through here — no direct panel
    references.

    Signals
    -------
    track_focused(run_id: str, cell_uid: str)
        User focused on a specific track.
    scan_requested(run_id: str, cell_uid: str, scan_time: object)
        User wants to open a scan at a given time.
    selection_activated(selection: object)
        A NamedSelection became the active selection.
    """

    run_activated = Signal(str)
    track_focused = Signal(str, str)
    scan_requested = Signal(str, str, object)
    selection_activated = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
