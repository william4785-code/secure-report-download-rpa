from __future__ import annotations

import socket


def test_stable_dns_requires_consecutive_successes():
    from secure_report_download_rpa.connectivity import wait_for_stable_dns

    outcomes = [None, socket.gaierror("temporary"), None, None, None]
    clock = [0.0]

    def resolver(*_args):
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0))]

    def sleep(seconds):
        clock[0] += seconds

    wait_for_stable_dns(
        "portal.example.com",
        consecutive_successes=3,
        timeout=10,
        interval=1,
        resolver=resolver,
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
        "wait_for_stable_dns",
        lambda hostname, **kwargs: events.append(("dns", hostname, kwargs)),
    )
    monkeypatch.setattr(
        platform_module.browser,
        "create_edge_driver",
        lambda *_args, **kwargs: events.append(("edge", kwargs)) or fake_driver,
    )

    assert platform.create_driver() is fake_driver
    assert events[0][0:2] == ("dns", "portal.example.com")
    assert events[1][0] == "edge"
    assert events[1][1]["max_attempts"] == 3


def test_new_window_task_does_not_scan_preexisting_report_handles(
    platform, monkeypatch
):
    from secure_report_download_rpa import platform as platform_module

    class FakeDriver:
        window_handles = ["main", "stale-report"]

        def execute_script(self, script, *_args):
            if "Open REPORT_A" in script:
                self.window_handles = ["main", "stale-report", "fresh-report"]

    driver = FakeDriver()
    platform.main_window_handle = "main"
    scans = []

    def scan(_driver, _condition, timeout=40, *, handles=None):
        scans.append((timeout, handles))
        return True

    monkeypatch.setattr(platform, "switch_to_frame_by_condition", scan)
    monkeypatch.setattr(platform_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(platform, "route_download", lambda *_args: None)

    assert platform.run_task(driver, platform.tasks["REPORT_A"])
    assert scans[0][1] == ["main"]
    assert scans[1][1] == ["fresh-report"]
    assert "stale-report" not in scans[1][1]


def test_new_window_task_fails_closed_when_no_window_opens(platform, monkeypatch):
    from secure_report_download_rpa import platform as platform_module

    class FakeDriver:
        window_handles = ["main", "stale-report"]

        def execute_script(self, _script, *_args):
            return None

    platform.main_window_handle = "main"
    monkeypatch.setattr(
        platform, "switch_to_frame_by_condition", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(platform_module.time, "sleep", lambda _seconds: None)

    assert not platform.run_task(FakeDriver(), platform.tasks["REPORT_A"])
