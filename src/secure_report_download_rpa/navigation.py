from __future__ import annotations

import time
from collections.abc import Iterable

from selenium.webdriver.common.by import By


def _scan_current_window(
    driver,
    condition_js: str,
    depth: int = 0,
    max_depth: int = 5,
) -> bool:
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
            if _scan_current_window(
                driver,
                condition_js,
                depth=depth + 1,
                max_depth=max_depth,
            ):
                return True
            driver.switch_to.parent_frame()
    except Exception:
        try:
            driver.switch_to.parent_frame()
        except Exception:
            pass
    return False


def switch_to_frame_by_condition(
    driver,
    condition_js: str,
    timeout: int = 40,
    *,
    handles: Iterable[str] | None = None,
) -> bool:
    start = time.time()

    scoped_handles = list(handles) if handles is not None else None
    while time.time() - start < timeout:
        candidates = scoped_handles if scoped_handles is not None else driver.window_handles
        for handle in candidates:
            driver.switch_to.window(handle)
            driver.switch_to.default_content()
            if _scan_current_window(driver, condition_js):
                return True
        time.sleep(1)
    return False


def switch_to_report_frame_by_condition(
    driver,
    condition_js: str,
    handles_before_open: set[str],
    menu_handle: str | None,
    timeout: int = 60,
) -> bool:
    """Scan dynamic new windows and the known menu, never other old handles."""

    start = time.time()
    while time.time() - start < timeout:
        try:
            handles = list(driver.window_handles)
        except Exception:
            time.sleep(1)
            continue

        candidates = [
            handle for handle in handles if handle not in handles_before_open
        ]
        if menu_handle in handles and menu_handle not in candidates:
            candidates.append(menu_handle)

        for handle in candidates:
            try:
                driver.switch_to.window(handle)
                driver.switch_to.default_content()
                if _scan_current_window(driver, condition_js):
                    return True
            except Exception:
                continue
        time.sleep(1)
    return False
