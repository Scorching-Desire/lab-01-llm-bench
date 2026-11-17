import sys
from pathlib import Path

import pytest


def test_missing_manifest_is_reported(monkeypatch, capsys, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import validate_docs

    monkeypatch.setattr(sys, "argv", ["validate_docs.py", "--path", str(tmp_path / "missing.jsonl")])
    try:
        result = validate_docs.main()
    except OSError as error:
        pytest.fail(f"validator did not turn the input error into an actionable message: {error}")
    assert result == 1
    assert "ПОМИЛКА" in capsys.readouterr().out
