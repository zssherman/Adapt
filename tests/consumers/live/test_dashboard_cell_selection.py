# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Unit tests for multi-cell selection pure-logic helpers."""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _next_free_color_slot
# ---------------------------------------------------------------------------


def test_next_free_slot_returns_zero_when_no_cells_selected():
    from adapt.consumers.live._utils import _next_free_color_slot

    assert _next_free_color_slot({}) == 0


def test_next_free_slot_skips_used_slots():
    from adapt.consumers.live._utils import _next_free_color_slot

    used = {"uid_a": 0, "uid_b": 2}
    assert _next_free_color_slot(used) == 1


def test_next_free_slot_returns_none_when_all_seven_taken():
    from adapt.consumers.live._utils import _next_free_color_slot

    used = {f"uid_{i}": i for i in range(7)}
    assert _next_free_color_slot(used) is None


def test_next_free_slot_returns_none_exactly_at_seven_cells():
    from adapt.consumers.live._utils import _next_free_color_slot

    used = {f"uid_{i}": i for i in range(7)}
    assert len(used) == 7
    assert _next_free_color_slot(used) is None


# ---------------------------------------------------------------------------
# _apply_overflow_action
# ---------------------------------------------------------------------------


def test_overflow_ignore_returns_none_without_modifying_selected():
    from adapt.consumers.live._utils import _apply_overflow_action

    selected = {f"uid_{i}": i for i in range(7)}
    original = dict(selected)

    slot = _apply_overflow_action("ignore", selected)

    assert slot is None
    assert selected == original


def test_overflow_replace_oldest_removes_first_added_and_returns_freed_slot():
    from adapt.consumers.live._utils import _apply_overflow_action

    # dict preserves insertion order; uid_0 was inserted first
    selected = {f"uid_{i}": i for i in range(7)}

    slot = _apply_overflow_action("replace_oldest", selected)

    assert slot == 0
    assert "uid_0" not in selected
    assert len(selected) == 6


def test_overflow_wrap_returns_index_modulo_seven():
    from adapt.consumers.live._utils import _apply_overflow_action

    selected = {f"uid_{i}": i for i in range(7)}

    slot = _apply_overflow_action("wrap", selected)

    assert slot == len(selected) % 7


def test_overflow_wrap_does_not_remove_any_cell():
    from adapt.consumers.live._utils import _apply_overflow_action

    selected = {f"uid_{i}": i for i in range(7)}
    original_len = len(selected)

    _apply_overflow_action("wrap", selected)

    assert len(selected) == original_len


# ---------------------------------------------------------------------------
# _visible_uids_in_scan
# ---------------------------------------------------------------------------


def test_visible_uids_in_scan_returns_uids_present_in_cell_label_array():
    import numpy as np

    from adapt.consumers.live._utils import _visible_uids_in_scan

    # uid_map maps integer label → cell_uid string
    uid_map = {1: "abcd1234", 2: "efgh5678"}
    cell_labels = np.array([[0, 1, 1], [0, 2, 0]])

    result = _visible_uids_in_scan(cell_labels, uid_map)

    assert result == {"abcd1234", "efgh5678"}


def test_visible_uids_in_scan_excludes_zero_background():
    import numpy as np

    from adapt.consumers.live._utils import _visible_uids_in_scan

    uid_map = {0: "should_not_appear", 1: "real_cell"}
    cell_labels = np.array([[0, 0, 1]])

    result = _visible_uids_in_scan(cell_labels, uid_map)

    assert "should_not_appear" not in result
    assert "real_cell" in result


def test_visible_uids_in_scan_returns_empty_set_when_no_cells():
    import numpy as np

    from adapt.consumers.live._utils import _visible_uids_in_scan

    uid_map = {}
    cell_labels = np.zeros((5, 5), dtype=int)

    assert _visible_uids_in_scan(cell_labels, uid_map) == set()
