# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Workspace SQLite database — schema creation and CRUD primitives."""

from __future__ import annotations

import sqlite3
from pathlib import Path

__all__ = ["CURRENT_VERSION", "WorkspaceDB"]

CURRENT_VERSION = 1

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_runs (
    run_id      TEXT PRIMARY KEY,
    radar_id    TEXT NOT NULL,
    repo_path   TEXT NOT NULL,
    label       TEXT,
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS selections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    run_id          TEXT NOT NULL REFERENCES workspace_runs(run_id),
    criteria_json   TEXT NOT NULL,
    parent_a_slug   TEXT,
    parent_b_slug   TEXT,
    set_op          TEXT CHECK(set_op IN ('intersection','union','difference') OR set_op IS NULL),
    track_count     INTEGER,
    materialized_at TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS derived_variables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    expression  TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS figures (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    slug           TEXT UNIQUE NOT NULL,
    display_name   TEXT NOT NULL,
    selection_slug TEXT REFERENCES selections(slug),
    figure_type    TEXT NOT NULL,
    recipe_json    TEXT NOT NULL,
    style          TEXT NOT NULL DEFAULT 'screen',
    file_path      TEXT,
    rendered_at    TIMESTAMP,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movies (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    slug           TEXT UNIQUE NOT NULL,
    display_name   TEXT NOT NULL,
    selection_slug TEXT REFERENCES selections(slug),
    movie_type     TEXT NOT NULL,
    recipe_json    TEXT NOT NULL,
    file_path      TEXT,
    rendered_at    TIMESTAMP,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS annotations (
    run_id      TEXT NOT NULL,
    cell_uid    TEXT NOT NULL,
    ann_type    TEXT NOT NULL,
    value       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, cell_uid, ann_type, value)
);

CREATE TABLE IF NOT EXISTS session (
    key         TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL
);
"""


class WorkspaceDB:
    """Low-level SQLite access for the Console workspace."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._initialise()

    def _initialise(self) -> None:
        self._conn.executescript(_DDL)
        # Write schema version only if table is empty
        row = self._conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,)
            )
            self._conn.commit()

    # ── Introspection ──────────────────────────────────────────────────────

    def schema_version(self) -> int:
        row = self._conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        return int(row["version"])

    def table_names(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def journal_mode(self) -> str:
        row = self._conn.execute("PRAGMA journal_mode").fetchone()
        return row[0]

    # ── Runs ────────────────────────────────────────────────────────────────

    def add_run(
        self,
        run_id: str,
        radar_id: str,
        repo_path: str,
        label: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO workspace_runs (run_id, radar_id, repo_path, label)"
            " VALUES (?, ?, ?, ?)",
            (run_id, radar_id, repo_path, label),
        )
        self._conn.commit()

    def list_runs(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT run_id, radar_id, repo_path, label, added_at FROM workspace_runs"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict:
        row = self._conn.execute(
            "SELECT run_id, radar_id, repo_path, label, added_at FROM workspace_runs"
            " WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    # ── Selections ──────────────────────────────────────────────────────────

    def save_selection(
        self,
        slug: str,
        display_name: str,
        run_id: str,
        criteria_json: str,
        parent_a_slug: str | None = None,
        parent_b_slug: str | None = None,
        set_op: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO selections
              (slug, display_name, run_id, criteria_json, parent_a_slug, parent_b_slug, set_op,
               updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (slug, display_name, run_id, criteria_json, parent_a_slug, parent_b_slug, set_op),
        )
        self._conn.commit()

    def get_selection(self, slug: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM selections WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None

    def list_selections(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM selections ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def set_selection_track_count(self, slug: str, count: int) -> None:
        self._conn.execute(
            "UPDATE selections SET track_count = ?, materialized_at = CURRENT_TIMESTAMP"
            " WHERE slug = ?",
            (count, slug),
        )
        self._conn.commit()

    def delete_selection(self, slug: str) -> None:
        self._conn.execute("DELETE FROM selections WHERE slug = ?", (slug,))
        self._conn.commit()

    # ── Figures ─────────────────────────────────────────────────────────────

    def save_figure(
        self,
        slug: str,
        display_name: str,
        selection_slug: str,
        figure_type: str,
        recipe_json: str,
        style: str,
        file_path: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO figures
              (slug, display_name, selection_slug, figure_type, recipe_json, style,
               file_path, rendered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (slug, display_name, selection_slug, figure_type, recipe_json, style, file_path),
        )
        self._conn.commit()

    def list_figures(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM figures ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    # ── Session ─────────────────────────────────────────────────────────────

    def set_session(self, key: str, value_json: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO session (key, value_json) VALUES (?, ?)",
            (key, value_json),
        )
        self._conn.commit()

    def get_session(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value_json FROM session WHERE key = ?", (key,)).fetchone()
        return row["value_json"] if row else None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> WorkspaceDB:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
