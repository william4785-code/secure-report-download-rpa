from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import ARCHIVE_EXTENSIONS, EXCEL_EXTENSIONS, ReportTask


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


def build_tasks(config: dict[str, Any], base_dir: Path) -> dict[str, ReportTask]:
    tasks: dict[str, ReportTask] = {}
    for item in config["reports"]:
        code = str(item["code"]).upper()
        extension_group = item.get("extension_group", "excel")
        extensions = (
            EXCEL_EXTENSIONS if extension_group == "excel" else ARCHIVE_EXTENSIONS
        )
        tasks[code] = ReportTask(
            code=code,
            page_hint=str(item["page_hint"]),
            ready_condition_js=str(item["ready_condition_js"]),
            open_script_js=str(item["open_script_js"]),
            download_script_js=str(item["download_script_js"]),
            destination_dir=resolve_path(str(item["destination_dir"]), base_dir),
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
