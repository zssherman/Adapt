# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Smoke test: adapt.consumers.live exports AdaptDashboard and main()."""

import pytest

pytestmark = pytest.mark.unit


def test_adapt_consumers_live_exports_main():
    from adapt.consumers.live import main

    assert callable(main)


def test_adapt_consumers_live_exports_dashboard_class():
    from adapt.consumers.live import AdaptDashboard

    assert AdaptDashboard is not None
