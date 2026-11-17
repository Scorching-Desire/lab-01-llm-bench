"""Recreate Lab 02 tables from append-only JSONL artifacts."""

import statistics
from collections import defaultdict
from pathlib import Path

from bench import data, models, score


def rows(pattern):
    for path in sorted(Path("results/lab2").glob(pattern)):
        latest = {}
        for row in data.read_rows(path):
            if not row["error_type"]:
                latest[row["id"]] = row
        yield path.name, list(latest.values())


def table(headers, entries):
    return "\n".join("| " + " | ".join(map(str, line)) + " |"
                     for line in [headers, ["---"] * len(headers), *entries])


def fraction(k, n):
    a, b = score.wilson_ci(k, n)
    return f"{k}/{n} [{a:.2f}; {b:.2f}]" if n else "0/0 —"


def cost(row, prices):
    spec = models.get(row["alias"])
    input_price, output_price = prices.get(row["alias"], (spec.price_in, spec.price_out))
    if row["input_tokens"] is None or row["output_tokens"] is None:
        return None
    return (row["input_tokens"] * input_price + row["output_tokens"] * output_price) / 1000000


def modality(prices):
    entries = []
    for name, group in rows("02-*.jsonl"):
        if not group:
            continue
        spent = [cost(r, prices) for r in group]
        entries.append([name, len(group), fraction(sum(r["correct"] for r in group), len(group)),
                        statistics.median(r["latency_ms"] for r in group),
                        *[round(statistics.mean(values), 1) if (values := [
                            r[field] for r in group if r[field] is not None]) else "—"
                            for field in ("input_tokens", "output_tokens")],
                        f"${statistics.mean(spent):.6f}" if all(v is not None for v in spent) else "—"])
    return table(["Прогін", "n", "Правильні і 95% ДІ", "Медіана мс", "Сер. in", "Сер. out", "$/документ"], entries)


def compare(groups, base):
    entries = []
    for (model, channel), comparison in sorted(groups.items()):
        if channel == base or (model, base) not in groups:
            continue
        baseline = groups[model, base]
        ids = baseline.keys() & comparison.keys()
        entries.append([model, f"{base} → {channel}", len(ids),
                        sum(not baseline[i] and comparison[i] for i in ids),
                        sum(baseline[i] and not comparison[i] for i in ids)])
    return table(["Модель", "Пара", "Спільні id", "Хибно → правильно", "Правильно → хибно"], entries)


def mod_flips(_):
    groups = defaultdict(dict)
    for _, group in rows("02-*.jsonl"):
        for row in group:
            groups[row["alias"], row["channel"]][row["src_id"]] = row["correct"]
    return compare(groups, "text")


def fields(_):
    entries = []
    for name, group in rows("04-fields-*.jsonl"):
        for key in score.FIELD_RULES:
            codes = [r["fields_correct"][key] for r in group]
            precision = recall = "—"
            if key == "note":
                precision = fraction(codes.count("ok"), sum(c in {"ok", "wrong", "spurious"} for c in codes))
                recall = fraction(codes.count("ok"), sum(c in {"ok", "wrong", "missing"} for c in codes))
            entries.append([name, key, len(codes), fraction(codes.count("ok") + codes.count("empty_ok"), len(codes)),
                            precision, recall])
        for label, k in [("точний збіг документа", sum(r["correct"] for r in group)),
                         ("валідно, але хибно", sum(r["schema_valid"] and not r["correct"] for r in group))]:
            entries.append([name, label, len(group), fraction(k, len(group)), "—", "—"])
    return table(["Прогін", "Поле", "n", "Частка і 95% ДІ", "Precision", "Recall"], entries)


def gen(_):
    groups = defaultdict(dict)
    for _, group in rows("04-gen-*.jsonl"):
        for row in group:
            groups[row["alias"], row["variant"]][row["src_id"]] = row["correct"]
    first = table(["Модель", "Варіант", "n", "Точний збіг і 95% ДІ"],
                  [[m, v, len(g), fraction(sum(g.values()), len(g))] for (m, v), g in sorted(groups.items())])
    return first + "\n\n" + compare(groups, "plain")


def verify(_):
    entries = []
    for name, group in rows("05-*.jsonl"):
        flagged = hit = broken = rescued = invalid = 0
        for row in group:
            verification = row["verify"]
            if verification["status"] == "invalid":
                invalid += 1
                continue
            before = verification["fields_correct_before"]
            incorrect = {key for key, value in before.items() if value in {"missing", "spurious", "wrong"}}
            flags = verification["flags_before"]
            if not flags:
                continue
            flagged += 1
            hit += any(incorrect.intersection(flag["fields"]) for flag in flags)
            rescued += verification["status"] == "verified" and row["correct"]
            broken += not incorrect and not row["correct"]
        entries.append([name, len(group), invalid, fraction(hit, flagged), fraction(rescued, flagged),
                        fraction(broken, flagged), statistics.median(r["latency_ms"] for r in group) if group else "—"])
    return table(["Прогін", "n", "Невалідні", "Справжня помилка / спрацьовування",
                  "Усі поля правильні й verified / спрацьовування",
                  "Зламано ремонтом / спрацьовування", "Медіана мс"], entries)


BLOCKS = {
    "modality": ("docs/lab2/modality.md", modality),
    "mod_flips": ("docs/lab2/modality.md", mod_flips),
    "fields": ("docs/lab2/fields.md", fields),
    "gen": ("docs/lab2/generation.md", gen),
    "verify": ("docs/lab2/verify.md", verify),
}
