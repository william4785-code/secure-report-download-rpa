from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_required_environment_value_is_returned(rpa_module, monkeypatch):
    monkeypatch.setenv("DEMO_REQUIRED_VALUE", "configured")
    assert rpa_module.get_required_env("DEMO_REQUIRED_VALUE") == "configured"


def test_required_environment_value_rejects_missing(rpa_module, monkeypatch):
    monkeypatch.delenv("DEMO_REQUIRED_VALUE", raising=False)
    with pytest.raises(RuntimeError, match="DEMO_REQUIRED_VALUE"):
        rpa_module.get_required_env("DEMO_REQUIRED_VALUE")


def test_private_config_loads_from_environment(rpa_module, tmp_path, monkeypatch):
    config_path = tmp_path / "demo_config.json"
    config_path.write_text(
        json.dumps({"reports": [{"code": "REPORT_A"}]}), encoding="utf-8"
    )
    monkeypatch.setenv("RPA_CONFIG_FILE", str(config_path))

    assert rpa_module.load_private_config()["reports"][0]["code"] == "REPORT_A"


def test_private_config_rejects_empty_report_list(rpa_module, tmp_path, monkeypatch):
    config_path = tmp_path / "demo_config.json"
    config_path.write_text(json.dumps({"reports": []}), encoding="utf-8")
    monkeypatch.setenv("RPA_CONFIG_FILE", str(config_path))

    with pytest.raises(ValueError, match="non-empty reports list"):
        rpa_module.load_private_config()


def test_resolve_path_anchors_relative_values(rpa_module, tmp_path):
    assert rpa_module.resolve_path("child/report", tmp_path) == (
        tmp_path / "child" / "report"
    ).resolve()


def test_report_tasks_map_extension_groups(platform, rpa_module):
    assert platform.tasks["REPORT_A"].extensions == rpa_module.EXCEL_EXTENSIONS
    assert platform.tasks["REPORT_B"].extensions == rpa_module.ARCHIVE_EXTENSIONS


def test_default_selection_excludes_experimental_tasks(platform):
    assert [task.code for task in platform.select_tasks([])] == ["REPORT_A"]
    assert [
        task.code for task in platform.select_tasks([], include_experimental=True)
    ] == ["REPORT_A", "REPORT_B"]


def test_explicit_selection_rejects_unknown_report(platform):
    with pytest.raises(ValueError, match="Undefined report"):
        platform.select_tasks(["NOT_DEFINED"])
