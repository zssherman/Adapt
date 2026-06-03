# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""WorkspaceManager — high-level workspace operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from adapt.api.selection import FilterSpec
from adapt.consumers.console.workspace.database import WorkspaceDB
from adapt.consumers.console.workspace.models import NamedSelection

__all__ = ["WorkspaceManager"]

_SUBDIRS = ("selections", "figures", "movies", "exports", "cache", "logs", "notebooks")


class WorkspaceManager:
    """Opens or creates a workspace directory and exposes high-level operations."""

    def __init__(self, root: Path, db: WorkspaceDB) -> None:
        self._root = root
        self._db = db

    @classmethod
    def open(cls, root: Path) -> WorkspaceManager:
        """Open or create a workspace at *root*."""
        root.mkdir(parents=True, exist_ok=True)
        for sub in _SUBDIRS:
            (root / sub).mkdir(exist_ok=True)
        db = WorkspaceDB(root / "workspace.db")
        return cls(root, db)

    # ── Runs ────────────────────────────────────────────────────────────────

    def add_run(self, run_id: str, radar_id: str, repo_path: str, label: str | None = None) -> None:
        self._db.add_run(run_id, radar_id, repo_path, label)

    def list_runs(self) -> list[dict]:
        return self._db.list_runs()

    def get_run(self, run_id: str) -> dict:
        return self._db.get_run(run_id)

    # ── Selections ──────────────────────────────────────────────────────────

    def save_selection(self, selection: NamedSelection) -> None:
        criteria_json = _filter_spec_to_json(selection.criteria)
        self._db.save_selection(
            slug=selection.slug,
            display_name=selection.display_name,
            run_id=selection.run_id,
            criteria_json=criteria_json,
            parent_a_slug=selection.parent_a_slug,
            parent_b_slug=selection.parent_b_slug,
            set_op=selection.set_op,
        )
        if selection.track_count is not None:
            self._db.set_selection_track_count(selection.slug, selection.track_count)

    def load_selection(self, slug: str) -> NamedSelection:
        row = self._db.get_selection(slug)
        if row is None:
            raise KeyError(f"No selection with slug '{slug}' in workspace")
        criteria = _filter_spec_from_json(row["criteria_json"])
        return NamedSelection(
            slug=row["slug"],
            display_name=row["display_name"],
            run_id=row["run_id"],
            criteria=criteria,
            parent_a_slug=row.get("parent_a_slug"),
            parent_b_slug=row.get("parent_b_slug"),
            set_op=row.get("set_op"),
            track_count=row.get("track_count"),
            created_at=_parse_ts(row["created_at"]),
            updated_at=_parse_ts(row["updated_at"]),
        )

    def list_selections(self) -> list[NamedSelection]:
        rows = self._db.list_selections()
        return [
            NamedSelection(
                slug=r["slug"],
                display_name=r["display_name"],
                run_id=r["run_id"],
                criteria=_filter_spec_from_json(r["criteria_json"]),
                parent_a_slug=r.get("parent_a_slug"),
                parent_b_slug=r.get("parent_b_slug"),
                set_op=r.get("set_op"),
                track_count=r.get("track_count"),
                created_at=_parse_ts(r["created_at"]),
                updated_at=_parse_ts(r["updated_at"]),
            )
            for r in rows
        ]

    def delete_selection(self, slug: str) -> None:
        self._db.delete_selection(slug)

    # ── Figures ─────────────────────────────────────────────────────────────

    def list_figures(self) -> list[dict]:
        return self._db.list_figures()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> WorkspaceManager:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# FilterSpec ↔ JSON helpers
# ---------------------------------------------------------------------------


def _filter_spec_to_json(spec: FilterSpec) -> str:
    d: dict = {}
    for field_name in spec.__dataclass_fields__:  # type: ignore[attr-defined]
        val = getattr(spec, field_name)
        if val is None:
            continue
        if isinstance(val, frozenset):
            d[field_name] = sorted(val)
        elif hasattr(val, "isoformat"):
            d[field_name] = val.isoformat()
        else:
            d[field_name] = val
    return json.dumps(d)


def _filter_spec_from_json(json_str: str) -> FilterSpec:
    from datetime import datetime as _dt

    d = json.loads(json_str)
    kwargs: dict = {}
    for key, val in d.items():
        if key in ("origin_types", "termination_types", "required_tags"):
            kwargs[key] = frozenset(val)
        elif key in ("first_seen_after", "first_seen_before"):
            kwargs[key] = _dt.fromisoformat(val)
        else:
            kwargs[key] = val
    return FilterSpec(**kwargs)


def _parse_ts(value: str | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC)
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(tz=UTC)
