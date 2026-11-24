"""Reject test questions/answers and near-duplicate training users.

Normalized word-set Jaccard >= 0.85 is rejected. Punctuation and case are ignored.
Corpus source text is allowed; canonical test answers in assistant outputs are not.
"""

import argparse
import re

from bench import data, score

THRESHOLD = 0.85


def similarity(a, b):
    left, right = (set(re.findall(r"\w+", score.norm(text))) for text in (a, b))
    return len(left & right) / len(left | right) if left or right else 1


def check(train, queries, threshold=THRESHOLD):
    errors = []
    test = [q for q in queries if q["split"] == "test"]
    dev = {q["id"] for q in queries if q["split"] == "dev"}
    for number, row in enumerate(train, 1):
        if row.get("src_split") not in {"dev", "corpus"} or not row.get("src_doc_ids"):
            errors.append(f"train:{number}: missing or invalid provenance")
        if row.get("src_split") == "dev" and row.get("src_query_id") not in dev:
            errors.append(f"train:{number}: unknown dev ID")
        user = "\n".join(m["content"] for m in row["messages"] if m["role"] == "user")
        target = "\n".join(m["content"] for m in row["messages"] if m["role"] == "assistant")
        for query in test:
            if score.norm(query["input"]) in score.norm(user) or similarity(user, query["input"]) >= threshold:
                errors.append(f"train:{number}: test question {query['id']}")
            if score.norm(query["expected"]) in score.norm(target):
                errors.append(f"train:{number}: test answer {query['id']}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default="data/lab3/train.jsonl")
    parser.add_argument("--queries", default="data/lab3/queries.jsonl")
    args = parser.parse_args()
    errors = check(data.read_rows(args.train), data.read_rows(args.queries))
    known = {r["doc_id"] for r in data.read_rows("data/lab3/manifest.jsonl")}
    for number, row in enumerate(data.read_rows(args.train), 1):
        if not set(row.get("src_doc_ids", [])).issubset(known):
            errors.append(f"train:{number}: unknown source document")
    for error in errors:
        print(error)
    print(f"{len(errors)} leaks; Jaccard threshold={THRESHOLD}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
