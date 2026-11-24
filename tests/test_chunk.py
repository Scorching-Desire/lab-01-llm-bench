import pytest

from bench.chunk import split_text


def test_offsets_overlap_and_coverage():
    text = "перший абзац\n\n" + "другий " * 40 + "\n\nхвіст"
    chunks = list(split_text(text, 80, 15))
    assert chunks[0]["start"] == 0 and chunks[-1]["end"] == len(text)
    for chunk in chunks:
        assert chunk["text"] == text[chunk["start"]:chunk["end"]]
        assert len(chunk["text"]) <= 80
    for a, b in zip(chunks, chunks[1:]):
        assert b["start"] == a["end"] - 15


def test_invalid_limits_and_empty_text():
    assert list(split_text("")) == []
    with pytest.raises(ValueError):
        list(split_text("text", 10, 10))
