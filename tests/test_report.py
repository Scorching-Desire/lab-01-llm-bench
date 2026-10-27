import importlib.util
from pathlib import Path

import pytest


def module():
    spec = importlib.util.spec_from_file_location("lab_report", Path(__file__).parents[1] / "scripts/report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_retries_are_not_accuracy_denominator():
    report = module()
    rows = [{"id": "a", "error_type": "rate_limit"}, {"id": "b", "error_type": "server"},
            {"id": "a", "error_type": None, "correct": True}]
    assert list(report.latest_ok(rows)) == ["a"]
    assert report.error_summary(rows) == "server 1"


def test_report_rejects_mixed_hashes():
    report = module()
    rows = [{"_file": "x", "prompt_sha256": "a", "dataset_sha256": "b"},
            {"_file": "x", "prompt_sha256": "c", "dataset_sha256": "b"}]
    with pytest.raises(SystemExit, match="prompt_sha256"):
        report.by_file(rows)


def test_marker_replacement_is_idempotent(tmp_path):
    report = module()
    path = tmp_path / "doc.md"
    path.write_text("Introduction\n<!-- report:begin x -->\nold\n<!-- report:end -->\nAnalysis\n", encoding="utf-8")
    report.write_block(str(path), "x", "table")
    before = path.read_bytes()
    report.write_block(str(path), "x", "table")
    assert path.read_bytes() == before
    assert before.startswith(b"Introduction") and before.endswith(b"Analysis\n")
