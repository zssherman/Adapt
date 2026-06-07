# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for RadarProcessor rolling-window executor grouping.

The processor groups modules by required_history (not pipeline_phase).
Modules with required_history=1 run on every scan.
Modules with required_history=2 run once 2 scans have accumulated.
"""

import queue

import pytest

from adapt.runtime.processor import RadarProcessor

pytestmark = [pytest.mark.unit, pytest.mark.pipeline]


def _make_proc(pipeline_config, pipeline_output_dirs, test_repository):
    return RadarProcessor(
        queue.Queue(),
        pipeline_config,
        pipeline_output_dirs,
        repository=test_repository,
    )


class TestProcessorExecutorGrouping:
    def test_processor_groups_executors_by_required_history(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """Processor builds one GraphExecutor per required_history value."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        assert isinstance(proc._executors, dict)
        assert 1 in proc._executors
        assert 2 in proc._executors

    def test_single_scan_executor_contains_ingest_and_detection(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """required_history=1 executor covers ingest and detection."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        names = {n.name for n in proc._executors[1].nodes}
        assert "ingest" in names
        assert "detection" in names

    def test_multi_scan_executor_contains_projection_analysis_tracking(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """required_history=2 executor covers projection, analysis, tracking."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        names = {n.name for n in proc._executors[2].nodes}
        assert "projection" in names
        assert "analysis" in names
        assert "tracking" in names

    def test_processor_has_empty_scan_history_on_init(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """Processor starts with empty scan history."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        assert proc._scan_history == []

    def test_no_phase_based_segmented_history(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """_segmented_history (old phase-based attr) must not exist."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        assert not hasattr(proc, "_segmented_history")

    def test_post_persistence_executor_present_by_default(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """cell_volume_stats is a default phase-3 module → post_executor is built."""
        proc = _make_proc(pipeline_config, pipeline_output_dirs, test_repository)
        assert proc._post_executor is not None
        assert "cell_volume_stats" in [m.name for m in proc._post_modules]

    def test_post_persistence_executor_is_none_without_phase3(
        self, pipeline_config, pipeline_output_dirs, test_repository
    ):
        """Disabling the only phase-3 module (--not) → post_executor is None."""
        cfg = pipeline_config.model_copy(update={"exclude_modules": ["cell_volume_stats"]})
        proc = _make_proc(cfg, pipeline_output_dirs, test_repository)
        assert proc._post_executor is None
        assert proc._post_modules == []
