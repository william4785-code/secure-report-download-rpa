from __future__ import annotations

import os
import time
from pathlib import Path


def touch_with_mtime(path: Path, modified_at: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic demo content", encoding="utf-8")
    os.utime(path, (modified_at, modified_at))
    return path


def test_recent_downloads_filter_prefix_extension_and_partial_files(platform):
    started_at = time.time() - 2
    download_dir = platform.download_dir
    accepted = touch_with_mtime(download_dir / "REPORT_A_result.xlsx", time.time())
    touch_with_mtime(download_dir / "OTHER_result.xlsx", time.time())
    touch_with_mtime(download_dir / "REPORT_A_result.csv", time.time())
    touch_with_mtime(download_dir / "REPORT_A_result.xlsx.crdownload", time.time())
    touch_with_mtime(download_dir / "REPORT_A_old.xlsx", started_at - 20)

    result = platform.get_recent_downloads(
        started_at,
        prefixes=("REPORT_A",),
        extensions=(".xls", ".xlsx"),
    )

    assert result == [str(accepted)]


def test_route_download_moves_and_timestamps_file(
    platform, rpa_module, tmp_path, monkeypatch
):
    from secure_report_download_rpa import downloads

    source = tmp_path / "downloads" / "REPORT_A_result.xlsx"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("synthetic demo content", encoding="utf-8")
    task = platform.tasks["REPORT_A"]
    monkeypatch.setattr(platform, "wait_for_download", lambda *_: str(source))
    real_datetime = downloads.datetime

    class FixedDateTime:
        @staticmethod
        def now():
            return real_datetime(2026, 1, 2, 3, 4, 5)

    monkeypatch.setattr(downloads, "datetime", FixedDateTime)
    platform.route_download(task, started_at=0)

    destination = task.destination_dir / "report_a_20260102_030405.xlsx"
    assert destination.read_text(encoding="utf-8") == "synthetic demo content"
    assert not source.exists()


def test_wait_for_download_times_out_without_files(platform, monkeypatch):
    current = {"value": 0.0}

    def fake_time():
        current["value"] += 1.0
        return current["value"]

    monkeypatch.setattr(platform, "download_timeout", 1)
    monkeypatch.setattr(time, "time", fake_time)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    try:
        platform.wait_for_download(platform.tasks["REPORT_A"], started_at=0)
    except TimeoutError as exc:
        assert "REPORT_A" in str(exc)
    else:
        raise AssertionError("Expected download timeout")
