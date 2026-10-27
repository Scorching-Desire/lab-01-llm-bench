"""Прогін набору через модель (кроки 03–05): uv run python -m bench.run --prompt prompts/v1.md --model local …

Прапорці: --split --tag --ids --ids-file --limit --mode A|B --out --resume --max-rpm --run-id --data --tools
"""
import argparse
import os
import random
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from bench import agent_loop, clients, data, models, prompts, schema, score

RETRYABLE = {"rate_limit", "server", "timeout"}


def error_type(exc: Exception) -> str:
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)  # openai / google-genai
    if code == 429:
        return "rate_limit"
    if isinstance(code, int) and code >= 500:
        return "server"
    if "timeout" in type(exc).__name__.lower():
        return "timeout"
    return "schema" if code == 400 and "schema" in str(exc).lower() else "other"


def with_retries(call, attempts: int = 5):
    """429 / 5xx / тайм-аут → експоненційна пауза з розкидом. Повертає (результат, (тип, текст) | None)."""
    for i in range(1, attempts + 1):
        try:
            return call(), None
        except Exception as exc:  # noqa: BLE001 — будь-яка помилка стає рядком результатів
            kind = error_type(exc)
            if kind not in RETRYABLE or i == attempts:
                text = f"{type(exc).__name__}: {exc}"
                for name, value in os.environ.items():  # текст помилки — без значень ключів
                    text = text.replace(value, "***") if name.endswith("_API_KEY") and value else text
                return None, (kind, text[:500])
            time.sleep(min(60, 2 ** i) + random.uniform(0, 1))


# --- [студент] оцінка відповіді (крок 03: clients.chat v1 повертає словник) -------

def evaluate(ex: data.Example, turn: clients.Turn, mode: str | None) -> tuple[object, bool | None, bool]:
    """Повертає (parsed, schema_valid, correct)."""
    if mode == "B":  # нативна схема: розбір уже зробив clients.chat
        parsed, valid = (turn.parsed.model_dump() if turn.parsed else None), turn.schema_valid
    elif mode == "A":  # формат лише в промпті: розбір і валідація Pydantic
        try:
            parsed, valid = schema.TicketLabel.model_validate_json(score.clean(turn.text or "")).model_dump(), True
        except ValidationError:
            parsed, valid = None, False
    else:  # крок 03: мітка з тексту, схема не застосовується
        parsed, valid = score.parse_output(turn.text or ""), None
    return parsed, valid, parsed is not None and score.is_correct(ex.expected, parsed)


def fill_turn(row: dict, ex: data.Example, turn: clients.Turn, mode: str | None) -> None:
    parsed, valid, correct = evaluate(ex, turn, mode)
    u = turn.usage
    row.update(model_reported=turn.model_reported, output_raw=turn.text, parsed=parsed, schema_valid=valid,
               correct=correct, finish_reason=turn.finish_reason, input_tokens=u.input, output_tokens=u.output,
               reasoning_tokens=u.reasoning, cached_tokens=u.cached, latency_ms=turn.latency_ms)

def fill_agent(row, ex, result, enabled, latency_ms):
    parsed = score.parse_output(result.final_text or "")
    u = result.usage_total
    row.update(output_raw=result.final_text, parsed=parsed, correct=score.is_correct(ex.expected, parsed),
               tools_enabled=enabled, stop_reason=result.stop_reason, steps=result.steps,
               failures=result.failures, tools_called=result.tools_called, input_tokens=u.input,
               output_tokens=u.output, reasoning_tokens=u.reasoning, cached_tokens=u.cached, latency_ms=latency_ms)


# --- ядро прогону --------------------------------------------------------------

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Прогін набору через модель")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", required=True, help="псевдонім з models.py")
    ap.add_argument("--data", default="data/golden.jsonl")
    ap.add_argument("--split")
    ap.add_argument("--tag")
    ap.add_argument("--ids", help="id через кому")
    ap.add_argument("--ids-file", help="файл з id (по одному в рядку)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--mode", choices=["A", "B"], help="крок 04: A — формат у промпті, B — нативна схема")
    ap.add_argument("--tools", help="крок 05: назви інструментів через кому або none")
    ap.add_argument("--out")
    ap.add_argument("--resume", action="store_true", help="пропустити id, що вже мають рядок без помилки")
    ap.add_argument("--max-rpm", type=float, help="не більше N запитів на хвилину")
    ap.add_argument("--run-id")
    return ap.parse_args(argv)


