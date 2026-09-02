from __future__ import annotations

import time

from selenium.webdriver.common.by import By


def switch_to_frame_by_condition(driver, condition_js: str, timeout: int = 40) -> bool:
    start = time.time()

    def scan(depth: int = 0, max_depth: int = 5) -> bool:
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
