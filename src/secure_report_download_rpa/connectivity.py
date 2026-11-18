from __future__ import annotations

import socket
import time
from collections.abc import Callable
from urllib.parse import urlparse


def endpoint_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Platform URL must include a hostname")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return hostname, port


def hostname_from_url(url: str) -> str:
    return endpoint_from_url(url)[0]


def wait_for_stable_endpoint(
    hostname: str,
    port: int,
    *,
    consecutive_successes: int = 3,
    timeout: float = 60,
    interval: float = 2,
    connect_timeout: float = 5,
    resolver: Callable[..., object] = socket.getaddrinfo,
    connector: Callable[..., object] = socket.create_connection,
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
            resolver(hostname, port)
            connection = connector((hostname, port), timeout=connect_timeout)
            close = getattr(connection, "close", None)
            if close is not None:
                close()
            successes += 1
            if successes >= consecutive_successes:
                return
        except OSError as exc:
            successes = 0
            last_error = exc

        sleep(interval)

    message = (
        f"Endpoint {hostname!r}:{port} did not remain reachable for "
        f"{consecutive_successes} consecutive checks"
    )
    raise TimeoutError(message) from last_error
