"""Таблиці звіту: results/*.jsonl → блоки між маркерами в docs/lab1/*.md.

uv run python scripts/report.py [блок ...] [--price alias=IN/OUT]
Без аргументів регенерує всі блоки; повторний запуск на тих самих results нічого не змінює.
"""
import argparse
import glob
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from bench import models
from bench.score import norm, wilson_ci
from bench.tools import TOOLS

NO_DATA = "_Немає результатів — запустіть прогін._"


# --- [повністю] ядро ---------------------------------------------------------------

def write_block(md_path: str, name: str, markdown: str) -> None:
    """Замінює вміст між <!-- report:begin name --> і <!-- report:end -->; текст поза маркерами не чіпає."""
    with open(md_path, encoding="utf-8", newline="") as f:
        text = f.read()
    pattern = re.compile(rf"(<!-- report:begin {re.escape(name)} -->)(.*?)(<!-- report:end -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"{md_path}: немає блоку «<!-- report:begin {name} -->» … «<!-- report:end -->» — додайте маркери")
    new = pattern.sub(lambda m: f"{m.group(1)}\n{markdown.strip()}\n{m.group(3)}", text, count=1)
    if new != text:
        with open(md_path, "w", encoding="utf-8", newline="") as f:
            f.write(new)


def load_rows(pattern: str) -> list[dict]:
    """Усі рядки файлів за шаблоном (у стабільному порядку); поле _file — назва файлу."""
    # Top-level globs exclude dev tuning and the explicitly interrupted 4B latency pilot
    # in results/exploratory/. Its raw rows are retained, but it is not a complete test matrix.
    rows = []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as f:
            rows += [{**json.loads(line), "_file": Path(path).name} for line in f if line.strip()]
    return rows


def by_file(rows: list[dict]) -> dict[str, list[dict]]:
    """Групує за файлом і відмовляється, якщо в одному файлі змішано різні промпти чи набори."""
    groups = defaultdict(list)
    for r in rows:
        groups[r["_file"]].append(r)
    for name, group in groups.items():
        for field in ("prompt_sha256", "dataset_sha256"):
            if len({r[field] for r in group}) > 1:
                raise SystemExit(f"{name}: різні {field} в одному файлі — змінений промпт чи набір пишіть у новий файл")
    return dict(sorted(groups.items()))


def latest_ok(rows: list[dict]) -> dict[str, dict]:
    """id → остання спроба без помилки."""
    return {r["id"]: r for r in rows if r.get("error_type") is None}


def error_summary(rows: list[dict]) -> str:
    """Помилки поза знаменником: id, в яких немає жодної успішної спроби."""
    ok, last = latest_ok(rows), {r["id"]: r for r in rows}
    kinds = Counter(r["error_type"] for i, r in last.items() if i not in ok)
    return ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "0"


def cost(rows: list[dict], prices: dict[str, tuple[float, float]]) -> float:
    """USD за реєстром models.py (або --price) з input_tokens / output_tokens."""
    total = 0.0
    for r in rows:
        spec = models.MODELS.get(r["alias"])
        price_in, price_out = prices.get(r["alias"], (spec.price_in, spec.price_out) if spec else (0.0, 0.0))
        total += ((r.get("input_tokens") or 0) * price_in + (r.get("output_tokens") or 0) * price_out) / 1e6
    return total


def md_table(headers: list[str], rows: list[list]) -> str:
    cell = lambda v: str(v).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows])


def frac(k: int, n: int) -> str:
    return f"{k}/{n}" if n else "—"


def acc_table(groups: dict[str, list[dict]], prices: dict) -> str:
    """n · точність · 95% ДІ Вілсона · hard · injection · помилки · вартість."""
    table = []
    for name, rows in groups.items():
        ok = list(latest_ok(rows).values())
        k, n = sum(bool(r["correct"]) for r in ok), len(ok)
        low, high = wilson_ci(k, n)
        tagged = lambda tag: [r for r in ok if tag in r["tags"]]  # noqa: E731
        table.append([name, rows[0]["model_requested"], rows[0]["prompt_version"], n,
                      f"{k / n:.2f}" if n else "—", f"[{low:.2f}; {high:.2f}]",
                      frac(sum(r["correct"] for r in tagged("hard")), len(tagged("hard"))),
                      frac(sum(r["correct"] for r in tagged("injection")), len(tagged("injection"))),
                      error_summary(rows), f"{cost(ok, prices):.4f}",
                      statistics.median(r["latency_ms"] for r in ok) if ok else "—",
                      f"{statistics.mean(r['output_tokens'] or 0 for r in ok):.1f}" if ok else "—"])
    return md_table(["файл", "модель", "промпт", "n", "точність", "95% ДІ", "hard", "injection", "помилки",
                     "вартість, $", "затримка, мс (медіана)", "вихідних токенів (сер.)"], table)


