import importlib


def test_hit_denominator_excludes_absent(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    report = importlib.import_module("report_lab3")
    positive = dict(id="q", tags=[], hit=True, all_hit=True, recall=1, mrr=1, ndcg=1,
                    latency_ms=10, error_type=None)
    absent = dict(positive, id="a", tags=["absent"], hit=False)
    monkeypatch.setattr(report.data, "read_rows", lambda path: [positive, absent])
    rendered = report.retrieval_table([Path("fake.jsonl")])
    assert "1/1" in rendered and "1/2" not in rendered


def test_answer_denominators_are_separate(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    report = importlib.import_module("report_lab3")
    correct = dict(id="q", tags=[], status="grounded", correct=True, citation_valid=True, error_type=None)
    unsupported = dict(correct, id="q2", status="unsupported", citation_valid=False)
    absent = dict(correct, id="a", tags=["absent"], status="refused", citation_valid=False)
    monkeypatch.setattr(report.data, "read_rows", lambda path: [correct, unsupported, absent])
    rendered = report.answer_metrics({})
    assert "2/2" in rendered
    assert rendered.count("1/1") == 2
