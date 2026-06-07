# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""--only / --not are mutually exclusive on run-nexrad."""

from argparse import Namespace

import pytest

from adapt.cli import _run_nexrad


def test_only_and_not_are_mutually_exclusive():
    args = Namespace(only_modules="ingest", exclude_modules="tracking")
    with pytest.raises(SystemExit, match="mutually exclusive"):
        _run_nexrad(args)
