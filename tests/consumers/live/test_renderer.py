# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Unit tests for _renderer module."""

import pytest

pytestmark = pytest.mark.unit

pytest.importorskip("matplotlib", reason="matplotlib not installed")


def test_render_config_fields_accessible():
    """RenderConfig must expose all required fields by name."""
    from adapt.consumers.live._renderer import RenderConfig

    cfg = RenderConfig(
        show_flow=False,
        bg_alpha=0.85,
        max_proj_steps=0,
        cfg={"colors": ["#ff0000"]},
        color_slots=["#ff0000"],
        selected_cells={"abcd1234": 0},
    )
    assert cfg.show_flow is False
    assert cfg.bg_alpha == 0.85
    assert cfg.max_proj_steps == 0
    assert "colors" in cfg.cfg
    assert cfg.color_slots == ["#ff0000"]
    assert "abcd1234" in cfg.selected_cells


def test_add_basemap_is_no_op_when_contextily_unavailable(monkeypatch):
    """add_basemap must not raise and must not call contextily when HAS_CTX is False."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    import adapt.consumers.live._renderer as renderer_mod

    monkeypatch.setattr(renderer_mod, "HAS_CTX", False)

    fig = Figure()
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(1, 1, 1)

    # Should complete without error and without touching contextily.
    # x_km/y_km are irrelevant when HAS_CTX is False (function returns early).
    renderer_mod.add_basemap(ax, ds=None, x_km=None, y_km=None)
