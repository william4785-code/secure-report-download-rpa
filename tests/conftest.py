from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "report_download_rpa.py"


@pytest.fixture(scope="session")
def rpa_module():
    module_name = "report_download_rpa_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report_config(tmp_path):
    return {
        "download_dir": str(tmp_path / "downloads"),
        "reports": [
            {
                "code": "REPORT_A",
                "page_hint": "report-a",
                "ready_condition_js": "document.querySelector('#query-form') !== null",
                "open_script_js": "console.log('Open REPORT_A demo')",
                "download_script_js": "console.log('Download REPORT_A demo')",
                "arguments": ["{month_start}", "{today}", 7],
                "destination_dir": str(tmp_path / "outputs" / "report_a"),
                "output_prefix": "report_a",
                "expected_prefixes": ["REPORT_A"],
                "extension_group": "excel",
                "enabled": True,
                "experimental": False,
            },
            {
                "code": "REPORT_B",
                "page_hint": "report-b",
                "ready_condition_js": "document.querySelector('#query-form') !== null",
                "open_script_js": "console.log('Open REPORT_B demo')",
                "download_script_js": "console.log('Download REPORT_B demo')",
                "destination_dir": str(tmp_path / "outputs" / "report_b"),
                "output_prefix": "report_b",
                "expected_prefixes": ["REPORT_B"],
                "extension_group": "archive",
                "enabled": True,
                "experimental": True,
            },
        ],
    }


@pytest.fixture
def platform(rpa_module, report_config, tmp_path, monkeypatch):
    monkeypatch.setenv("EDGE_PROFILE_DIR", str(tmp_path / "profile"))
    monkeypatch.setenv("PLATFORM_ENTRY_URL", "https://portal.example.com/")
    return rpa_module.ReportDownloadPlatform(report_config)
