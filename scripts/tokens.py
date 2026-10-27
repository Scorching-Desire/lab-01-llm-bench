"""Measure the same ten bilingual pairs with o200k_base and the running model."""
import argparse
import json

import tiktoken
from dotenv import load_dotenv

from bench import clients, data, experiments, models


def model_counter(alias):
    def count(text):
        turn = clients.chat(alias, [{"role": "user", "content": text}], max_tokens=1, reasoning_effort="none")
        if turn.usage.input is None:
            raise ValueError("server did not report prompt tokens")
        return turn.usage.input
    baseline = count("")
    return lambda text: count(text) - baseline


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="local")
    ap.add_argument("--pairs", default="data/ua_en.jsonl")
    ap.add_argument("--out", default="results/02-tokens.jsonl")
    a = ap.parse_args()
    spec = models.get(a.model)
    common = experiments.context(a.model, a.pairs, "tokens")
    pairs = [json.loads(line) for line in open(a.pairs, encoding="utf-8") if line.strip()]
    encoding = tiktoken.get_encoding("o200k_base")
    counters = {"o200k_base": lambda text: len(encoding.encode(text)),
                f"{spec.alias}:{spec.model}": model_counter(spec.alias)}
    for pair in pairs:
        for tokenizer, count in counters.items():
            ua, en = count(pair["ua"]), count(pair["en"])
            if ua < 0 or en <= 0:
                raise ValueError("invalid token counts after baseline subtraction")
            data.append_row(a.out, data.new_row(**common, ts=data.utc_now(), id=pair["id"],
                params={**spec.params, "max_tokens": 1, "num_ctx": spec.num_ctx}, attempt=1,
                tokenizer=tokenizer, ua_tokens=ua, en_tokens=en, ratio=round(ua / en, 3)))
            print(f"{pair['id']} {tokenizer}: {ua}/{en} = {ua/en:.3f}", flush=True)


if __name__ == "__main__":
    main()
