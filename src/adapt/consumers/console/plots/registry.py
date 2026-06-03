# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""FigureTypeRegistry — plug-in registration for console figure types."""

from __future__ import annotations

__all__ = ["FigureTypeRegistry", "RegistrationError"]

_REQUIRED_ATTRS = ("type_key", "display_name", "required_variables")
_REQUIRED_METHODS = ("compute", "render")


class RegistrationError(Exception):
    """Raised when a figure type is invalid or duplicated."""


class FigureTypeRegistry:
    """Registry of figure types.

    Each entry must expose:
    - ``type_key`` (str)
    - ``display_name`` (str)
    - ``required_variables`` (list[str])
    - ``compute(client, tracks_df, options) -> Any``
    - ``render(result, output_path, style) -> Path``
    """

    def __init__(self) -> None:
        self._types: dict[str, object] = {}

    def register(self, figure_type: object) -> None:
        """Register a figure type.

        Raises
        ------
        RegistrationError
            If protocol is incomplete or ``type_key`` is already registered.
        """
        for attr in _REQUIRED_ATTRS:
            if not hasattr(figure_type, attr):
                raise RegistrationError(
                    f"Figure type missing required attribute '{attr}': {figure_type!r}"
                )
        for method in _REQUIRED_METHODS:
            if not hasattr(figure_type, method) or not callable(getattr(figure_type, method)):
                raise RegistrationError(
                    f"Figure type missing required method '{method}': {figure_type!r}"
                )

        key = figure_type.type_key  # type: ignore[attr-defined]
        if key in self._types:
            raise RegistrationError(
                f"Figure type '{key}' is already registered. Unregister it before re-registering."
            )
        self._types[key] = figure_type

    def get(self, type_key: str) -> object:
        """Retrieve a registered figure type by key.

        Raises
        ------
        KeyError
            If *type_key* is not registered.
        """
        if type_key not in self._types:
            raise KeyError(
                f"No figure type registered for key '{type_key}'. Available: {sorted(self._types)}"
            )
        return self._types[type_key]

    def keys(self) -> list[str]:
        return list(self._types.keys())

    def __len__(self) -> int:
        return len(self._types)
