import json
from pathlib import Path

import pytest

from bench import clients, run

PROMPT = "version: v0\n\n## system\nТестовий промпт.\n\n## user\n<<input>>\n"


def make_files(tmp_path: Path) -> tuple[str, str]:
    """Власні крихітні набір і промпт: тест не залежить від ваших data/ і prompts/."""
    rows = [{"id": f"t{i:02d}", "input": f"вхід {i}", "expected": "ремонт", "split": "test", "tags": []}
            for i in range(1, 5)]
    data_path, prompt_path = tmp_path / "golden.jsonl", tmp_path / "v0.md"
    data_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    prompt_path.write_text(PROMPT, encoding="utf-8")
    return str(data_path), str(prompt_path)


def fake_chat(alias, messages, **params):
    """Відповідь у форматі clients.chat v1, без мережі."""
    return clients.Turn('{"label": "ремонт"}', None, None, [], clients.Usage(100, 5),
                        "stop", 12, "fake-model", {"role": "assistant", "content": '{"label":"ремонт"}'})


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def test_resume_only_appends(tmp_path, monkeypatch):
    data_path, prompt_path = make_files(tmp_path)
    monkeypatch.setattr(clients, "chat", fake_chat)
    out = tmp_path / "03.jsonl"
    args = ["--prompt", prompt_path, "--model", "local", "--data", data_path, "--split", "test", "--out", str(out)]
    run.main(args + ["--limit", "2"])
    before = out.read_bytes()
    run.main(args + ["--limit", "4", "--resume"])
    assert out.read_bytes().startswith(before)  # старі рядки не змінено
    assert [r["id"] for r in rows(out)] == ["t01", "t02", "t03", "t04"]  # t01, t02 не повторено
    row = rows(out)[0]
    assert row["correct"] is True and row["prompt_version"] == "v0" and row["attempt"] == 1


def test_rate_limit_becomes_error_row_then_resume(tmp_path, monkeypatch):
    class RateLimited(Exception):
        status_code = 429

    def failing(alias, messages, **params):
        raise RateLimited("429 Too Many Requests")

    data_path, prompt_path = make_files(tmp_path)
    monkeypatch.setattr(run.time, "sleep", lambda s: None)
    monkeypatch.setattr(clients, "chat", failing)
    out = tmp_path / "03.jsonl"
    args = ["--prompt", prompt_path, "--model", "local", "--data", data_path, "--ids", "t03", "--out", str(out)]
    run.main(args)
    first = rows(out)[0]
    assert first["error_type"] == "rate_limit" and first["correct"] is None
    monkeypatch.setattr(clients, "chat", fake_chat)
    run.main(args + ["--resume"])
    second = rows(out)[1]
    assert second["id"] == "t03" and second["attempt"] == 2 and second["error_type"] is None


def test_dispatcher_records_concurrency_and_prevents_mixing(tmp_path):
    dataset, prompt = make_files(tmp_path)
    out = tmp_path / "parallel.jsonl"
    args = ["--prompt", prompt, "--model", "local", "--data", dataset, "--ids", "t01", "--out", str(out)]
    run.main(args, concurrency=4, retry_attempts=1, chat=fake_chat)
    assert rows(out)[0]["concurrency"] == 4
    with pytest.raises(ValueError, match="concurrency"):
        run.main(args + ["--resume"], concurrency=1, chat=fake_chat)
