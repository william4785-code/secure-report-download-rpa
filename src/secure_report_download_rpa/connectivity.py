from __future__ import annotations

import socket
import time
from collections.abc import Callable
from urllib.parse import urlparse


def hostname_from_url(url: str) -> str:
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("Platform URL must include a hostname")
    return hostname


def wait_for_stable_dns(
    hostname: str,
    *,
    consecutive_successes: int = 3,
    timeout: float = 60,
    interval: float = 2,
    resolver: Callable[..., object] = socket.getaddrinfo,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> None:
    if consecutive_successes < 1:
        raise ValueError("consecutive_successes must be at least 1")

    deadline = monotonic() + timeout
    successes = 0
    last_error: OSError | None = None

    while monotonic() <= deadline:
        try:
            resolver(hostname, None)
            successes += 1
            if successes >= consecutive_successes:
                return
        except OSError as exc:
            successes = 0
            last_error = exc

        sleep(interval)

    message = (
        f"DNS for {hostname!r} did not remain stable for "
        f"{consecutive_successes} consecutive checks"
    )
    raise TimeoutError(message) from last_error
