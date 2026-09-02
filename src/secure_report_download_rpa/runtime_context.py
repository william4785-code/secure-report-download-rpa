from __future__ import annotations

from datetime import date, datetime
from typing import Any


def runtime_context() -> dict[str, str]:
    today = date.today()
    return {
        "today": today.strftime("%Y-%m-%d"),
        "month_start": today.replace(day=1).strftime("%Y-%m-%d"),
        "yyyymm": today.strftime("%Y%m"),
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }


def render_arguments(arguments: list[Any]) -> list[Any]:
    context = runtime_context()
    return [
        value.format(**context) if isinstance(value, str) else value
        for value in arguments
    ]
