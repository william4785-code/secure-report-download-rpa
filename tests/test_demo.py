from __future__ import annotations

import zipfile

import pytest


def test_demo_runs_without_environment_or_browser(tmp_path, monkeypatch):
    from secure_report_download_rpa import browser, cli

    monkeypatch.delenv("EDGE_PROFILE_DIR", raising=False)
    monkeypatch.delenv("PLATFORM_ENTRY_URL", raising=False)
    monkeypatch.delenv("RPA_CONFIG_FILE", raising=False)
    monkeypatch.setattr(
        browser.webdriver,
        "Edge",
        lambda *_args, **_kwargs: pytest.fail("Demo Mode launched Edge"),
    )

    assert cli.main(["--demo", "--demo-output-dir", str(tmp_path)]) == 0

    outputs = list(tmp_path.glob("routed/report_a/report_a_*.xlsx"))
    assert len(outputs) == 1
    assert zipfile.is_zipfile(outputs[0])


def test_demo_includes_experimental_archive_on_request(tmp_path):
    from secure_report_download_rpa.demo import run_demo

    routed = run_demo(tmp_path, include_experimental=True)

    assert {path.suffix for path in routed} == {".xlsx", ".zip"}
    archive = next(path for path in routed if path.suffix == ".zip")
    with zipfile.ZipFile(archive) as package:
        assert set(package.namelist()) == {"manifest.txt", "sample.csv"}


def test_demo_allows_explicit_experimental_report(tmp_path):
    from secure_report_download_rpa.demo import run_demo

    routed = run_demo(tmp_path, requested_codes=["report_b"])

    assert len(routed) == 1
    assert routed[0].name.startswith("report_b_")


def test_demo_rejects_unknown_report(tmp_path):
    from secure_report_download_rpa.demo import run_demo

    with pytest.raises(ValueError, match="Undefined demo report: UNKNOWN"):
        run_demo(tmp_path, requested_codes=["unknown"])


def test_demo_output_option_requires_demo():
    from secure_report_download_rpa import cli

    with pytest.raises(ValueError, match="requires --demo"):
        cli.main(["--demo-output-dir", "unused"])