# --- [студент] блоки звіту -----------------------------------------------------------

def last_run(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["run_id"] == rows[-1]["run_id"]] if rows else []


def block_tokens(prices: dict) -> str:
    ratios = defaultdict(dict)  # токенізатор → id пари → множник (останній рядок перекриває)
    for r in load_rows("results/02-tokens.jsonl"):
        ratios[r["tokenizer"]][r["id"]] = r["ratio"]
    table = []
    for tokenizer, by_id in sorted(ratios.items()):
        values = list(by_id.values())
        q = statistics.quantiles(values, n=4) if len(values) > 1 else values * 3
        table.append([tokenizer, len(values), f"{statistics.median(values):.2f}", f"{q[0]:.2f}–{q[2]:.2f}"])
    return md_table(["токенізатор", "пар", "медіана ua/en", "міжквартильний розмах"], table) if table else NO_DATA


# … block_sampling і block_reasoning — ваші (вимоги нижче)


def block_ablation(prices: dict) -> str:
    groups = by_file(load_rows("results/03-*.jsonl"))
    return acc_table(groups, prices) if groups else NO_DATA


def block_flips(prices: dict) -> str:
    ok = {(g[0]["alias"], g[0]["prompt_version"]): latest_ok(g) for g in by_file(load_rows("results/03-*.jsonl")).values()}
    table = []
    for (alias, version), rows in sorted(ok.items()):
        base = ok.get((alias, "v0"))
        if base is None or version == "v0":
            continue
        common = sorted(set(base) & set(rows))
        fixed = sum(not base[i]["correct"] and rows[i]["correct"] for i in common)
        broken = sum(base[i]["correct"] and not rows[i]["correct"] for i in common)
        table.append([alias, f"v0 → {version}", len(common), fixed, broken])
    return md_table(["модель", "порівняння", "спільних id", "стали правильними", "стали хибними"], table) if table else NO_DATA


def block_structured(prices: dict) -> str:
    table = []
    for name, rows in by_file(load_rows("results/04-*.jsonl")).items():
        ok = list(latest_ok(rows).values())
        n = len(ok)
        valid = sum(bool(r["schema_valid"]) for r in ok)
        correct = sum(bool(r["correct"]) for r in ok)
        valid_wrong = sum(bool(r["schema_valid"]) and not r["correct"] for r in ok)
        finish = ", ".join(f"{f} {c}" for f, c in sorted(Counter(str(r["finish_reason"]) for r in ok).items()))
        out_tokens = round(statistics.mean(r["output_tokens"] or 0 for r in ok)) if ok else "—"
        table.append([name, rows[0]["api"], rows[0]["mode"], n, frac(valid, n), frac(correct, n), frac(valid_wrong, n),
                      finish, out_tokens, error_summary(rows)])
    headers = ["файл", "api", "режим", "n", "валідні", "правильні", "валідно, але хибно", "finish_reason",
               "вихідних токенів (сер.)", "помилки"]
    return md_table(headers, table) if table else NO_DATA


def block_tools(prices: dict) -> str:
    table = []
    for name, rows in by_file(load_rows("results/05-*.jsonl")).items():
        ok = list(latest_ok(rows).values())
        n = len(ok)
        right_tool = sum(set(t for t in r["tags"] if t in TOOLS) <= set(r["tools_called"]) for r in ok)
        calls = sum(len(r["tools_called"]) for r in ok)
        bad_args = sum(r["failures"].count("bad_args") for r in ok)
        stops = ", ".join(f"{s} {c}" for s, c in sorted(Counter(r["stop_reason"] for r in ok).items()))
        fails = ", ".join(f"{s} {c}" for s, c in sorted(Counter(f for r in ok for f in r["failures"]).items())) or "—"
        table.append([name, "так" if ok and ok[0]["tools_enabled"] else "ні", n, frac(sum(r["correct"] for r in ok), n),
                      frac(right_tool, n), frac(calls - bad_args, calls),
                      f"{statistics.mean(r['steps'] for r in ok):.1f}" if ok else "—", stops, fails])
    headers = ["файл", "інструменти", "n", "правильні", "потрібні інструменти викликано", "валідні аргументи",
               "кроків (сер.)", "причини зупинки", "збої"]
    return md_table(headers, table) if table else NO_DATA





