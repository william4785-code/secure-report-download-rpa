from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXCEL_EXTENSIONS = (".xls", ".xlsx")
ARCHIVE_EXTENSIONS = (".zip", ".rar", ".7z")


@dataclass(frozen=True)
class ReportTask:
    code: str
    page_hint: str
    ready_condition_js: str
    open_script_js: str
    download_script_js: str
    destination_dir: Path
    output_prefix: str
    expected_prefixes: tuple[str, ...]
    extensions: tuple[str, ...]
    arguments: list[Any]
    enabled: bool = True
    experimental: bool = False
    open_wait_seconds: float = 3.0
    allow_any_excel: bool = False
