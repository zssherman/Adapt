# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Workspace domain models — NamedSelection, FigureRecipe, MovieRecipe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from adapt.api.selection import FilterSpec

__all__ = ["NamedSelection", "FigureRecipe", "MovieRecipe"]


@dataclass
class NamedSelection:
    """A named, persisted subset of tracks from a single run.

    Set operations (& | -) produce new NamedSelection instances that are
    not yet persisted (track_count is None, set_op is filled).
    """

    slug: str
    display_name: str
    run_id: str
    criteria: FilterSpec
    parent_a_slug: str | None
    parent_b_slug: str | None
    set_op: str | None
    track_count: int | None
    created_at: datetime
    updated_at: datetime

    def __and__(self, other: NamedSelection) -> NamedSelection:
        self._assert_same_run(other)
        return NamedSelection(
            slug=f"{self.slug}_and_{other.slug}",
            display_name=f"{self.display_name} ∩ {other.display_name}",
            run_id=self.run_id,
            criteria=self.criteria,
            parent_a_slug=self.slug,
            parent_b_slug=other.slug,
            set_op="intersection",
            track_count=None,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )

    def __or__(self, other: NamedSelection) -> NamedSelection:
        self._assert_same_run(other)
        return NamedSelection(
            slug=f"{self.slug}_or_{other.slug}",
            display_name=f"{self.display_name} ∪ {other.display_name}",
            run_id=self.run_id,
            criteria=self.criteria,
            parent_a_slug=self.slug,
            parent_b_slug=other.slug,
            set_op="union",
            track_count=None,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )

    def __sub__(self, other: NamedSelection) -> NamedSelection:
        self._assert_same_run(other)
        return NamedSelection(
            slug=f"{self.slug}_not_{other.slug}",
            display_name=f"{self.display_name} \\ {other.display_name}",
            run_id=self.run_id,
            criteria=self.criteria,
            parent_a_slug=self.slug,
            parent_b_slug=other.slug,
            set_op="difference",
            track_count=None,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )

    def _assert_same_run(self, other: NamedSelection) -> None:
        if self.run_id != other.run_id:
            raise ValueError(
                f"Cannot combine selections from different runs: "
                f"'{self.run_id}' vs '{other.run_id}'"
            )


@dataclass(frozen=True)
class FigureRecipe:
    """Specification for generating a figure from a named selection."""

    figure_type: str
    selection_slug: str
    variables: tuple[str, ...]
    options: dict
    style: str = "screen"

    def to_dict(self) -> dict:
        return {
            "figure_type": self.figure_type,
            "selection_slug": self.selection_slug,
            "variables": list(self.variables),
            "options": self.options,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FigureRecipe:
        return cls(
            figure_type=d["figure_type"],
            selection_slug=d["selection_slug"],
            variables=tuple(d["variables"]),
            options=d["options"],
            style=d.get("style", "screen"),
        )


@dataclass(frozen=True)
class MovieRecipe:
    """Specification for generating a movie from a named selection."""

    movie_type: str
    selection_slug: str
    cell_uid: str | None
    variable: str
    n_frames_before: int = 4
    n_frames_after: int = 4
    fps: int = 8
    annotate_tracks: bool = True

    def to_dict(self) -> dict:
        return {
            "movie_type": self.movie_type,
            "selection_slug": self.selection_slug,
            "cell_uid": self.cell_uid,
            "variable": self.variable,
            "n_frames_before": self.n_frames_before,
            "n_frames_after": self.n_frames_after,
            "fps": self.fps,
            "annotate_tracks": self.annotate_tracks,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MovieRecipe:
        return cls(
            movie_type=d["movie_type"],
            selection_slug=d["selection_slug"],
            cell_uid=d.get("cell_uid"),
            variable=d["variable"],
            n_frames_before=d.get("n_frames_before", 4),
            n_frames_after=d.get("n_frames_after", 4),
            fps=d.get("fps", 8),
            annotate_tracks=d.get("annotate_tracks", True),
        )