def block_sampling(prices):
    groups = defaultdict(list)
    for r in last_run(load_rows("results/02-sampling.jsonl")):
        groups[(r["params"]["temperature"], str(r["params"].get("seed")))].append(r)
    table = [[temperature, seed, len(rows), len({norm(r["output_raw"] or "") for r in rows}),
              sum(bool(r["correct"]) for r in rows)] for (temperature, seed), rows in sorted(groups.items())]
    return md_table(["temperature", "seed", "прогонів", "різних відповідей", "правильних"], table) if table else NO_DATA


def block_reasoning(prices):
    groups = defaultdict(list)
    for r in last_run(load_rows("results/02-reasoning.jsonl")):
        groups[(r["model_requested"], r["params"]["reasoning_effort"])].append(r)
    table = []
    for (model, level), rows in sorted(groups.items()):
        table.append([model, level, frac(sum(bool(r["correct"]) for r in rows), len(rows)),
                      f"{statistics.mean(r['output_tokens'] or 0 for r in rows):.1f}",
                      f"{statistics.mean(r['reasoning_chars'] for r in rows):.1f}",
                      statistics.median(r["latency_ms"] for r in rows),
                      str(dict(sorted(Counter(str(r["finish_reason"]) for r in rows).items())))])
    return md_table(["модель", "рівень", "правильні", "вихідних токенів (сер.)", "символів думок (сер.)",
                     "затримка, мс (медіана)", "finish_reason"], table) if table else NO_DATA


def block_injection(prices):
    table = []
    for name, rows in by_file(load_rows("results/03-*.jsonl")).items():
        for key, r in sorted(latest_ok(rows).items()):
            if "injection" in r["tags"]:
                table.append([key, name, (r["output_raw"] or "")[:80], r["correct"]])
    return md_table(["id", "файл", "початок відповіді", "правильно"], table) if table else NO_DATA


def block_baseline(prices):
    from bench.baseline import predict
    from bench.data import load_jsonl, select
    test = select(load_jsonl("data/golden.jsonl"), split="test")
    n = len(test)
    k = sum(predict(ex.input) == ex.expected for ex in test)
    low, high = wilson_ci(k, n)
    return md_table(["метод", "k/n", "точність", "95% ДІ"],
                    [["словник, без LLM", frac(k, n), f"{k/n:.2f}", f"[{low:.2f}; {high:.2f}]"]])


BLOCKS = {
    "baseline": ("docs/lab1/task.md", block_baseline),
    "tokens": ("docs/lab1/basics.md", block_tokens),
    "sampling": ("docs/lab1/basics.md", block_sampling),
    "reasoning": ("docs/lab1/basics.md", block_reasoning),
    "ablation": ("docs/lab1/prompts.md", block_ablation),
    "injection": ("docs/lab1/prompts.md", block_injection),
    "flips": ("docs/lab1/prompts.md", block_flips),
    "structured": ("docs/lab1/structured.md", block_structured),
    "tools": ("docs/lab1/tools.md", block_tools),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks", nargs="*", help=f"блоки: {', '.join(BLOCKS)} (без аргументів — усі)")
    ap.add_argument("--price", action="append", default=[], help="перекрити ціну: alias=IN/OUT (USD за 1 млн)")
    args = ap.parse_args()
    unknown = set(args.blocks) - set(BLOCKS)
    if unknown:
        raise SystemExit(f"невідомі блоки: {sorted(unknown)}")
    prices = {}
    for item in args.price:
        alias, pair = item.split("=")
        price_in, price_out = pair.split("/")
        prices[alias] = (float(price_in), float(price_out))
    for name in args.blocks or BLOCKS:
        md_path, build = BLOCKS[name]
        write_block(md_path, name, build(prices))
        print(f"{md_path}: {name}")


if __name__ == "__main__":
    main()
