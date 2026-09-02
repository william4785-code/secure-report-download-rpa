from __future__ import annotations

import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_EXACT_PATHS = {
    ".env",
    "config/private_reports.json",
}

FORBIDDEN_PARTS = {
    ".venv",
    "downloads",
    "edge-profile",
    "logs",
    "outputs",
    "profiles",
    "session storage",
    "user data",
}

FORBIDDEN_SUFFIXES = {
    ".7z",
    ".csv",
    ".db",
    ".duckdb",
    ".gif",
    ".har",
    ".html",
    ".jpeg",
    ".jpg",
    ".parquet",
    ".pdf",
    ".png",
    ".rar",
    ".rds",
    ".sqlite",
    ".sql",
    ".xls",
    ".xlsx",
    ".zip",
}

ALLOWED_URL_HOSTS = {
    "docs.github.com",
    "example.com",
    "github.com",
    "internal-platform.example.com",
    "pypi.org",
    "python.org",
    "www.python.org",
}


def candidate_files() -> list[Path]:
    command = [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def path_violations(path: Path) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    lowered = relative.lower()
    parts = {part.lower() for part in Path(relative).parts}
    violations: list[str] = []

    if lowered in FORBIDDEN_EXACT_PATHS:
        violations.append("private configuration path")
    if parts & FORBIDDEN_PARTS:
        violations.append("private/runtime directory")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        violations.append(f"forbidden public suffix {path.suffix.lower()}")
    if "private" in path.name.lower() and relative != "SECURITY.md":
        violations.append("private-labelled file")
    if "production" in path.name.lower() or "internal" in path.name.lower():
        violations.append("operational-labelled file")

    return violations


def text_violations(text: str) -> list[str]:
    violations: list[str] = []
    windows_users = r"[a-z]:[\\/]+" + "users" + r"[\\/]+"
    posix_users = "/" + "users" + "/"
    posix_home = "/" + "home" + "/"
    user_path = re.compile(
        rf"(?i)(?:{windows_users}|{posix_users}|{posix_home})[^\s<>'\"]+"
    )
    if user_path.search(text):
        violations.append("personal filesystem path")

    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    if private_key_marker in text:
        violations.append("private key material")

    if re.search(r"(?i)authorization\s*[:=]\s*bearer\s+\S+", text):
        violations.append("authorization bearer value")
    if re.search(r"(?i)cookie\s*[:=]\s*[^\s<>'\"]+", text):
        violations.append("cookie value")
    if re.search(
        r"(?im)^(?:password|passwd|token|secret|api[_-]?key)\s*=\s*\S+",
        text,
    ):
        violations.append("non-empty credential assignment")
    if re.search(r"(?i)(?:jdbc|mysql|mariadb|postgresql|sqlserver)://", text):
        violations.append("database connection string")

    for raw_url in re.findall(r"https?://[^\s<>'\"`)]+", text):
        parsed = urlparse(raw_url.rstrip(".,;"))
        host = (parsed.hostname or "").lower()
        if not host:
            continue
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            violations.append(f"literal IP URL: {host}")
            continue
        if host not in ALLOWED_URL_HOSTS and not host.endswith(".example.com"):
            violations.append(f"non-public URL host: {host}")

    return violations


def validate_example_config() -> list[str]:
    path = ROOT / "config" / "reports.example.json"
    issues: list[str] = []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"config/reports.example.json is invalid: {exc}"]

    reports = config.get("reports")
    if not isinstance(reports, list) or not reports:
        return ["example config must contain at least one synthetic report"]

    for index, report in enumerate(reports):
        code = str(report.get("code", ""))
        page_hint = str(report.get("page_hint", ""))
        scripts = " ".join(
            str(report.get(key, ""))
            for key in ("ready_condition_js", "open_script_js", "download_script_js")
        )
        if not re.fullmatch(r"REPORT_[A-Z]", code):
            issues.append(f"report {index} code is not a synthetic REPORT_X value")
        if not re.fullmatch(r"report-[a-z]", page_hint):
            issues.append(f"report {index} page_hint is not a synthetic placeholder")
        if code not in scripts and "query-form" not in scripts:
            issues.append(f"report {index} scripts lack explicit demo placeholders")

    return issues


def main() -> int:
    findings: list[str] = []

    for path in candidate_files():
        relative = path.relative_to(ROOT).as_posix()
        for violation in path_violations(path):
            findings.append(f"{relative}: {violation}")

        try:
            data = path.read_bytes()
        except OSError as exc:
            findings.append(f"{relative}: cannot read file: {exc}")
            continue
        if b"\x00" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for violation in text_violations(text):
            findings.append(f"{relative}: {violation}")

    findings.extend(validate_example_config())

    if findings:
        print("Public-safety scan failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Public-safety scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
