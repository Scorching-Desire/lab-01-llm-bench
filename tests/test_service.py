import json

from bench import clients, data, prompts, service


def test_service_rows_and_runner_rows_share_columns(tmp_path):
    path = tmp_path / "prompt.md"
    path.write_text("version: lab2-fields-v1\n\n## system\nExtract\n\n## user\n<<input>>\n", encoding="utf-8")
    prompt = prompts.load_prompt(path)
    fields = dict(doc_no="MS-1234", total=10, issued_on="2026-10-20", items=["item"], note=None, label="ремонт")
    for_service = data.Example("cli", "document", None, "service", [])
    for_benchmark = data.Example("batch", "document", fields, "test", [])
    common = dict(alias="fake", mode="B", run_id="test")

    def chat(*args, **kwargs):
        return clients.Turn(json.dumps(fields), None, True, [], clients.Usage(), "stop", 1, "mock", {})

    standalone = service.benchmark_row(for_service, prompt, common, 1, True, chat, tmp_path / "service.jsonl")
    measured = service.benchmark_row(for_benchmark, prompt, common, 1, True, chat, tmp_path / "bench.jsonl")
    assert standalone.keys() == measured.keys()
    assert standalone["correct"] is None and measured["correct"] is True
    assert standalone["parsed"] == measured["parsed"]


def test_corrupt_media_produces_media_error_without_call(tmp_path):
    bad = tmp_path / "invalid.png"
    bad.write_bytes(b"broken")
    path = tmp_path / "prompt.md"
    path.write_text("version: lab2-fields-v1\n\n## system\nExtract\n\n## user\n<<input>>\n", encoding="utf-8")
    example = data.Example("bad", "", None, "service", [], channel="clean",
                           input_file=str(bad), input_sha256="wrong digest")
    common = dict(alias="fake", mode="A")

    def unexpected(*args, **kwargs):
        raise AssertionError("invalid media reached the API")

    row = service.benchmark_row(example, prompts.load_prompt(path), common, 1, True, unexpected, tmp_path / "out.jsonl")
    assert row["error_type"] == "media"
