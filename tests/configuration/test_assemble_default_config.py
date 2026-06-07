# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for assemble_default_config — dynamic default config from the registry.

The complete default config is ParamConfig defaults (shared global + core sections)
plus module_params[name] = module.default_params() for every registered extension
module. A new module's owned params appear automatically; no ParamConfig edit.
"""

import pytest

pytestmark = pytest.mark.unit

from pydantic import BaseModel, Field  # noqa: E402

from adapt.configuration.schemas.assemble import assemble_default_config  # noqa: E402
from adapt.execution.module_registry import registry  # noqa: E402
from adapt.modules.base import BaseModule  # noqa: E402


class _FakeCfg(BaseModel):
    gain: float = Field(2.5, description="amplification")
    reflectivity_var: str = "reflectivity"  # injected from global


class _FakeExtension(BaseModule):
    name = "fake_ext"
    pipeline_phase = 3
    config_class = _FakeCfg
    injected_global_fields = frozenset({"reflectivity_var"})

    def run(self, context: dict) -> dict:
        return {}


@pytest.fixture
def registered_fake():
    registry.register(_FakeExtension)
    try:
        yield
    finally:
        registry.unregister("fake_ext")


class TestAssembleDefaultConfig:
    def test_includes_core_paramconfig_sections(self):
        cfg = assemble_default_config()
        for section in ("segmenter", "regridder", "tracker", "global", "projector"):
            assert section in cfg

    def test_extension_owned_params_appear_under_module_params(self, registered_fake):
        cfg = assemble_default_config()
        assert cfg["module_params"]["fake_ext"] == {"gain": 2.5}

    def test_injected_global_fields_excluded(self, registered_fake):
        cfg = assemble_default_config()
        assert "reflectivity_var" not in cfg["module_params"]["fake_ext"]

    def test_core_modules_do_not_emit_module_params(self):
        """Core (phase-0) modules stay as ParamConfig sections, not module_params."""
        cfg = assemble_default_config()
        assert "detection" not in cfg.get("module_params", {})
        assert "ingest" not in cfg.get("module_params", {})
