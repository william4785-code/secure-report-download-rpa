from __future__ import annotations

import glob
import os
import shutil
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .models import EXCEL_EXTENSIONS, ReportTask


class DownloadManager:
    def __init__(
        self,
        download_dir: Path,
        timeout: int,
        timestamp_factory: Callable[[], str] | None = None,
    ):
        self.download_dir = download_dir
        self.timeout = timeout
        self.timestamp_factory = timestamp_factory

    def get_recent_downloads(
        self,
        started_at: float,
        prefixes: tuple[str, ...] | None = None,
        extensions: tuple[str, ...] | None = None,
    ) -> list[str]:
        files: list[str] = []
        for path in glob.glob(str(self.download_dir / "*")):
            if os.path.isdir(path):
                continue
            name = os.path.basename(path)
            extension = os.path.splitext(name)[1].lower()
            if name.endswith(".crdownload"):
                continue
            if prefixes and not any(name.startswith(prefix) for prefix in prefixes):
                continue
            if extensions and extension not in extensions:
                continue
            if os.path.getmtime(path) >= started_at - 1:
                files.append(path)
        return files

    def wait_for_download(self, task: ReportTask, started_at: float) -> str:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            active = [
                path
                for path in glob.glob(str(self.download_dir / "*.crdownload"))
                if os.path.getmtime(path) >= started_at - 1
            ]
            files = self.get_recent_downloads(
                started_at,
                prefixes=task.expected_prefixes,
                extensions=task.extensions,
            )
            if not files and task.allow_any_excel:
                files = self.get_recent_downloads(
                    started_at, extensions=EXCEL_EXTENSIONS
                )
            if files and not active:
                return max(files, key=os.path.getmtime)
            time.sleep(1)
        raise TimeoutError(f"Timed out waiting for {task.code} download")

    def route_download(self, task: ReportTask, started_at: float) -> Path:
        source = self.wait_for_download(task, started_at)
        return self.route_source(task, source)

    def route_source(self, task: ReportTask, source: str | Path) -> Path:
        task.destination_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(source).suffix
        timestamp = (
            self.timestamp_factory()
            if self.timestamp_factory
            else datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        destination = task.destination_dir / (
            f"{task.output_prefix}_{timestamp}{extension}"
        )
        shutil.move(source, destination)
        print(f"{task.code} moved to {destination}")
        return destination
