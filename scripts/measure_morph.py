"""Record the three FTS5 morphology modes from the actual built index."""

import re
from pathlib import Path

from bench import data, index


def main():
    with index.connect(index.DB) as con:
        for mode, query in (("exact", "пломба"), ("prefix", "пломб"), ("trigram", "ломб")):
            rows = index.lexical(con, query, mode, 10000)
            forms = sorted({w for r in rows for w in re.findall(r"\w+", r["text"].casefold()) if "пломб" in w})
            data.append_row("results/lab3/01-morph.jsonl", dict(ts=data.utc_now(), git_sha=data.git_sha(),
                            mode=mode, query=query, count=len(rows), forms=forms,
                            best_score=rows[0]["score"] if rows else None, bytes=Path(index.DB).stat().st_size))
        generic = index.lexical(con, "обладнання", "exact", 10000)
        data.append_row("results/lab3/01-morph.jsonl", dict(ts=data.utc_now(), git_sha=data.git_sha(),
                        mode="common-term", query="обладнання", count=len(generic), forms=[],
                        best_score=generic[0]["score"] if generic else None, bytes=Path(index.DB).stat().st_size))


if __name__ == "__main__":
    main()
