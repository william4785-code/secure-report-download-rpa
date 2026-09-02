from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .config import load_private_config
from .demo import run_demo
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the synthetic demo without a browser or private configuration.",
    )
    parser.add_argument(
        "--demo-output-dir",
        type=Path,
        help="Optional destination root for synthetic demo output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.demo:
        run_demo(args.demo_output_dir, args.reports, args.include_experimental)
        return 0
    if args.demo_output_dir:
        raise ValueError("--demo-output-dir requires --demo")
    platform = ReportDownloadPlatform(load_private_config())
    platform.run(args.reports, args.include_experimental)
    return 0
