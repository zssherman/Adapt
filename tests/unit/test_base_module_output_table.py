# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for BaseModule.output_table declaration.

Modules that produce a persisted table declare an OutputTableSpec. Modules that
produce no table (all current core modules) leave it None.
"""

import pytest

pytestmark = pytest.mark.unit

from adapt.modules.base import BaseModule  # noqa: E402


class _NoTableModule(BaseModule):
    name = "no_table"

    def run(self, context: dict) -> dict:
        return {}


class TestBaseModuleOutputTable:
    def test_default_output_table_is_none(self):
        assert _NoTableModule.output_table is None

    def test_core_modules_declare_no_output_table(self):
        from adapt.execution.nodes.detection import DetectModule
        from adapt.execution.nodes.tracking import TrackingModule

        assert DetectModule.output_table is None
        assert TrackingModule.output_table is None
