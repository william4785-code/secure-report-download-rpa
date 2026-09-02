from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from . import browser, navigation, runtime_context
from .config import build_tasks, get_required_env, resolve_path
from .downloads import DownloadManager
from .models import ReportTask


class ReportDownloadPlatform:
    def __init__(self, config: dict[str, Any], base_dir: Path | None = None):
        self.config = config
        self.base_dir = base_dir or Path(__file__).resolve().parents[2]
        self.download_dir = resolve_path(
            config.get("download_dir", "downloads"), self.base_dir
        )
        self.edge_profile_dir = resolve_path(
            get_required_env("EDGE_PROFILE_DIR"), self.base_dir
        )
        self.entry_url = get_required_env("PLATFORM_ENTRY_URL")
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tasks = build_tasks(config, self.base_dir)
        self.download_manager = DownloadManager(
            self.download_dir, self.download_timeout
        )

    def create_driver(self):
        return browser.create_edge_driver(
            self.entry_url, self.edge_profile_dir, self.download_dir
        )

    @staticmethod
    def switch_to_frame_by_condition(driver, condition_js: str, timeout: int = 40):
        return navigation.switch_to_frame_by_condition(driver, condition_js, timeout)

    def wait_for_login(self, driver):
        return browser.wait_for_login(driver, self.config)

    @staticmethod
    def runtime_context() -> dict[str, str]:
        return runtime_context.runtime_context()

    def render_arguments(self, arguments: list[Any]) -> list[Any]:
        context = self.runtime_context()
        return [
            value.format(**context) if isinstance(value, str) else value
            for value in arguments
        ]

    def get_recent_downloads(self, started_at, prefixes=None, extensions=None):
        return self.download_manager.get_recent_downloads(
            started_at, prefixes=prefixes, extensions=extensions
        )

    def wait_for_download(self, task: ReportTask, started_at: float) -> str:
        self.download_manager.timeout = self.download_timeout
        return self.download_manager.wait_for_download(task, started_at)

    def route_download(self, task: ReportTask, started_at: float):
        source = self.wait_for_download(task, started_at)
        return self.download_manager.route_source(task, source)

    def run_task(self, driver, task: ReportTask) -> bool:
        label = f"{task.code} (experimental)" if task.experimental else task.code
        print(f"\n======== {label} START ========")
        try:
            menu_condition = str(
                self.config.get(
                    "menu_ready_condition_js",
                    "return document.readyState === 'complete';",
                )
            )
            if not self.switch_to_frame_by_condition(
                driver, menu_condition, timeout=60
            ):
                raise RuntimeError("Main menu frame was not found")
            driver.execute_script(task.open_script_js)
            time.sleep(task.open_wait_seconds)
            ready_condition = (
                f"return location.href.includes({json.dumps(task.page_hint)})"
                f" && Boolean(({task.ready_condition_js}));"
            )
            if not self.switch_to_frame_by_condition(
                driver, ready_condition, timeout=60
            ):
                raise RuntimeError(f"{task.code} report frame was not found")
            started_at = time.time()
            driver.execute_script(
                task.download_script_js, *self.render_arguments(task.arguments)
            )
            self.route_download(task, started_at)
            print(f"{task.code} completed")
            return True
        except Exception as exc:
            print(f"{task.code} failed: {exc}")
            return False

    def select_tasks(self, requested_codes, include_experimental: bool = False):
        if requested_codes:
            selected = []
            for code in requested_codes:
                report_code = code.upper()
                if report_code not in self.tasks:
                    raise ValueError(f"Undefined report: {report_code}")
                selected.append(self.tasks[report_code])
            return selected
        return [
            task
            for task in self.tasks.values()
            if task.enabled and (include_experimental or not task.experimental)
        ]

    def run(self, requested_codes, include_experimental: bool = False):
        selected = self.select_tasks(requested_codes, include_experimental)
        if not selected:
            raise RuntimeError("No reports selected")
        print("Selected reports:", ", ".join(task.code for task in selected))
        driver = self.create_driver()
        self.wait_for_login(driver)
        results = {task.code: self.run_task(driver, task) for task in selected}
        failed = [code for code, success in results.items() if not success]
        if failed:
            raise RuntimeError(f"Reports failed: {', '.join(failed)}")
        print("All selected reports completed")
