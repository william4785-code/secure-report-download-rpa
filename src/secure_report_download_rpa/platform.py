from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from . import browser, connectivity, navigation, runtime_context
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
        self.dns_successes = int(config.get("dns_consecutive_successes", 3))
        self.dns_timeout = float(config.get("dns_timeout_seconds", 60))
        self.dns_interval = float(config.get("dns_check_interval_seconds", 2))
        self.edge_start_attempts = int(config.get("edge_start_attempts", 3))
        self.edge_retry_delay = float(config.get("edge_retry_delay_seconds", 5))
        self.main_window_handle: str | None = None
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tasks = build_tasks(config, self.base_dir)
        self.download_manager = DownloadManager(
            self.download_dir, self.download_timeout
        )

    def create_driver(self):
        hostname = connectivity.hostname_from_url(self.entry_url)
        connectivity.wait_for_stable_dns(
            hostname,
            consecutive_successes=self.dns_successes,
            timeout=self.dns_timeout,
            interval=self.dns_interval,
        )
        return browser.create_edge_driver(
            self.entry_url,
            self.edge_profile_dir,
            self.download_dir,
            max_attempts=self.edge_start_attempts,
            retry_delay_seconds=self.edge_retry_delay,
        )

    @staticmethod
    def switch_to_frame_by_condition(
        driver, condition_js: str, timeout: int = 40, *, handles=None
    ):
        return navigation.switch_to_frame_by_condition(
            driver, condition_js, timeout, handles=handles
        )

    def wait_for_login(self, driver):
        hostname = connectivity.hostname_from_url(self.entry_url)

        def recovery_probe() -> bool:
            try:
                connectivity.wait_for_stable_dns(
                    hostname,
                    consecutive_successes=self.dns_successes,
                    timeout=float(
                        self.config.get("network_recovery_timeout_seconds", 120)
                    ),
                    interval=self.dns_interval,
                )
                return True
            except TimeoutError:
                return False

        return browser.wait_for_login(driver, self.config, recovery_probe)

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
                driver,
                menu_condition,
                timeout=60,
                handles=[self.main_window_handle] if self.main_window_handle else None,
            ):
                raise RuntimeError("Main menu frame was not found")
            handles_before_open = set(driver.window_handles)
            driver.execute_script(task.open_script_js)
            time.sleep(task.open_wait_seconds)
            ready_condition = (
                f"return location.href.includes({json.dumps(task.page_hint)})"
                f" && Boolean(({task.ready_condition_js}));"
            )
            report_handles = None
            if task.scan_new_windows_only:
                report_handles = [
                    handle
                    for handle in driver.window_handles
                    if handle not in handles_before_open
                ]
                if not report_handles:
                    raise RuntimeError(
                        f"{task.code} did not open a new report window"
                    )
            if not self.switch_to_frame_by_condition(
                driver, ready_condition, timeout=60, handles=report_handles
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
        self.main_window_handle = driver.current_window_handle
        results = {task.code: self.run_task(driver, task) for task in selected}
        failed = [code for code, success in results.items() if not success]
        if failed:
            raise RuntimeError(f"Reports failed: {', '.join(failed)}")
        print("All selected reports completed")
