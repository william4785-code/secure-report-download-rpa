from __future__ import annotations

import socket


def test_stable_endpoint_requires_consecutive_successes():
    from secure_report_download_rpa.connectivity import wait_for_stable_endpoint

    outcomes = [None, socket.gaierror("temporary"), None, None, None]
    clock = [0.0]

    def resolver(*_args):
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0))]

    class FakeConnection:
        def close(self):
            return None

    def sleep(seconds):
        clock[0] += seconds

    wait_for_stable_endpoint(
        "portal.example.com",
        443,
        consecutive_successes=3,
        timeout=10,
        interval=1,
        resolver=resolver,
        connector=lambda *_args, **_kwargs: FakeConnection(),
        sleep=sleep,
        monotonic=lambda: clock[0],
    )

    assert outcomes == []


def test_edge_start_retries_three_times(monkeypatch, tmp_path):
    from secure_report_download_rpa import browser

    attempts = []
    sleeps = []

    class FakeDriver:
        def get(self, url):
            self.url = url

    def edge_factory(**_kwargs):
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise RuntimeError("driver startup failed")
        return FakeDriver()

    monkeypatch.setattr(browser.webdriver, "Edge", edge_factory)
    monkeypatch.setattr(browser.time, "sleep", sleeps.append)

    driver = browser.create_edge_driver(
        "https://portal.example.com/",
        tmp_path / "profile",
        tmp_path / "downloads",
        max_attempts=3,
        retry_delay_seconds=4,
    )

    assert attempts == [1, 2, 3]
    assert sleeps == [4, 4]
    assert driver.url == "https://portal.example.com/"


def test_login_gets_grace_period_after_network_recovery(monkeypatch):
    from secure_report_download_rpa import browser

    calls = []

    def scan(_driver, _condition, timeout):
        calls.append(timeout)
        return len(calls) == 2

    monkeypatch.setattr(browser, "switch_to_frame_by_condition", scan)

    browser.wait_for_login(
        object(),
        {
            "login_timeout_seconds": 180,
            "network_recovery_grace_seconds": 30,
        },
        recovery_probe=lambda: True,
    )

    assert calls == [180, 30]


def test_platform_checks_dns_before_starting_edge(platform, monkeypatch):
    from secure_report_download_rpa import platform as platform_module

    events = []
    fake_driver = object()

    monkeypatch.setattr(
        platform_module.connectivity,
        "wait_for_stable_endpoint",
        lambda hostname, port, **kwargs: events.append(
            ("endpoint", hostname, port, kwargs)
        ),
    )
    monkeypatch.setattr(
        platform_module.browser,
        "create_edge_driver",
        lambda *_args, **kwargs: events.append(("edge", kwargs)) or fake_driver,
    )

    assert platform.create_driver() is fake_driver
    assert events[0][0:3] == ("endpoint", "portal.example.com", 443)
    assert events[1][0] == "edge"
    assert events[1][1]["max_attempts"] == 3


def test_new_window_task_does_not_scan_preexisting_report_handles(
    platform, monkeypatch
):
    from secure_report_download_rpa import platform as platform_module

    class FakeDriver:
        window_handles = ["main", "stale-report"]
        current_window_handle = "main"

        def execute_script(self, script, *_args):
            if "Open REPORT_A" in script:
                self.window_handles = ["main", "stale-report", "fresh-report"]

    driver = FakeDriver()
    platform.main_window_handle = "main"
    menu_scans = []
    report_scans = []

    def scan(_driver, _condition, timeout=40, *, handles=None):
        menu_scans.append((timeout, handles))
        return True

    def report_scan(
        _driver,
        _condition,
        handles_before_open,
        menu_handle,
        timeout=60,
    ):
        report_scans.append((handles_before_open, menu_handle, timeout))
        return True

    monkeypatch.setattr(platform, "switch_to_frame_by_condition", scan)
    monkeypatch.setattr(
        platform,
        "switch_to_report_frame_by_condition",
        report_scan,
    )
    monkeypatch.setattr(platform_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(platform, "route_download", lambda *_args: None)

    assert platform.run_task(driver, platform.tasks["REPORT_A"])
    assert menu_scans == [(60, ["main"])]
    assert report_scans == [({"main", "stale-report"}, "main", 60)]


def test_scoped_task_allows_menu_iframe_fallback(platform, monkeypatch):
    from secure_report_download_rpa import platform as platform_module

    class FakeDriver:
        window_handles = ["main", "stale-report"]
        current_window_handle = "main"

        def execute_script(self, _script, *_args):
            return None

    platform.main_window_handle = "main"
    monkeypatch.setattr(
        platform, "switch_to_frame_by_condition", lambda *_args, **_kwargs: True
    )
    scoped_calls = []
    monkeypatch.setattr(
        platform,
        "switch_to_report_frame_by_condition",
        lambda _driver, _condition, before, menu, timeout=60: (
            scoped_calls.append((before, menu, timeout)) or True
        ),
    )
    monkeypatch.setattr(platform_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(platform, "route_download", lambda *_args: None)

    assert platform.run_task(FakeDriver(), platform.tasks["REPORT_A"])
    assert scoped_calls == [({"main", "stale-report"}, "main", 60)]


def test_scoped_navigation_excludes_old_non_menu_handles():
    from secure_report_download_rpa.navigation import (
        switch_to_report_frame_by_condition,
    )

    class SwitchTo:
        def __init__(self, driver):
            self.driver = driver

        def window(self, handle):
            self.driver.current_handle = handle
            self.driver.visited.append(handle)

        def default_content(self):
            return None

        def frame(self, _frame):
            return None

        def parent_frame(self):
            return None

    class FakeDriver:
        window_handles = ["stale-report", "menu", "new-report"]

        def __init__(self):
            self.current_handle = None
            self.visited = []
            self.switch_to = SwitchTo(self)

        def execute_script(self, _condition):
            return self.current_handle == "menu"

        def find_elements(self, *_args):
            return []

    driver = FakeDriver()
    assert switch_to_report_frame_by_condition(
        driver,
        "return true;",
        {"stale-report", "menu"},
        "menu",
        timeout=1,
    )
    assert driver.visited == ["new-report", "menu"]
    assert "stale-report" not in driver.visited
