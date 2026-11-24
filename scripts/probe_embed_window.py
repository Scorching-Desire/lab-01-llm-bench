"""Bracket a real input rejection with truncate=False and preserve its response."""

import json
import time
import urllib.error

from bench import data
from bench.embed import embed


def main():
    model = "bge-m3:latest"
    success, failure = 0, 256
    trials = []
    error_text = None

    def accepted(length):
        nonlocal error_text
        text = ("майстерня пломба обслуговування " * (length // 31 + 2))[:length]
        start = time.perf_counter()
        try:
            embed([text], model)
            ok = True
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            if exc.code not in {400, 413, 500} or not any(t in error_text.lower() for t in ("context", "length", "token")):
                raise
            ok = False
        trials.append(dict(chars=len(text), accepted=ok, seconds=round(time.perf_counter() - start, 3)))
        print(trials[-1], flush=True)
        return ok

    while accepted(failure):
        success, failure = failure, failure * 2
        if failure > 524288:
            raise RuntimeError("no input rejection within probe limit")
    while failure - success > 128:
        midpoint = (success + failure) // 2
        if accepted(midpoint):
            success = midpoint
        else:
            failure = midpoint
    row = dict(ts=data.utc_now(), git_sha=data.git_sha(), model=model, success_chars=success,
               failure_chars=failure, error=error_text, trials=trials)
    data.append_row("results/lab3/00-embed-window.jsonl", row)
    print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
