from __future__ import annotations

from scripts.check_public_safety import ROOT, path_violations, text_violations


def test_safety_scan_detects_personal_user_path_without_embedding_one():
    value = "C:" + "\\" + "Users" + "\\" + "ExamplePerson" + "\\reports"
    assert "personal filesystem path" in text_violations(value)


def test_safety_scan_rejects_runtime_data_path():
    violations = path_violations(ROOT / "downloads" / "synthetic.xlsx")
    assert "private/runtime directory" in violations
    assert "forbidden public suffix .xlsx" in violations


def test_safety_scan_allows_documented_example_url():
    assert text_violations("https://internal-platform.example.com/") == []
