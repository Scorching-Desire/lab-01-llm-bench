"""All hard test cases plus other test cases, thinking off versus on."""
import argparse
import re

from dotenv import load_dotenv

from bench import clients, data, experiments, models
from bench.task import SYSTEM


def reasoning_text(turn):
    raw = turn.raw_assistant_message
    return (raw.get("reasoning_content") or raw.get("reasoning") or "") + "".join(
        re.findall(r"<think>(.*?)</think>", turn.text or "", re.S))


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="local")
    ap.add_argument("--data", default="data/golden.jsonl")
    ap.add_argument("--levels", default="none,high")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--out", default="results/02-reasoning.jsonl")
    a = ap.parse_args()
    if a.max_tokens < 4096 or a.limit < 10:
        ap.error("max-tokens >= 4096 and limit >= 10 are required")
    spec = models.get(a.model)
    test = data.select(data.load_jsonl(a.data), split="test")
    hard = [ex for ex in test if "hard" in ex.tags]
    chosen = hard + [ex for ex in test if ex not in hard][:max(0, a.limit - len(hard))]
    common = experiments.context(a.model, a.data, "reasoning")
    for level in a.levels.split(","):
        for ex in chosen:
            turn = clients.generate(a.model, SYSTEM, ex.input, max_tokens=a.max_tokens, reasoning_effort=level)
            experiments.record(a.out, common, ex, turn,
                {**spec.params, "reasoning_effort": level, "max_tokens": a.max_tokens, "num_ctx": spec.num_ctx},
                reasoning_chars=len(reasoning_text(turn)))


if __name__ == "__main__":
    main()
