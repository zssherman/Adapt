# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Tests for the ingress source plugin system.

Sources are registered, swappable-by-name plugins that push file paths into the
processor queue. AwsNexradDownloader (download) and LocalDirectorySource
(already-present files) both satisfy the ScanSource interface.
"""

import queue

import pytest

from adapt.configuration.schemas.param import ParamConfig
from adapt.configuration.schemas.resolve import resolve_config
from adapt.configuration.schemas.user import UserConfig

pytestmark = pytest.mark.unit


def _config(tmp_path, **user_kw):
    user = UserConfig(base_dir=str(tmp_path), radar="KLOT", **user_kw)
    return resolve_config(ParamConfig(), user, None)


class TestSourceRegistry:
    def test_registry_resolves_builtin_sources(self):
        from adapt.modules.acquisition.module import AwsNexradDownloader
        from adapt.runtime.sources import LocalDirectorySource, source_registry

        assert source_registry.get("aws_nexrad") is AwsNexradDownloader
        assert source_registry.get("local_directory") is LocalDirectorySource

    def test_unknown_source_raises(self):
        from adapt.runtime.sources import source_registry

        with pytest.raises(KeyError, match="unknown_source"):
            source_registry.get("unknown_source")


class TestLocalDirectorySource:
    def test_queues_files_in_chronological_order(self, tmp_path):
        from adapt.runtime.sources import LocalDirectorySource

        src_dir = tmp_path / "incoming"
        src_dir.mkdir()
        # NEXRAD-style names embed the timestamp; lexical sort == chronological
        for name in ["KLOT20240101_120500_V06", "KLOT20240101_120000_V06"]:
            (src_dir / name).write_bytes(b"x" * 6000)

        cfg = _config(tmp_path, source="local_directory", source_dir=str(src_dir))
        q: queue.Queue = queue.Queue()
        src = LocalDirectorySource(
            config=cfg, output_dirs={"base": str(tmp_path)}, result_queue=q, file_tracker=None
        )
        src.run()

        queued = []
        while not q.empty():
            item = q.get()
            queued.append(item["path"] if isinstance(item, dict) else item)

        assert [p.split("/")[-1] for p in queued] == [
            "KLOT20240101_120000_V06",
            "KLOT20240101_120500_V06",
        ]
        assert src.is_historical_complete() is True
        assert src.get_historical_progress() == (2, 2)

    def test_missing_source_dir_raises(self, tmp_path):
        from adapt.runtime.sources import LocalDirectorySource

        cfg = _config(tmp_path, source="local_directory")  # source_dir is None
        with pytest.raises(ValueError, match="source_dir"):
            LocalDirectorySource(
                config=cfg, output_dirs={"base": str(tmp_path)}, result_queue=queue.Queue()
            )
