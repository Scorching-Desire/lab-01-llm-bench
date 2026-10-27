from concurrent.futures import ThreadPoolExecutor

from bench import data


def test_parallel_append_preserves_complete_utf8_rows(tmp_path):
    path = tmp_path / "rows.jsonl"
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: data.append_row(path, {"id": i, "text": "український текст " * 1000}), range(40)))
    rows = data.read_rows(path)
    assert len(rows) == 40 and {r["id"] for r in rows} == set(range(40))
    assert all(r["text"] == "український текст " * 1000 for r in rows)