def default_out(a: argparse.Namespace, version: str) -> str:
    if a.tools is not None:
        return f"results/05-{version}-{a.model}-{'notools' if a.tools == 'none' else 'tools'}.jsonl"
    return f"results/04-{a.mode}-{a.model}.jsonl" if a.mode else f"results/03-{version}-{a.model}.jsonl"


def main(argv: list[str] | None = None, *, concurrency: int = 1, retry_attempts: int = 5, chat=None) -> None:
    load_dotenv()
    a = parse_args(argv)
    chat_fn = chat or clients.chat
    spec, prompt = models.get(a.model), prompts.load_prompt(a.prompt)
    examples = data.load_jsonl(a.data)
    ids = a.ids.split(",") if a.ids else None
    if a.ids_file:
        with open(a.ids_file, encoding="utf-8") as f:
            ids = f.read().split()
    out = Path(a.out or default_out(a, prompt.version))
    previous = data.read_rows(out)  # файл лише дописується: рядки не переписуються
    dataset_hash = data.sha256_file(a.data)
    for row in previous:
        if row["dataset_sha256"] != dataset_hash or row["prompt_sha256"] != prompt.sha256:
            raise ValueError("changed dataset or prompt: use a new output file")
        if row["alias"] != spec.alias or row["mode"] != (a.mode or "A"):
            raise ValueError("changed model or mode: use a new output file")
        if row["model_requested"] != spec.model or row["params"] != {**spec.params, "num_ctx": spec.num_ctx}:
            raise ValueError("changed model ID or parameters: use a new output file")
        if row["concurrency"] != concurrency:
            raise ValueError("changed concurrency: use a new output file")
    done = {r["id"] for r in previous if r["error_type"] is None}
    attempts = Counter(r["id"] for r in previous)
    todo = [ex for ex in data.select(examples, split=a.split, tag=a.tag, ids=ids, limit=a.limit)
            if not (a.resume and ex.id in done)]
    dev = data.select(examples, split="dev")
    run_id = a.run_id or f"{datetime.now(timezone.utc):%Y-%m-%dT%H-%M-%SZ}_{prompt.version}_{a.model}_{uuid.uuid4().hex[:8]}"
    tool_names = [] if a.tools in (None, "none") else a.tools.split(",")
    common = dict(run_id=run_id, git_sha=data.git_sha(), dataset_sha256=data.sha256_file(a.data),
                  prompt_version=prompt.version, prompt_sha256=prompt.sha256, alias=spec.alias, api=spec.api,
                  model_requested=spec.model, params={**spec.params, "num_ctx": spec.num_ctx},
                  mode=a.mode or "A", concurrency=concurrency)
    print(f"{run_id}: {len(todo)} прикладів → {out}")
    for ex in todo:
        messages = prompts.render(prompt, ex, dev)
        row = data.new_row(**common, id=ex.id, split=ex.split, tags=ex.tags, attempt=attempts[ex.id] + 1)
        start = time.perf_counter()
        if a.tools is None:
            use_schema = schema.TicketLabel if a.mode == "B" else None
            result, err = with_retries(lambda: chat_fn(spec.alias, messages, schema=use_schema), attempts=retry_attempts)
        else:
            trace = str(out.parent / "traces" / f"{run_id}.jsonl")
            result, err = with_retries(lambda: agent_loop.run_agent(
                spec.alias, messages, tool_names, run_id=run_id, case_id=ex.id, trace_path=trace, chat=chat_fn),
                attempts=retry_attempts)
        row["ts"] = data.utc_now()
        if err:  # рядок з error_type не рахується як хибна відповідь
            row.update(error_type=err[0], error=err[1])
        elif a.tools is None:
            fill_turn(row, ex, result, a.mode)
        else:
            fill_agent(row, ex, result, bool(tool_names), round((time.perf_counter() - start) * 1000))
        data.append_row(out, row)
        attempts[ex.id] += 1
        print(f"  {ex.id}: {row['error_type'] or ('правильно' if row['correct'] else 'хибно')}")
        if a.max_rpm:
            time.sleep(60 / a.max_rpm)


if __name__ == "__main__":
    main()
