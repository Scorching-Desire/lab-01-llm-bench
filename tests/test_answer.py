import inspect
import json

from bench import clients
from bench.answer import REFUSAL, answer, assemble_system, correctness


def fake_turn(text):
    return clients.Turn(text, None, None, [], clients.Usage(), "stop", 1, "fake", {})


def test_answer_contract_and_literal_quote(monkeypatch):
    assert "expected" not in inspect.signature(answer).parameters
    pool = [dict(doc_id="d", chunk_id="c", text="Пломбою опікується сектор А10.")]
    seen = []

    def chat(alias, messages, **kwargs):
        seen.append(messages)
        return fake_turn(json.dumps(dict(answer="сектор А10", citations=[
            dict(doc_id="d", chunk_id="c", quote="опікується сектор А10")])))

    monkeypatch.setattr(clients, "chat", chat)
    result = answer("INPUT_CANARY", retriever=lambda q: pool, system="SYSTEM_CORE")
    assert result["status"] == "grounded"
    assert seen[0][0]["content"] == "SYSTEM_CORE"
    assert "TRUTH_CANARY" not in str(seen)
    assert assemble_system("CORE\n", "OVERLAY") == "CORE\n\n\nOVERLAY"


def test_fabricated_citation_does_not_ground(monkeypatch):
    monkeypatch.setattr(clients, "chat", lambda *a, **kw: fake_turn(json.dumps(dict(answer="сектор А10", citations=[
        dict(doc_id="d", chunk_id="c", quote="text absent from returned chunk")]))))
    result = answer("query", retriever=lambda q: [dict(doc_id="d", chunk_id="c", text="original")], system="s")
    assert result["status"] == "unsupported" and result["citations"] == []


def test_absent_refusal_requires_no_citation():
    result = answer("unavailable", retriever=lambda q: [], system="system")
    assert result["status"] == "refused" and result["answer"] == REFUSAL
    assert correctness(dict(tags=["absent"], expected=REFUSAL), result)


def test_batch_never_sends_expected(monkeypatch, tmp_path):
    import sys

    from bench import answer as module

    queries = tmp_path / "queries.jsonl"
    queries.write_text(json.dumps(dict(id="q", input="INPUT_CANARY", expected="TRUTH_CANARY",
                                       split="test", tags=[], gold_spans=[])) + "\n", encoding="utf-8")
    core = tmp_path / "core.md"
    core.write_text("version: fake-core\nCore text", encoding="utf-8")
    overlay = tmp_path / "overlay.md"
    overlay.write_text("Overlay text", encoding="utf-8")
    seen = []

    def chat(alias, messages, **kwargs):
        seen.append(messages)
        return fake_turn(json.dumps(dict(answer=REFUSAL, citations=[])))

    monkeypatch.setattr(module.index, "QUERIES", str(queries))
    monkeypatch.setattr(module.clients, "chat", chat)
    monkeypatch.setattr(sys, "argv", ["answer", "--line", "prompting", "--core", str(core),
                                      "--overlay", str(overlay), "--out", str(tmp_path / "results.jsonl")])
    module.main()
    assert "INPUT_CANARY" in str(seen)
    assert "TRUTH_CANARY" not in str(seen)
