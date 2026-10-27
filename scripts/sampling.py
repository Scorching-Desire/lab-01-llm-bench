"""Ten repetitions of one hard test example in each of four sampling conditions."""
import argparse

from dotenv import load_dotenv

from bench import clients, data, experiments, models
from bench.task import SYSTEM

CONFIGS = [(0, 7), (0, None), (1, 7), (1, None)]


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="local")
    ap.add_argument("--data", default="data/golden.jsonl")
    ap.add_argument("--id", required=True)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--out", default="results/02-sampling.jsonl")
    a = ap.parse_args()
    spec = models.get(a.model)
    chosen = data.select(data.load_jsonl(a.data), split="test", tag="hard", ids=[a.id])
    if not chosen or a.runs < 1:
        ap.error("select a hard test id and a positive number of runs")
    ex = chosen[0]
    common = experiments.context(a.model, a.data, "sampling")
    for temperature, seed in CONFIGS:
        for index in range(1, a.runs + 1):
            turn = clients.generate(a.model, SYSTEM, ex.input, temperature=temperature, seed=seed)
            experiments.record(a.out, common, ex, turn,
                {**spec.params, "temperature": temperature, "seed": seed, "num_ctx": spec.num_ctx}, run_index=index)


if __name__ == "__main__":
    main()
