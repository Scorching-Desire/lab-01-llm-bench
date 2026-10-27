"""Перевірка еталонного набору: uv run python scripts/validate_golden.py [--path ...] [--min N] [--tools ...]"""
import argparse
import codecs
import json
import sys
from collections import Counter

FIELDS = ("id", "input", "expected", "split", "tags")


def check_file(path: str, splits: set[str]) -> tuple[list[dict], list[str]]:
    """Формат кожного рядка; повертає (рядки, помилки з номером рядка)."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(codecs.BOM_UTF8):
        return [], [f"{path}: файл має BOM — збережіть як UTF-8 без BOM"]
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as e:
        return [], [f"{path}: не UTF-8 ({e})"]
    rows, errors, seen = [], [], set()
    for n, line in enumerate(lines, start=1):
        err = lambda msg: errors.append(f"{path}:{n}: {msg}")  # noqa: E731
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            err(f"не JSON ({e.msg})")
            continue
        if not isinstance(row, dict) or any(k not in row for k in FIELDS):
            err(f"потрібен JSON-об'єкт з полями {', '.join(FIELDS)}")
            continue
        if not isinstance(row["id"], str) or not row["id"].strip() or row["id"] in seen:
            err(f"id {row['id']!r}: порожній, не рядок або повторюється")
        seen.add(str(row["id"]))
        if not isinstance(row["input"], str) or not row["input"].strip():
            err("input — непорожній рядок")
        exp = row["expected"]
        if not isinstance(exp, (str, dict, list)) or not (exp.strip() if isinstance(exp, str) else exp):
            err("expected — непорожній рядок, об'єкт або список")
        if not isinstance(row["split"], str) or row["split"] not in splits:
            err(f"split має бути одним із {sorted(splits)}")
        if not isinstance(row["tags"], list) or not all(isinstance(t, str) for t in row["tags"]):
            err("tags — список рядків")
            row["tags"] = []
        rows.append(row)
    return rows, errors


def summary(rows: list[dict]) -> str:
    return (f"рядків: {len(rows)} · split: {dict(Counter(str(r['split']) for r in rows))} · "
            f"теги: {dict(Counter(t for r in rows for t in r['tags']))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="data/golden.jsonl")
    ap.add_argument("--min", type=int, help="чернетка: лише формат і щонайменше N рядків")
    ap.add_argument("--tools", help="файл tool-кейсів (split = tool)")
    args = ap.parse_args()
    rows, errors = check_file(args.path, {"dev", "test"})
    print(summary(rows))
    if args.min is not None:
        errors += [f"рядків {len(rows)}, потрібно ≥{args.min}"] if len(rows) < args.min else []
    else:
        dev, test = (sum(r["split"] == s for r in rows) for s in ("dev", "test"))
        tagged = {t: [r for r in rows if t in r["tags"]] for t in ("hard", "injection", "q15")}
        checks = [(len(rows) >= 33, f"рядків {len(rows)}, потрібно ≥33"), (dev == 8, f"dev = {dev}, потрібно рівно 8"),
                  (test >= 25, f"test = {test}, потрібно ≥25"),
                  (len(tagged["hard"]) >= 5, f"hard = {len(tagged['hard'])}, потрібно ≥5"),
                  (len(tagged["injection"]) >= 2, f"injection = {len(tagged['injection'])}, потрібно ≥2"),
                  (len(tagged["q15"]) == 15, f"q15 = {len(tagged['q15'])}, потрібно рівно 15")]
        errors += [msg for ok, msg in checks if not ok]
        errors += [f"{r['id']}: тег {t} дозволений лише в test" for t, rs in tagged.items() for r in rs if r["split"] != "test"]
    if args.tools:
        tool_rows, tool_errors = check_file(args.tools, {"tool"})
        print(summary(tool_rows))
        errors += tool_errors + ([f"{args.tools}: рядків {len(tool_rows)}, потрібно ≥8"] if len(tool_rows) < 8 else [])
        overlap = {str(r["id"]) for r in rows} & {str(r["id"]) for r in tool_rows}
        errors += [f"{args.tools}: id перетинаються з golden: {sorted(overlap)}"] if overlap else []
    for e in errors:
        print("ПОМИЛКА", e)
    print("OK" if not errors else f"помилок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
