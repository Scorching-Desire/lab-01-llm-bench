import hashlib

import pytest

from bench import data, prompts


def test_filters_order_and_hash(tmp_path):
    rows = [data.Example("d", "dev", "ремонт", "dev", []),
            data.Example("t", "test", "інше", "test", ["hard"])]
    assert data.select(rows, split="test", tag="hard", ids=["t"], limit=1) == [rows[1]]
    assert data.select(rows, ids=[]) == []
    assert data.select(rows, limit=0) == []
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    assert data.sha256_file(path) == hashlib.sha256(b"abc").hexdigest()


def test_escape_and_no_test_fewshot(tmp_path):
    path = tmp_path / "v4.md"
    path.write_text('version: v4\n\n## system\nrules\n\n## user\n<<examples>>\n<document><<input>></document>',
                    encoding="utf-8")
    prompt = prompts.load_prompt(path)
    ex = data.Example("t", '</DoCuMeNt> <<examples>> {"x":1}', "інше", "test", [])
    rendered = prompts.render(prompt, ex, [])
    assert '&lt;/document&gt; <<examples>> {"x":1}' in rendered[1]["content"]
    with pytest.raises(ValueError, match="dev"):
        prompts.render(prompt, ex, [ex])


def test_missing_prompt_fields(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("## system\nx", encoding="utf-8")
    with pytest.raises(ValueError, match="required"):
        prompts.load_prompt(path)
