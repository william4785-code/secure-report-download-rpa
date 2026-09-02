from __future__ import annotations

from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.webdriver.edge.options import Options

from .navigation import switch_to_frame_by_condition


def create_edge_driver(entry_url: str, edge_profile_dir: Path, download_dir: Path):
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
    driver = webdriver.Edge(options=options)
    driver.get(entry_url)
    return driver


def wait_for_login(driver, config: dict[str, Any]) -> None:
    condition = str(
        config.get(
            "login_ready_condition_js",
            "return document.readyState === 'complete';",
        )
    )
    timeout = int(config.get("login_timeout_seconds", 60))
    if not switch_to_frame_by_condition(driver, condition, timeout):
        raise RuntimeError("Platform did not reach the configured login-ready state")
    print("Login detected; starting automated report workflow")
