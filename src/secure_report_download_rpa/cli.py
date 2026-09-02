from __future__ import annotations

import argparse
from collections.abc import Sequence

from .config import load_private_config
from .platform import ReportDownloadPlatform


def parse_args(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Secure configurable browser report download platform"
    )
    parser.add_argument(
        "reports",
        nargs="*",
        help="Report codes to run. Leave empty to run all enabled reports.",
    )
    parser.add_argument(
        "--include-experimental",
        action="store_true",
        help="Include experimental reports when no explicit codes are supplied.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    platform = ReportDownloadPlatform(load_private_config())
    platform.run(args.reports, args.include_experimental)
    return 0
