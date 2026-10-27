"""Resume the Gemini matrix with bounded concurrency and a shared per-request rate limit."""
import argparse
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from bench import clients, data, models, run


class NotDispatched(BaseException):
    """No API call was made, so this cancellation must not create a result row."""


def jobs(stages):
    result = []
    if "04" in stages:
        for mode in ("B", "A"):
            result.append((f"04-{mode}", "gemini-native", "prompts/v4.md", "data/golden.jsonl", "test", "q15",
                           ["--mode", mode], f"results/04-{mode}-gemini-native.jsonl"))
    if "03" in stages:
        for version in ("v0", "v1", "v2", "v4"):
            result.append((f"03-{version}", "gemini", f"prompts/{version}.md", "data/golden.jsonl", "test", "q15",
                           [], f"results/03-{version}-gemini.jsonl"))
    if "05" in stages:
        for tools, name in (("station_status,booking_status", "tools"), ("none", "notools")):
            result.append((f"05-{name}", "gemini-native", "prompts/t1.md", "data/tool_cases.jsonl", "tool", None,
                           ["--tools", tools], f"results/05-t1-gemini-native-{name}.jsonl"))
    return result


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--max-rpm", type=float, default=6)
    ap.add_argument("--retry-attempts", type=int, default=5)
    ap.add_argument("--stages", default="04,03,05")
    a = ap.parse_args()
    if a.workers < 1 or a.max_rpm <= 0 or a.retry_attempts < 1 or not set(a.stages.split(",")) <= {"03", "04", "05"}:
        ap.error("positive workers/rpm and stages 03,04,05 required")
    # Freeze corpus, hypotheses and prompts before any test request.
    for name in ("data/golden.jsonl", "data/tool_cases.jsonl", "docs/lab1/task.md",
                 *map(str, Path("prompts").glob("*.md"))):
        committed = subprocess.run(["git", "show", "HEAD:" + name.replace("\\", "/")],
                                   check=True, capture_output=True).stdout
        if committed != Path(name).read_bytes():
            raise SystemExit(f"commit {name} before cloud measurements")
    tasks = []
    batch = data.utc_now().replace(":", "-") + "_cloud_" + uuid.uuid4().hex[:8]
    for stage, alias, prompt, dataset, split, tag, extra, out in jobs(a.stages.split(",")):
        clients._client(models.get(alias))  # initialize before sharing the HTTP clients across workers
        done = {r["id"] for r in data.read_rows(out) if r["error_type"] is None}
        for ex in data.select(data.load_jsonl(dataset), split=split, tag=tag):
            if ex.id not in done:
                args = ["--prompt", prompt, "--model", alias, "--data", dataset, "--split", split,
                        "--ids", ex.id, "--out", out, "--resume", "--run-id", batch + "_" + stage, *extra]
                if tag:
                    args += ["--tag", tag]
                tasks.append((stage, ex.id, out, args))
    stop = threading.Event()
    rate_lock = threading.Lock()
    local = threading.local()
    next_request = [0.0]

    def chat(alias, messages, **kwargs):
        with rate_lock:
            if stop.is_set() and not local.started:
                raise NotDispatched()
            time.sleep(max(0, next_request[0] - time.monotonic()))
            if stop.is_set() and not local.started:
                raise NotDispatched()
            next_request[0] = time.monotonic() + 60 / a.max_rpm
            local.started = True
        try:
            return clients.chat(alias, messages, **kwargs)
        except Exception as exc:
            # A 503 may recover with the runner's bounded backoff. Quota/auth errors
            # stop new cases immediately; exhausted transient errors stop them below.
            if run.error_type(exc) not in {"server", "timeout"}:
                stop.set()
            raise exc

    def work(task):
        stage, case_id, out, args = task
        local.started = False
        if stop.is_set():
            return "skipped", stage, case_id
        try:
            run.main(args, concurrency=a.workers, retry_attempts=a.retry_attempts, chat=chat)
        except NotDispatched:
            return "skipped", stage, case_id
        rows = [r for r in data.read_rows(out) if r["id"] == case_id]
        last = rows[-1]
        if last["error_type"]:
            stop.set()
        return last["error_type"] or "ok", stage, case_id

    print(f"{batch}: pending={len(tasks)}, max concurrency={a.workers}, max RPM={a.max_rpm}", flush=True)
    failed = 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(work, task) for task in tasks]
        for future in as_completed(futures):
            state, stage, case_id = future.result()
            failed += state != "ok"
            if state != "skipped":
                print(f"{data.utc_now()} {stage} {case_id}: {state}", flush=True)
    print(f"Finished: complete={len(tasks)-failed}/{len(tasks)}. Resume with the same settings.", flush=True)
    raise SystemExit(int(bool(failed)))


if __name__ == "__main__":
    main()
