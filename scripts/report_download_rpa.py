from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
import argparse
import glob
import json
import os
import shutil
import time

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By


EXCEL_EXTENSIONS = (".xls", ".xlsx")
ARCHIVE_EXTENSIONS = (".zip", ".rar", ".7z")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_private_config() -> dict[str, Any]:
    config_path = Path(os.getenv("RPA_CONFIG_FILE", "config/private_reports.json"))
    if not config_path.exists():
        raise FileNotFoundError(
            f"Private report configuration not found: {config_path}. "
            "Copy config/reports.example.json and keep the real file out of Git."
        )

    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config.get("reports"), list) or not config["reports"]:
        raise ValueError("Configuration must contain a non-empty reports list")

    return config


def resolve_path(value: str, base_dir: Path) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute():
        expanded = base_dir / expanded
    return expanded.resolve()


@dataclass
class ReportTask:
    code: str
    page_hint: str
    ready_condition_js: str
    open_script_js: str
    download_script_js: str
    destination_dir: Path
    output_prefix: str
    expected_prefixes: tuple[str, ...]
    extensions: tuple[str, ...]
    arguments: list[Any]
    enabled: bool = True
    experimental: bool = False
    open_wait_seconds: float = 3.0
    allow_any_excel: bool = False


class ReportDownloadPlatform:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_dir = Path(__file__).resolve().parents[1]
        self.download_dir = resolve_path(
            config.get("download_dir", "downloads"), self.base_dir
        )
        self.edge_profile_dir = resolve_path(
            get_required_env("EDGE_PROFILE_DIR"), self.base_dir
        )
        self.entry_url = get_required_env("PLATFORM_ENTRY_URL")
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tasks = self._build_tasks()

    def _build_tasks(self) -> dict[str, ReportTask]:
        tasks: dict[str, ReportTask] = {}

        for item in self.config["reports"]:
            code = str(item["code"]).upper()
            extension_group = item.get("extension_group", "excel")
            extensions = (
                EXCEL_EXTENSIONS
                if extension_group == "excel"
                else ARCHIVE_EXTENSIONS
            )

            tasks[code] = ReportTask(
                code=code,
                page_hint=str(item["page_hint"]),
                ready_condition_js=str(item["ready_condition_js"]),
                open_script_js=str(item["open_script_js"]),
                download_script_js=str(item["download_script_js"]),
                destination_dir=resolve_path(
                    str(item["destination_dir"]), self.base_dir
                ),
                output_prefix=str(item.get("output_prefix", code)),
                expected_prefixes=tuple(item.get("expected_prefixes", [code])),
                extensions=extensions,
                arguments=list(item.get("arguments", [])),
                enabled=bool(item.get("enabled", True)),
                experimental=bool(item.get("experimental", False)),
                open_wait_seconds=float(item.get("open_wait_seconds", 3)),
                allow_any_excel=bool(item.get("allow_any_excel", False)),
            )

        return tasks

    def create_driver(self):
        options = Options()
        options.add_argument(f"--user-data-dir={self.edge_profile_dir}")
        options.add_argument("--start-maximized")
        options.add_experimental_option("detach", True)
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )

        driver = webdriver.Edge(options=options)
        driver.get(self.entry_url)
        return driver

    @staticmethod
    def switch_to_frame_by_condition(driver, condition_js: str, timeout=40):
        start = time.time()

        def scan(depth=0, max_depth=5):
            try:
                if driver.execute_script(condition_js):
                    return True

                if depth >= max_depth:
                    return False

                frames = driver.find_elements(By.TAG_NAME, "iframe")
                frames += driver.find_elements(By.TAG_NAME, "frame")

                for index in range(len(frames)):
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    frames += driver.find_elements(By.TAG_NAME, "frame")
                    driver.switch_to.frame(frames[index])

                    if scan(depth + 1, max_depth):
                        return True

                    driver.switch_to.parent_frame()
            except Exception:
                try:
                    driver.switch_to.parent_frame()
                except Exception:
                    pass

            return False

        while time.time() - start < timeout:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                driver.switch_to.default_content()
                if scan():
                    return True
            time.sleep(1)

        return False

    def wait_for_login(self, driver):
        condition = str(
            self.config.get(
                "login_ready_condition_js",
                "return document.readyState === 'complete';",
            )
        )
        timeout = int(self.config.get("login_timeout_seconds", 60))

        if not self.switch_to_frame_by_condition(driver, condition, timeout):
            raise RuntimeError("Platform did not reach the configured login-ready state")

        print("Login detected; starting automated report workflow")

    @staticmethod
    def runtime_context() -> dict[str, str]:
        today = date.today()
        return {
            "today": today.strftime("%Y-%m-%d"),
            "month_start": today.replace(day=1).strftime("%Y-%m-%d"),
            "yyyymm": today.strftime("%Y%m"),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }

    def render_arguments(self, arguments: list[Any]) -> list[Any]:
        context = self.runtime_context()
        rendered = []

        for value in arguments:
            if isinstance(value, str):
                rendered.append(value.format(**context))
            else:
                rendered.append(value)

        return rendered

    def get_recent_downloads(self, started_at, prefixes=None, extensions=None):
        files = []

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
        deadline = time.time() + self.download_timeout

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

    def route_download(self, task: ReportTask, started_at: float):
        source = self.wait_for_download(task, started_at)
        task.destination_dir.mkdir(parents=True, exist_ok=True)

        extension = Path(source).suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = task.destination_dir / (
            f"{task.output_prefix}_{timestamp}{extension}"
        )

        shutil.move(source, destination)
        print(f"{task.code} moved to {destination}")

    def run_task(self, driver, task: ReportTask) -> bool:
        label = f"{task.code} (experimental)" if task.experimental else task.code
        print(f"\n======== {label} START ========")

        try:
            if not self.switch_to_frame_by_condition(
                driver,
                str(
                    self.config.get(
                        "menu_ready_condition_js",
                        "return document.readyState === 'complete';",
                    )
                ),
                timeout=60,
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

    def select_tasks(self, requested_codes, include_experimental=False):
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

    def run(self, requested_codes, include_experimental=False):
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Secure configurable browser report download platform"
    )
    parser.add_argument(
        "reports",
        nargs="*",
        help="Report codes to run. Leave empty to run all enabled reports.",
    )
    parser.add_argument(
        "--include-experimental",
        action="store_true",
        help="Include experimental reports when no explicit codes are supplied.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    platform = ReportDownloadPlatform(load_private_config())
    platform.run(args.reports, args.include_experimental)


if __name__ == "__main__":
    main()
