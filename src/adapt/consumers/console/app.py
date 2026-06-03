# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""ADAPT Console — MainWindow and application entry point."""

from __future__ import annotations

import sys
from datetime import UTC
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableView,
    QTabWidget,
    QWidget,
)

from adapt.api import RepositoryClient
from adapt.consumers.console.context import NavigationContext
from adapt.consumers.console.panels.explorer import WorkspaceExplorer
from adapt.consumers.console.panels.log_panel import LogPanel
from adapt.consumers.console.panels.properties import PropertiesPanel
from adapt.consumers.console.panels.track_detail import TrackDetailView
from adapt.consumers.console.panels.track_table import TrackTableModel
from adapt.consumers.console.workspace.manager import WorkspaceManager

__all__ = ["MainWindow", "run_console"]


class MainWindow(QMainWindow):
    """ADAPT Console main window with docking panel layout."""

    def __init__(
        self,
        workspace_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = NavigationContext(self)

        ws_path = Path(workspace_path) if workspace_path else Path.home() / ".adapt" / "console"
        self._workspace = WorkspaceManager.open(ws_path)
        self._ws_path = ws_path

        self._client: RepositoryClient | None = None
        self._active_run_id: str | None = None
        self._active_tracks: pd.DataFrame | None = None
        self._track_table_model: TrackTableModel | None = None

        self.setWindowTitle(f"ADAPT Console — {ws_path.name}")
        self.resize(1400, 900)

        # ── Central widget: tab bar ──────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.setCentralWidget(self._tabs)

        placeholder = QLabel(
            "<center>"
            "<h2>Welcome to ADAPT Console</h2>"
            "<p>Use <b>File → Open Workspace</b> to open an existing project,<br>"
            "or <b>File → New Workspace</b> to create one.</p>"
            "<p>Then use <b>Selection → New Selection</b> to filter tracks,<br>"
            "and <b>Analysis → Show Population</b> / <b>Show Lifecycle</b> to explore them.</p>"
            "</center>"
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setTextFormat(Qt.TextFormat.RichText)
        self._tabs.addTab(placeholder, "Welcome")
        self._tabs.tabBar().setTabButton(0, self._tabs.tabBar().ButtonPosition.RightSide, None)

        # ── Left dock: WorkspaceExplorer ─────────────────────────────────────
        self._explorer = WorkspaceExplorer(self.ctx)
        self._explorer_dock = QDockWidget("Workspace", self)
        self._explorer_dock.setWidget(self._explorer)
        self._explorer_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._explorer_dock)

        # ── Right dock: PropertiesPanel ──────────────────────────────────────
        self._properties = PropertiesPanel(self.ctx)
        self._props_dock = QDockWidget("Properties", self)
        self._props_dock.setWidget(self._properties)
        self._props_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._props_dock)

        # ── Bottom dock: LogPanel ────────────────────────────────────────────
        self._log = LogPanel()
        self._log_dock = QDockWidget("Log", self)
        self._log_dock.setWidget(self._log)
        self._log_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)

        # ── Bottom dock: Track Table ─────────────────────────────────────────
        self._track_table_view = QTableView()
        self._track_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._track_table_view.setAlternatingRowColors(True)
        self._track_dock = QDockWidget("Tracks", self)
        self._track_dock.setWidget(self._track_table_view)
        self._track_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._track_dock)
        self.splitDockWidget(self._log_dock, self._track_dock, Qt.Orientation.Horizontal)

        # ── Bottom dock: Track Detail ────────────────────────────────────────
        self._track_detail = TrackDetailView(self.ctx)
        self._track_detail_dock = QDockWidget("Track Detail", self)
        self._track_detail_dock.setWidget(self._track_detail)
        self._track_detail_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._track_detail_dock)
        self.tabifyDockWidget(self._track_dock, self._track_detail_dock)

        # ── Menu bar ────────────────────────────────────────────────────────
        self._build_menus()

        # ── Toolbar ─────────────────────────────────────────────────────────
        self._build_toolbar()

        # ── Signal connections ───────────────────────────────────────────────
        self.ctx.run_activated.connect(self._on_run_activated)
        self.ctx.selection_activated.connect(self._on_selection_activated)
        self._track_table_view.clicked.connect(self._on_track_row_clicked)

        # ── Load workspace content ───────────────────────────────────────────
        self._refresh_explorer()
        self._restore_session()
        self._log.append(f"Workspace: {ws_path}")

    # ── Menu construction ────────────────────────────────────────────────────

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        file_menu.addAction(
            self._action("&New Workspace…", self._new_workspace, shortcut="Ctrl+Shift+N")
        )
        file_menu.addAction(
            self._action("&Open Workspace…", self._open_workspace, shortcut="Ctrl+O")
        )
        file_menu.addSeparator()
        file_menu.addAction(
            self._action(
                "&Connect Repository…",
                self._connect_repository,
                shortcut="Ctrl+Shift+A",
                tip="Connect to an ADAPT repository and discover runs",
            )
        )
        file_menu.addSeparator()
        file_menu.addAction(self._action("E&xport Selection to CSV…", self._export_csv))
        file_menu.addAction(self._action("Export Selection to &Parquet…", self._export_parquet))
        file_menu.addSeparator()
        file_menu.addAction(self._action("&Quit", self.close, shortcut="Ctrl+Q"))

        # Selection
        sel_menu = mb.addMenu("&Selection")
        sel_menu.addAction(
            self._action(
                "&New Selection…",
                self._new_selection,
                shortcut="Ctrl+N",
                tip="Filter tracks by lifetime, area, reflectivity…",
            )
        )
        sel_menu.addAction(self._action("&Duplicate Selection…", self._duplicate_selection))
        sel_menu.addSeparator()
        sel_menu.addAction(self._action("Intersection (A ∩ B)…", self._set_intersection))
        sel_menu.addAction(self._action("Union (A ∪ B)…", self._set_union))
        sel_menu.addAction(self._action("Difference (A − B)…", self._set_difference))
        sel_menu.addSeparator()
        sel_menu.addAction(self._action("&Delete Selection", self._delete_selection))

        # Analysis
        analysis_menu = mb.addMenu("&Analysis")
        analysis_menu.addAction(
            self._action("Show &Population View", self._open_population, shortcut="Ctrl+1")
        )
        analysis_menu.addAction(
            self._action("Show &Lifecycle View", self._open_lifecycle, shortcut="Ctrl+2")
        )
        analysis_menu.addAction(
            self._action("Show &Comparison View", self._open_comparison, shortcut="Ctrl+3")
        )
        analysis_menu.addSeparator()
        analysis_menu.addAction(self._action("New Derived &Variable…", self._new_derived_variable))

        # Figures
        fig_menu = mb.addMenu("Fi&gures")
        fig_menu.addAction(
            self._action(
                "&Render Figure…",
                self._render_figure,
                shortcut="Ctrl+R",
                tip="Configure and render a figure to PNG",
            )
        )

        # Movies
        mov_menu = mb.addMenu("&Movies")
        mov_menu.addAction(
            self._action(
                "&Render Movie…",
                self._render_movie,
                tip="Configure and render a scan loop or track evolution",
            )
        )

        # View
        view_menu = mb.addMenu("&View")
        view_menu.addAction(self._explorer_dock.toggleViewAction())
        view_menu.addAction(self._props_dock.toggleViewAction())
        view_menu.addAction(self._log_dock.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(
            self._action("&Refresh Workspace", self._refresh_explorer, shortcut="F5")
        )

        # Help
        help_menu = mb.addMenu("&Help")
        help_menu.addAction(self._action("&About ADAPT Console", self._about))

    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Main")
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        tb.addAction(
            self._action("New Selection", self._new_selection, tip="New Selection (Ctrl+N)")
        )
        tb.addAction(
            self._action(
                "Connect Repository",
                self._connect_repository,
                tip="Connect to ADAPT repository (Ctrl+Shift+A)",
            )
        )
        tb.addSeparator()
        tb.addAction(
            self._action("Population", self._open_population, tip="Open Population View (Ctrl+1)")
        )
        tb.addAction(
            self._action("Lifecycle", self._open_lifecycle, tip="Open Lifecycle View (Ctrl+2)")
        )
        tb.addAction(
            self._action("Comparison", self._open_comparison, tip="Open Comparison View (Ctrl+3)")
        )
        tb.addSeparator()
        tb.addAction(
            self._action("Render Figure", self._render_figure, tip="Render Figure to PNG (Ctrl+R)")
        )
        tb.addAction(
            self._action(
                "Render Movie", self._render_movie, tip="Render Movie (scan loop / track evolution)"
            )
        )

    def _action(
        self,
        label: str,
        slot,
        shortcut: str | None = None,
        tip: str | None = None,
    ) -> QAction:
        act = QAction(label, self)
        act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        if tip:
            act.setStatusTip(tip)
            act.setToolTip(tip)
        return act

    # ── File actions ────────────────────────────────────────────────────────

    def _new_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose or create workspace directory")
        if path:
            self._workspace.close()
            self._ws_path = Path(path)
            self._workspace = WorkspaceManager.open(self._ws_path)
            self.setWindowTitle(f"ADAPT Console — {self._ws_path.name}")
            self._refresh_explorer()
            self._log.append(f"Workspace: {self._ws_path}")

    def _open_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open existing workspace directory")
        if path:
            self._workspace.close()
            self._ws_path = Path(path)
            self._workspace = WorkspaceManager.open(self._ws_path)
            self.setWindowTitle(f"ADAPT Console — {self._ws_path.name}")
            self._refresh_explorer()
            self._log.append(f"Opened workspace: {self._ws_path}")

    def _connect_repository(self) -> None:
        """Connect to an ADAPT repository and auto-discover all runs."""
        path = QFileDialog.getExistingDirectory(
            self, "Select ADAPT repository root (folder containing adapt_registry.db)"
        )
        if not path:
            return
        repo_path = Path(path)
        registry = repo_path / "adapt_registry.db"
        if not registry.exists():
            QMessageBox.critical(
                self,
                "Not a repository",
                f"No adapt_registry.db found in:\n{repo_path}\n\n"
                "Select the directory that contains adapt_registry.db.",
            )
            return
        try:
            client = RepositoryClient(repo_path)
            runs = client.runs()
            client.close()
        except Exception as exc:
            QMessageBox.critical(self, "Repository error", str(exc))
            return
        if not runs:
            QMessageBox.information(self, "No runs", f"No runs found in {repo_path}")
            return
        added = 0
        for run in runs:
            self._workspace.add_run(run.run_id, run.radar_id, str(repo_path))
            added += 1
        self._refresh_explorer()
        self._log.append(
            f"Connected to {repo_path.name}: found {added} run(s) "
            f"({', '.join(r.run_id for r in runs)})"
        )

    def _export_csv(self) -> None:
        sel = self._active_selection_slug()
        if sel is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", f"{sel}.csv", "CSV files (*.csv)"
        )
        if path:
            self._do_export(sel, Path(path), "csv")

    def _export_parquet(self) -> None:
        sel = self._active_selection_slug()
        if sel is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to Parquet", f"{sel}.parquet", "Parquet files (*.parquet)"
        )
        if path:
            self._do_export(sel, Path(path), "parquet")

    def _do_export(self, slug: str, out: Path, fmt: str) -> None:
        try:
            import pandas as pd

            tracks_path = self._ws_path / "selections" / slug / "tracks.parquet"
            if not tracks_path.exists():
                QMessageBox.warning(
                    self,
                    "Export",
                    f"No materialised data for '{slug}'.\n"
                    "The selection has not been loaded from the repository yet.",
                )
                return
            df = pd.read_parquet(tracks_path)
            from adapt.consumers.console.workspace.export import export_csv, export_parquet

            if fmt == "csv":
                export_csv(df, out)
            else:
                export_parquet(df, out)
            self._log.append(f"Exported '{slug}' → {out}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    # ── Selection actions ────────────────────────────────────────────────────

    def _new_selection(self) -> None:
        run_ids = [r["run_id"] for r in self._workspace.list_runs()]
        if not run_ids:
            QMessageBox.information(
                self,
                "No Runs",
                "No runs in this workspace yet.\n\nUse File → Connect Repository to discover runs.",
            )
            return

        run_id, ok = QInputDialog.getItem(self, "New Selection", "Run:", run_ids, editable=False)
        if not ok:
            return

        slug, ok2 = QInputDialog.getText(self, "New Selection", "Selection name (slug):")
        if not ok2 or not slug.strip():
            return

        from adapt.consumers.console.dialogs.selection import SelectionDialog

        dlg = SelectionDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        from datetime import datetime

        from adapt.consumers.console.workspace.models import NamedSelection

        now = datetime.now(tz=UTC)
        selection = NamedSelection(
            slug=slug.strip(),
            display_name=slug.strip(),
            run_id=run_id,
            criteria=dlg.current_spec(),
            parent_a_slug=None,
            parent_b_slug=None,
            set_op=None,
            track_count=None,
            created_at=now,
            updated_at=now,
        )
        self._workspace.save_selection(selection)
        self._refresh_explorer()
        self._log.append(f"Created selection: {slug.strip()}")

    def _duplicate_selection(self) -> None:
        slug = self._active_selection_slug()
        if slug is None:
            return
        new_slug, ok = QInputDialog.getText(
            self, "Duplicate Selection", f"New name (copy of '{slug}'):"
        )
        if not ok or not new_slug.strip():
            return
        try:
            sel = self._workspace.load_selection(slug)
            from datetime import datetime

            from adapt.consumers.console.workspace.models import NamedSelection

            now = datetime.now(tz=UTC)
            dup = NamedSelection(
                slug=new_slug.strip(),
                display_name=new_slug.strip(),
                run_id=sel.run_id,
                criteria=sel.criteria,
                parent_a_slug=None,
                parent_b_slug=None,
                set_op=None,
                track_count=None,
                created_at=now,
                updated_at=now,
            )
            self._workspace.save_selection(dup)
            self._refresh_explorer()
        except Exception as exc:
            QMessageBox.critical(self, "Duplicate failed", str(exc))

    def _set_intersection(self) -> None:
        self._do_set_op("intersection")

    def _set_union(self) -> None:
        self._do_set_op("union")

    def _set_difference(self) -> None:
        self._do_set_op("difference")

    def _do_set_op(self, op: str) -> None:
        sels = self._workspace.list_selections()
        slugs = [s.slug for s in sels]
        if len(slugs) < 2:
            QMessageBox.information(self, "Set Operation", "Need at least two saved selections.")
            return
        a, ok1 = QInputDialog.getItem(
            self, f"Set {op.title()}", "Selection A:", slugs, editable=False
        )
        if not ok1:
            return
        b, ok2 = QInputDialog.getItem(
            self, f"Set {op.title()}", "Selection B:", slugs, editable=False
        )
        if not ok2:
            return
        try:
            sel_a = self._workspace.load_selection(a)
            sel_b = self._workspace.load_selection(b)
            if op == "intersection":
                result = sel_a & sel_b
            elif op == "union":
                result = sel_a | sel_b
            else:
                result = sel_a - sel_b
            self._workspace.save_selection(result)
            self._refresh_explorer()
            self._log.append(f"Created {op}: {result.slug}")
        except ValueError as exc:
            QMessageBox.warning(self, "Set Operation failed", str(exc))

    def _delete_selection(self) -> None:
        slug = self._active_selection_slug()
        if slug is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete Selection",
            f"Delete '{slug}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._workspace.delete_selection(slug)
            self._refresh_explorer()
            self._log.append(f"Deleted selection: {slug}")

    # ── Analysis actions ─────────────────────────────────────────────────────

    def _open_population(self) -> None:
        from adapt.consumers.console.views.population import PopulationView

        view = PopulationView(self.ctx)
        self._tabs.addTab(view, "Population")
        self._tabs.setCurrentWidget(view)
        if self._active_tracks is not None and not self._active_tracks.empty:
            view.load_tracks(self._active_tracks)
            self._log.append(f"Population view: {len(self._active_tracks)} tracks")
        else:
            self._log.append("Population view opened — connect a repository and click a run")

    def _open_lifecycle(self) -> None:
        from adapt.consumers.console.views.lifecycle import LifecycleView

        view = LifecycleView(self.ctx)
        self._tabs.addTab(view, "Lifecycle")
        self._tabs.setCurrentWidget(view)
        if self._client is None or self._active_tracks is None or self._active_tracks.empty:
            self._log.append("Lifecycle view opened — connect a repository and click a run")
            return
        run_id = self._active_run_id
        if run_id is None:
            return
        cell_uids = self._active_tracks["cell_uid"].tolist()
        self._log.append(f"Fetching histories for {len(cell_uids)} tracks…")
        try:
            histories = pd.concat(
                [self._client.track_history(run_id, uid) for uid in cell_uids],
                ignore_index=True,
            )
            view.load_histories(histories, n_tracks=len(cell_uids))
            self._log.append(f"Lifecycle view: {len(histories)} scan observations")
        except Exception as exc:
            self._log.append(f"History fetch failed: {exc}")

    def _open_comparison(self) -> None:
        from adapt.consumers.console.views.comparison import ComparisonView

        view = ComparisonView(self.ctx)
        self._tabs.addTab(view, "Comparison")
        self._tabs.setCurrentWidget(view)
        self._log.append("Opened Comparison View")

    def _new_derived_variable(self) -> None:
        from adapt.consumers.console.dialogs.derived_variable import DerivedVariableDialog

        dlg = DerivedVariableDialog(
            available_columns=["area", "reflectivity", "lifetime_s", "n_scans"],
            parent=self,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            spec = dlg.current_spec()
            if spec:
                self._log.append(f"Derived variable defined: {spec.name} = {spec.expression}")

    # ── Figure / Movie actions ────────────────────────────────────────────────

    def _render_figure(self) -> None:
        sels = self._workspace.list_selections()
        slugs = [s.slug for s in sels]
        if not slugs:
            QMessageBox.information(self, "Render Figure", "No selections yet. Create one first.")
            return
        from adapt.consumers.console.dialogs.figure import FigureDialog

        dlg = FigureDialog(
            selection_slugs=slugs,
            available_variables=["area", "max_reflectivity_dbz", "lifetime_s", "n_scans"],
            parent=self,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            recipe = dlg.current_recipe()
            if self._client is None:
                QMessageBox.warning(
                    self, "No Active Run", "Select a run first (click it in the Workspace tree)."
                )
                return
            try:
                from adapt.consumers.console.workspace.executor import RecipeExecutor

                out_path = RecipeExecutor().render_figure(recipe, self._workspace, self._client)
                self._log.append(f"Rendered: {out_path.name}")
                self._refresh_explorer()
            except Exception as exc:
                QMessageBox.critical(self, "Render failed", str(exc))

    def _render_movie(self) -> None:
        sels = self._workspace.list_selections()
        slugs = [s.slug for s in sels]
        if not slugs:
            QMessageBox.information(self, "Render Movie", "No selections yet. Create one first.")
            return
        from adapt.consumers.console.dialogs.movie import MovieDialog

        dlg = MovieDialog(
            selection_slugs=slugs,
            available_variables=["reflectivity", "area", "velocity"],
            parent=self,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            recipe = dlg.current_recipe()
            self._log.append(f"Movie recipe: {recipe.movie_type}, {recipe.fps} fps")

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _active_selection_slug(self) -> str | None:
        sels = self._workspace.list_selections()
        if not sels:
            QMessageBox.information(self, "No Selection", "No selections in this workspace yet.")
            return None
        slugs = [s.slug for s in sels]
        slug, ok = QInputDialog.getItem(
            self, "Choose Selection", "Selection:", slugs, editable=False
        )
        return slug if ok else None

    def _refresh_explorer(self) -> None:
        runs = self._workspace.list_runs()
        self._explorer.set_runs([r["run_id"] for r in runs])

        sels = self._workspace.list_selections()
        self._explorer.set_selections([s.slug for s in sels])

        figs = self._workspace.list_figures()
        self._explorer.set_figures([f["slug"] for f in figs])

    def _on_tab_close_requested(self, index: int) -> None:
        if index == 0:
            return
        self._tabs.removeTab(index)

    def _on_run_activated(self, run_id: str) -> None:
        try:
            row = self._workspace.get_run(run_id)
        except KeyError:
            self._log.append(f"Run not found: {run_id}")
            return
        self._active_run_id = run_id
        try:
            self._client = RepositoryClient(row["repo_path"])
        except Exception as exc:
            QMessageBox.critical(self, "Repository error", str(exc))
            return
        self._track_detail.set_client(self._client)
        self._log.append(f"Active run: {run_id} ({row['radar_id']})")
        try:
            df = self._client.tracks(run_id)
            self._load_tracks_into_table(df)
            self._log.append(f"Loaded {len(df)} tracks")
        except Exception as exc:
            self._log.append(f"Could not load tracks: {exc}")

    def _load_tracks_into_table(self, df: pd.DataFrame) -> None:
        self._active_tracks = df
        self._track_table_model = TrackTableModel(df)
        self._track_table_view.setModel(self._track_table_model)
        self._track_table_view.resizeColumnsToContents()

    def _on_selection_activated(self, slug: object) -> None:
        try:
            sel = self._workspace.load_selection(str(slug))
        except KeyError:
            return
        self._properties.show_selection(sel.slug, run_id=sel.run_id, track_count=sel.track_count)
        self._log.append(f"Selection active: {slug}")
        if self._client is None:
            self._log.append("No active run — click a run in the Workspace tree first")
            return
        try:
            df = self._client.select(sel.run_id, sel.criteria)
            self._load_tracks_into_table(df)
            sel.track_count = len(df)
            self._workspace.save_selection(sel)
            self._properties.show_selection(sel.slug, run_id=sel.run_id, track_count=len(df))
            self._log.append(f"{len(df)} tracks match '{slug}'")
        except Exception as exc:
            self._log.append(f"Could not filter tracks: {exc}")

    def _on_track_row_clicked(self, index) -> None:
        if self._active_tracks is None or self._active_run_id is None:
            return
        row = index.row()
        if row < 0 or row >= len(self._active_tracks):
            return
        cell_uid = str(self._active_tracks.iloc[row].get("cell_uid", ""))
        if cell_uid:
            self.ctx.track_focused.emit(self._active_run_id, cell_uid)

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About ADAPT Console",
            "<b>ADAPT Console</b><br>"
            "Scientific analysis workbench for atmospheric object tracking datasets.<br><br>"
            "The central object is the <b>Selection</b> — a named, filtered subset of tracks "
            "from a pipeline run.<br><br>"
            "Workflow:<br>"
            "1. <b>File → Connect Repository</b> — select the folder with adapt_registry.db<br>"
            "2. <b>Selection → New Selection</b> — filter by lifetime, area, reflectivity…<br>"
            "3. <b>Analysis →</b> open Population, Lifecycle, or Comparison views<br>"
            "4. <b>Figures / Movies →</b> render to PNG or MP4",
        )

    def _restore_session(self) -> None:
        import json as _json

        run_id_json = self._workspace._db.get_session("active_run_id")
        if run_id_json:
            try:
                run_id = _json.loads(run_id_json)
                if run_id:
                    self._on_run_activated(run_id)
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        import json as _json

        if self._active_run_id is not None:
            self._workspace._db.set_session("active_run_id", _json.dumps(self._active_run_id))
        self._workspace.close()
        super().closeEvent(event)


def run_console(workspace: str | None = None) -> None:
    """Launch the ADAPT Console application."""
    from PySide6.QtCore import Qt as _Qt

    app = QApplication.instance() or QApplication(sys.argv)
    app.setAttribute(_Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    win = MainWindow(workspace_path=Path(workspace) if workspace else None)
    win.show()
    sys.exit(app.exec())
