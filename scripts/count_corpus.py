"""Estimate corpus tokens from ten measured local-chat input-token ratios."""

import statistics
import subprocess
from pathlib import Path

from bench import clients, data


def main():
    alias = "local-fast"

    def count(text):
        return clients.chat(alias, [{"role": "user", "content": text}], max_tokens=1).usage.input

    overhead = count("x")
    samples = data.read_rows("data/lab3/chunks.jsonl")[:10]
    measured = [dict(chars=len(row["text"]), input_tokens=count(row["text"])) for row in samples]
    ratio = statistics.median((row["input_tokens"] - overhead) / row["chars"] for row in measured)
    chars = sum(len(Path(row["path"]).read_text(encoding="utf-8")) for row in data.read_rows("data/lab3/manifest.jsonl"))
    ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    row = dict(ts=data.utc_now(), git_sha=data.git_sha(), alias=alias, chars=chars, overhead=overhead,
               samples=measured, tokens_per_char=ratio, estimated_tokens=round(chars * ratio), ollama_ps=ps)
    data.append_row("results/lab3/00-corpus-window.jsonl", row)
    print(row)


if __name__ == "__main__":
    main()
