from __future__ import annotations

from pathlib import Path
import time
from collections.abc import Callable
from typing import Any

from selenium import webdriver
from selenium.webdriver.edge.options import Options

from .navigation import switch_to_frame_by_condition


def create_edge_driver(
    entry_url: str,
    edge_profile_dir: Path,
    download_dir: Path,
    *,
    max_attempts: int = 3,
    retry_delay_seconds: float = 5,
    before_retry: Callable[[], None] | None = None,
):
    options = Options()
    options.add_argument(f"--user-data-dir={edge_profile_dir}")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        driver = None
        try:
            driver = webdriver.Edge(options=options)
            driver.get(entry_url)
            return driver
        except Exception as exc:
            last_error = exc
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if attempt < max_attempts:
                if before_retry is not None:
                    before_retry()
                time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Microsoft Edge failed to start after {max_attempts} attempts"
    ) from last_error


def wait_for_login(driver, config: dict[str, Any], recovery_probe=None) -> None:
    condition = str(
        config.get(
            "login_ready_condition_js",
            "return document.readyState === 'complete';",
        )
    )
    timeout = int(config.get("login_timeout_seconds", 180))
    if not switch_to_frame_by_condition(driver, condition, timeout):
        grace = int(config.get("network_recovery_grace_seconds", 30))
        recovered = recovery_probe is not None and recovery_probe()
        if not recovered or not switch_to_frame_by_condition(driver, condition, grace):
            raise RuntimeError("Platform did not reach the configured login-ready state")
    print("Login detected; starting automated report workflow")
