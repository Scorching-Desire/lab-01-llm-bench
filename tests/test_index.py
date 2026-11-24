import pytest

from bench.index import build_index, connect, dense, lexical, metrics


def test_lexical_bm25_is_ascending(tmp_path):
    chunks = [dict(chunk_id="a", doc_id="d", text="пломбою пломбою пломбою"),
              dict(chunk_id="b", doc_id="e", text="пломбою " + "обладнання " * 30)]
    path = tmp_path / "db.sqlite"
    build_index(path, chunks, "lex")
    with connect(path) as con:
        result = lexical(con, "пломбою")
        assert result[0]["chunk_id"] == "a"
        assert result[0]["score"] < result[1]["score"] < 0
        assert lexical(con, "пл", "trigram") == []


def test_dense_dimension_and_model_guard(tmp_path):
    chunks = [dict(chunk_id="a", doc_id="d", text="пломбою")]
    path = tmp_path / "db.sqlite"
    build_index(path, chunks, "dense", "fake", lambda texts, model: [[1.0, 0.0] for t in texts])
    with connect(path) as con:
        assert dense(con, "q", "fake", embedder=lambda texts, model: [[1.0, 0.0]])[0]["chunk_id"] == "a"
        with pytest.raises(ValueError, match="dimension"):
            dense(con, "q", "fake", embedder=lambda texts, model: [[1.0]])
        with pytest.raises(ValueError, match="differs"):
            dense(con, "q", "other")


def test_span_metrics_require_exact_quote_and_document():
    query = dict(gold_spans=[dict(doc_id="d", text="пломбою")])
    assert not metrics(query, [dict(doc_id="other", text="пломбою")])["hit"]
    assert metrics(query, [dict(doc_id="d", text="за пломбою")])["hit"]
    assert metrics(dict(gold_spans=[]), [dict(doc_id="d", text="пломбою")])["recall"] is None
