# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Radar scan rendering helpers — no Tk, no self references."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import contextily as ctx

    HAS_CTX = True
except ImportError:
    ctx = None
    HAS_CTX = False


@dataclass
class RenderConfig:
    """Snapshot of dashboard render-control state passed to drawing functions."""

    show_flow: bool
    bg_alpha: float
    max_proj_steps: int
    cfg: dict
    color_slots: list[str]
    selected_cells: dict[str, int] = field(default_factory=dict)  # uid → slot


def add_basemap(ax, ds, x_km, y_km) -> None:
    """Add an OpenStreetMap basemap to *ax* using the dataset's radar location.

    No-op when contextily is unavailable or the dataset has no lat/lon attrs.
    """
    if not HAS_CTX:
        return

    if ds is None:
        return

    lat = ds.attrs.get("radar_latitude", ds.attrs.get("origin_latitude"))
    lon = ds.attrs.get("radar_longitude", ds.attrs.get("origin_longitude"))

    if lat is None or lon is None:
        radar_id = ds.attrs.get("radar", ds.attrs.get("radar_id", ""))
        logger.debug("No radar location for %s — skipping basemap", radar_id)
        return

    lat, lon = float(lat), float(lon)
    crs_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=km"
    ax.set_xlim(x_km.min(), x_km.max())
    ax.set_ylim(y_km.min(), y_km.max())
    try:
        ctx.add_basemap(
            ax,
            crs=crs_str,
            source=ctx.providers.OpenStreetMap.Mapnik,
            alpha=0.6,
            attribution=False,
            zoom=8,
            zorder=0,
        )
    except Exception as e:
        logger.warning("Basemap unavailable: %s", e)
