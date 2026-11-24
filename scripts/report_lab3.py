"""Deterministic Lab 03 tables using shared Wilson intervals and marker writer."""

import statistics
from collections import Counter
from pathlib import Path

from report_lab2 import fraction, table

from bench import data


def latest(path):
    rows = {}
    for row in data.read_rows(path):
        if not row.get("error_type"):
            rows[row["id"]] = row
    return rows


def retrieval_table(paths):
    entries = []
    for path in paths:
        main = [r for r in latest(path).values() if "absent" not in r["tags"]]
        subsets = [(path.name, main)]
        morph_rows = [r for r in main if "morph" in r["tags"]]
        if morph_rows:
            subsets.append((path.name + " · morph", morph_rows))
        for label, rows in subsets:
            if not rows:
                continue
            multi = [r for r in rows if "multi" in r["tags"]]
            entries.append([label, len(rows), fraction(sum(r["hit"] for r in rows), len(rows)),
                        fraction(sum(r["all_hit"] for r in multi), len(multi)),
                        f"{statistics.mean(r['recall'] for r in rows):.3f}",
                        f"{statistics.mean(r['mrr'] for r in rows):.3f}",
                        f"{statistics.mean(r['ndcg'] for r in rows):.3f}",
                        statistics.median(r["latency_ms"] for r in rows)])
    return table(["Прогін", "n без absent", "hit@5 і 95% ДІ", "multi, усі уривки", "Recall@5", "MRR", "nDCG@10", "Медіана мс"], entries)


def retrieval(_):
    return retrieval_table(
        [Path("results/lab3/01-lex.jsonl"), Path("results/lab3/01-dense.jsonl")])


def morph(_):
    rows = data.read_rows("results/lab3/01-morph.jsonl")
    return table(["Режим", "Запит", "Знайдено", "Форми", "bm25 першого", "Байтів індексу"],
                 [[r["mode"], r["query"], r["count"], ", ".join(r["forms"]), r["best_score"], r["bytes"]]
                  for r in rows])


def rrf_table(_):
    return retrieval_table([Path("results/lab3/02-single-best.jsonl"), Path("results/lab3/02-rrf.jsonl")])


def paired(a, b, key):
    ids = sorted(a.keys() & b.keys())
    return len(ids), sum(not a[i][key] and b[i][key] for i in ids), sum(a[i][key] and not b[i][key] for i in ids)


def flips_ret(_):
    base = {k: v for k, v in latest("results/lab3/02-single-best.jsonl").items() if "absent" not in v["tags"]}
    other = {k: v for k, v in latest("results/lab3/02-rrf.jsonl").items() if "absent" not in v["tags"]}
    n, improved, lost = paired(base, other, "hit")
    return table(["Пара", "Спільні id", "Гібрид hit@5 і 95% ДІ", "Знайдено замість промаху", "Втрачено"],
                 [["single-best → RRF", n, fraction(sum(other[i]["hit"] for i in base.keys() & other.keys()), n), improved, lost]])


def answer_metrics(_):
    rows = list(latest("results/lab3/03-rag-q8.jsonl").values())
    non_absent = [r for r in rows if "absent" not in r["tags"]]
    grounded = [r for r in non_absent if r["status"] == "grounded"]
    absent = [r for r in rows if "absent" in r["tags"]]
    return table(["Метрика", "Знаменник", "k/n і 95% ДІ"], [
        ["Правильність", "test без absent", fraction(sum(r["correct"] for r in non_absent), len(non_absent))],
        ["Чинна цитата", "test без absent зі статусом grounded", fraction(sum(r["citation_valid"] for r in grounded), len(grounded))],
        ["Правильна відмова", "test з absent", fraction(sum(r["status"] == "refused" for r in absent), len(absent))]])


def attacks(_):
    raw = data.read_rows("results/lab3/03-attacks-q8.jsonl")
    rows = {r["id"]: r for r in raw}
    entries = []
    for tag in ("direct", "indirect"):
        group = [r for r in rows.values() if tag in r["tags"]]
        count = Counter(r["outcome"] for r in group)
        entries.append([tag, len(group), fraction(count["held"], len(group)),
                        *[count[name] for name in ("held", "followed", "leaked", "fabricated", "crashed")]])
    return table(["Тип", "n", "Held і 95% ДІ", "held", "followed", "leaked", "fabricated", "crashed"], entries)


def line_rows():
    return {line: latest(f"results/lab3/04-q8-{line}.jsonl") for line in ("prompting", "rag", "lora")}


def lines(_):
    entries = []
    for line, lookup in line_rows().items():
        rows = list(lookup.values())
        if not rows:
            entries.append([line, 0, "стан у adapt.md", "—", "—", "—", "—"])
            continue
        absent = [r for r in rows if "absent" in r["tags"]]
        cited = [r for r in rows if "absent" not in r["tags"] and r["status"] == "grounded"]
        errors = sum(bool(r.get("error_type")) for r in data.read_rows(f"results/lab3/04-q8-{line}.jsonl"))
        entries.append([line, len(rows), fraction(sum(r["correct"] for r in rows), len(rows)),
                        fraction(sum(r["status"] == "refused" for r in absent), len(absent)),
                        fraction(sum(r["citation_valid"] for r in cited), len(cited)) if line == "rag" else "—",
                        statistics.median(r["latency_ms"] for r in rows), errors])
    return table(["Лінія", "n усі test", "Правильні і 95% ДІ", "Відмова на absent", "Цитати", "Медіана мс", "Помилки"], entries)


def lines_flips(_):
    groups = line_rows()
    entries = []
    for line in ("rag", "lora"):
        if groups[line]:
            entries.append([f"prompting → {line}", *paired(groups["prompting"], groups[line], "correct")])
    return table(["Пара", "Спільні id", "Хибно → правильно", "Правильно → хибно"], entries)


BLOCKS = {
    "morph": ("docs/lab3/retrieval.md", morph),
    "retrieval": ("docs/lab3/retrieval.md", retrieval),
    "rrf": ("docs/lab3/retrieval.md", rrf_table),
    "flips_ret": ("docs/lab3/retrieval.md", flips_ret),
    "answer": ("docs/lab3/answer.md", answer_metrics),
    "attacks": ("docs/lab3/answer.md", attacks),
    "lines": ("docs/lab3/lines.md", lines),
    "lines_flips": ("docs/lab3/lines.md", lines_flips),
}
