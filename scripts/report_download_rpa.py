from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from secure_report_download_rpa import (  # noqa: E402,F401
    ARCHIVE_EXTENSIONS,
    EXCEL_EXTENSIONS,
    ReportDownloadPlatform,
    ReportTask,
    get_required_env,
    load_private_config,
    resolve_path,
)
from secure_report_download_rpa.cli import main, parse_args  # noqa: E402,F401


if __name__ == "__main__":
    main()
