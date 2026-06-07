# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for BaseModule class-level declarations.

required_history declares how many scans of history a module needs.
pipeline_phase = 3 marks post-persistence extension modules.
"""

import pytest

pytestmark = pytest.mark.unit

from adapt.modules.base import BaseModule  # noqa: E402


class _MinimalModule(BaseModule):
    """Concrete subclass for testing BaseModule defaults."""

    name = "test_minimal"

    def run(self, context: dict) -> dict:
        return {}


class _MultiScanModule(BaseModule):
    """Module that declares it needs 2 historical scans."""

    name = "test_multi_scan"
    required_history = 2

    def run(self, context: dict) -> dict:
        return {}


class _PostPersistenceModule(BaseModule):
    """Post-persistence extension module."""

    name = "test_post_persist"
    pipeline_phase = 3

    def run(self, context: dict) -> dict:
        return {}


class TestBaseModuleDefaults:
    def test_default_required_history_is_one(self):
        """Modules that need only the current scan default to required_history=1."""
        assert _MinimalModule.required_history == 1

    def test_default_pipeline_phase_is_zero(self):
        """In-pipeline modules default to pipeline_phase=0 (not post-persistence)."""
        assert _MinimalModule.pipeline_phase == 0

    def test_multi_scan_module_declares_required_history(self):
        """A module needing N scans declares required_history=N."""
        assert _MultiScanModule.required_history == 2

    def test_post_persistence_module_declares_pipeline_phase_3(self):
        """Post-persistence extension modules declare pipeline_phase=3."""
        assert _PostPersistenceModule.pipeline_phase == 3

    def test_required_history_is_class_variable_not_instance_state(self):
        """required_history is a ClassVar — same value on all instances."""
        m1 = _MultiScanModule()
        m2 = _MultiScanModule()
        assert m1.required_history == m2.required_history == 2
