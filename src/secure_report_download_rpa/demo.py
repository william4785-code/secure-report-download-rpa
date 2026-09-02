from __future__ import annotations

import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

from .config import build_tasks
from .downloads import DownloadManager
from .models import ReportTask


DEMO_CONFIG = {
    "reports": [
        {
            "code": "REPORT_A",
            "page_hint": "synthetic-report-a",
            "ready_condition_js": "true",
            "open_script_js": "return true;",
            "download_script_js": "return true;",
            "destination_dir": "routed/report_a",
            "output_prefix": "report_a",
            "expected_prefixes": ["REPORT_A"],
            "extension_group": "excel",
            "enabled": True,
            "experimental": False,
        },
        {
            "code": "REPORT_B",
            "page_hint": "synthetic-report-b",
            "ready_condition_js": "true",
            "open_script_js": "return true;",
            "download_script_js": "return true;",
            "destination_dir": "routed/report_b",
            "output_prefix": "report_b",
            "expected_prefixes": ["REPORT_B"],
            "extension_group": "archive",
            "enabled": True,
            "experimental": True,
        },
    ]
}


def _select_tasks(
    tasks: dict[str, ReportTask],
    requested_codes: tuple[str, ...] | list[str],
    include_experimental: bool,
) -> list[ReportTask]:
    if requested_codes:
        selected: list[ReportTask] = []
        for code in requested_codes:
            report_code = code.upper()
            if report_code not in tasks:
                raise ValueError(f"Undefined demo report: {report_code}")
            selected.append(tasks[report_code])
        return selected
    return [
        task
        for task in tasks.values()
        if task.enabled and (include_experimental or not task.experimental)
    ]


def _write_synthetic_xlsx(path: Path) -> None:
    rows = (
        '<row r="1"><c r="A1" t="inlineStr"><is><t>report_code</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>status</t></is></c></row>'
        '<row r="2"><c r="A2" t="inlineStr"><is><t>REPORT_A</t></is></c>'
        '<c r="B2" t="inlineStr"><is><t>synthetic</t></is></c></row>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        workbook.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        workbook.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Demo" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{rows}</sheetData></worksheet>",
        )


def _write_synthetic_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.txt",
            "Synthetic demo archive\nNo operational data is included.\n",
        )
        archive.writestr("sample.csv", "report_code,status\nREPORT_B,synthetic\n")


def _create_synthetic_download(task: ReportTask, download_dir: Path) -> Path:
    extension = ".xlsx" if ".xlsx" in task.extensions else ".zip"
    path = download_dir / f"{task.code}_synthetic{extension}"
    if extension == ".xlsx":
        _write_synthetic_xlsx(path)
    else:
        _write_synthetic_archive(path)
    return path


def run_demo(
    output_root: Path | None = None,
    requested_codes: tuple[str, ...] | list[str] = (),
    include_experimental: bool = False,
) -> list[Path]:
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_root is None:
        repository_root = Path(__file__).resolve().parents[2]
        output_root = repository_root / "demo_output" / f"run_{run_timestamp}"
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    tasks = build_tasks(DEMO_CONFIG, output_root)
    selected = _select_tasks(tasks, requested_codes, include_experimental)
    if not selected:
        raise RuntimeError("No demo reports selected")

    print("Demo Mode: synthetic files only; browser and private configuration disabled")
    print("Selected demo reports:", ", ".join(task.code for task in selected))

    routed: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="secure_rpa_demo_") as staging:
        download_dir = Path(staging)
        manager = DownloadManager(
            download_dir,
            timeout=2,
            timestamp_factory=lambda: run_timestamp,
        )
        for task in selected:
            started_at = time.time()
            _create_synthetic_download(task, download_dir)
            routed.append(manager.route_download(task, started_at))

    print(f"Demo completed: {len(routed)} file(s) routed under {output_root}")
    return routed
