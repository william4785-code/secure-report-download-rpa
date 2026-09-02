from __future__ import annotations

import pytest


def test_runtime_context_formats_dates(rpa_module, monkeypatch):
    real_date = rpa_module.date

    class FixedDate:
        @staticmethod
        def today():
            return real_date(2026, 2, 14)

    monkeypatch.setattr(rpa_module, "date", FixedDate)
    context = rpa_module.ReportDownloadPlatform.runtime_context()

    assert context["today"] == "2026-02-14"
    assert context["month_start"] == "2026-02-01"
    assert context["yyyymm"] == "202602"


def test_render_arguments_preserves_non_string_values(platform, monkeypatch):
    monkeypatch.setattr(
        platform,
        "runtime_context",
        lambda: {"today": "2026-02-14", "month_start": "2026-02-01"},
    )
    assert platform.render_arguments(["{month_start}", "to-{today}", 7]) == [
        "2026-02-01",
        "to-2026-02-14",
        7,
    ]


def test_run_aggregates_failed_reports(platform, monkeypatch):
    fake_driver = object()
    monkeypatch.setattr(platform, "create_driver", lambda: fake_driver)
    monkeypatch.setattr(platform, "wait_for_login", lambda _driver: None)
    monkeypatch.setattr(
        platform,
        "run_task",
        lambda _driver, task: task.code != "REPORT_B",
    )

    with pytest.raises(RuntimeError, match="REPORT_B"):
        platform.run(["REPORT_A", "REPORT_B"])
