"""Validate source manifests, exact spans, source offsets and attack provenance."""

import argparse
from collections import Counter
from pathlib import Path

from validate_golden import check_file, summary

from bench import data

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "У корпусі немає відповіді."


def validate(root, queries, attacks=None):
    errors = []
    manifests = data.read_rows(root / "data/lab3/manifest.jsonl")
    chunks = data.read_rows(root / "data/lab3/chunks.jsonl")
    documents = {}
    total = 0
    if not 20 <= len(manifests) <= 60:
        errors.append("require 20–60 documents")
    for record in manifests:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to((root / "data/lab3/docs").resolve()):
            errors.append("document path escapes corpus")
            continue
        try:
            documents[record["doc_id"]] = path.read_text(encoding="utf-8")
            total += path.stat().st_size
            if data.sha256_file(path) != record["sha256"] or path.stat().st_size != record["bytes"] or record["bytes"] > 2097152:
                errors.append(f"{path}: incorrect hash or size")
        except OSError as exc:
            errors.append(f"{path}: {exc}")
        if any(not record.get(key) or "ЗАПОВНІТЬ" in record[key] for key in ("source", "license", "date")):
            errors.append(f"{record['doc_id']}: incomplete provenance")
    if len(documents) != len(manifests) or len(set(r["doc_id"] for r in manifests)) != len(manifests):
        errors.append("duplicate or unreadable documents")
    disk = {path.resolve() for path in (root / "data/lab3/docs").rglob("*") if path.is_file() and path.name != ".gitkeep"}
    if disk != {(root / r["path"]).resolve() for r in manifests}:
        errors.append("manifest does not cover corpus directory")
    if total > 41943040:
        errors.append("corpus exceeds 40 MiB")
    attrs = root / ".gitattributes"
    if attrs.exists() and "filter=lfs" in attrs.read_text(encoding="utf-8"):
        errors.append("LFS is forbidden")
    seen = set()
    for chunk in chunks:
        source = documents.get(chunk["doc_id"], "")
        if (chunk["chunk_id"] in seen or not chunk["text"] or not 0 <= chunk["start"] < chunk["end"] <= len(source)
                or source[chunk["start"]:chunk["end"]] != chunk["text"]):
            errors.append(f"{chunk['chunk_id']}: bad offset, duplicate or empty chunk")
        seen.add(chunk["chunk_id"])
    rows, problems = check_file(str(queries), {"dev", "test"})
    errors.extend(problems)
    print(summary(rows))
    splits = Counter(r["split"] for r in rows)
    tags = Counter(t for r in rows for t in r["tags"])
    if splits["dev"] != 8 or splits["test"] < 25:
        errors.append("require dev=8 and test>=25")
    for tag, minimum in {"morph": 5, "multi": 3, "absent": 3, "injection": 2}.items():
        if tags[tag] < minimum:
            errors.append(f"too few {tag}")
    dev = {r["input"] for r in rows if r["split"] == "dev"}
    for row in rows:
        if row["split"] == "test" and row["input"] in dev:
            errors.append(f"{row['id']}: dev/test input collision")
        spans = row.get("gold_spans", [])
        if "absent" in row["tags"]:
            if row["expected"] != REFUSAL or spans:
                errors.append(f"{row['id']}: inconsistent refusal")
        elif not spans:
            errors.append(f"{row['id']}: missing gold span")
        if "multi" in row["tags"] and len({s["doc_id"] for s in spans}) < 2:
            errors.append(f"{row['id']}: multi requires distinct documents")
        for span in spans:
            if not span["text"] or documents.get(span["doc_id"], "").count(span["text"]) != 1:
                errors.append(f"{row['id']}: span not unique in source")
            if not any(c["doc_id"] == span["doc_id"] and span["text"] in c["text"] for c in chunks):
                errors.append(f"{row['id']}: span crosses chunk boundary")
    if attacks:
        pool, problems = check_file(str(attacks), {"attack"})
        errors.extend(problems)
        indirect = [r for r in pool if "indirect" in r["tags"]]
        if len(pool) < 20 or len(indirect) < 5:
            errors.append("require >=20 attacks and >=5 indirect")
        for attack in indirect:
            source = next((c for c in chunks if c["chunk_id"] == attack.get("chunk_id") and
                           c["doc_id"] == attack.get("doc_id")), None)
            if not source or source["text"] not in attack.get("inject", ""):
                errors.append(f"{attack['id']}: injected excerpt has no source")
    print(f"{len(manifests)} documents; {len(chunks)} chunks; {total} bytes")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", "--queries", dest="path", default="data/lab3/queries.jsonl")
    parser.add_argument("--attacks")
    args = parser.parse_args()
    try:
        errors = validate(ROOT, ROOT / args.path, ROOT / args.attacks if args.attacks else None)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print("ПОМИЛКА", error)
    print(f"помилок: {len(errors)}" if errors else "OK")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
