import json

import pytest

from bench import clients, data, prompts, service

GOOD = dict(doc_no="MS-1234", total=120, issued_on="2026-10-20", items=["Ролик"], note=None, label="ремонт")


@pytest.mark.parametrize(("first", "second", "status", "count", "error"), [
    (GOOD, None, "verified", 1, None),
    ({**GOOD, "total": -1}, GOOD, "verified", 2, None),
    ({**GOOD, "total": -1}, {**GOOD, "total": -2}, "flagged", 2, None),
    ({**GOOD, "total": -1}, TimeoutError(), "flagged", 2, "timeout"),
    ({"label": "ремонт"}, None, "invalid", 1, None),
])
def test_extract_repair(first, second, status, count, error, tmp_path):
    path = tmp_path / "prompt.md"
    path.write_text("version: lab2-fields-v1\n\n## system\nExtract\n\n## user\n<<input>>\n", encoding="utf-8")
    prompt = prompts.load_prompt(path)
    calls = []

    def fake(model, messages, **kwargs):
        calls.append(messages)
        response = first if len(calls) == 1 else second
        if isinstance(response, Exception):
            raise response
        if len(calls) == 2:
            assert kwargs["timeout"] == 60 and kwargs["max_tokens"] == 512
        return clients.Turn(json.dumps(response), None, None, [], clients.Usage(), "stop", 1, None, {})

    example = data.Example("s", "INPUT_CANARY", {"note": "TRUTH_CANARY"}, "test", [])
    common = dict(alias="fake", mode="A", run_id="case")
    row = service.benchmark_row(example, prompt, common, 1, True, fake, tmp_path / "result.jsonl")
    assert row["verify"]["status"] == status
    assert row["verify"]["repair_error"] == error
    assert len(calls) == count
    assert "TRUTH_CANARY" not in str(calls)
    if count == 2:
        assert "INPUT_CANARY" not in calls[-1][-1]["content"]
        assert "range.total" in calls[-1][-1]["content"]
