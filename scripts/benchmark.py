"""Run the local benchmark matrix. Cloud runs require an explicit separate command."""
import argparse
import subprocess
import sys
from pathlib import Path


def run(*args):
    subprocess.run([sys.executable, *args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["02", "03", "04", "05", "all"], default="all")
    ap.add_argument("--models", default="local,local-large")
    a = ap.parse_args()
    aliases = a.models.split(",")
    if not set(aliases) <= {"local", "local-large"}:
        ap.error("this script is local-only; invoke bench.run explicitly for cloud models")
    for name in ["data/golden.jsonl", "data/tool_cases.jsonl", "data/ua_en.jsonl",
                 "docs/lab1/task.md", *map(str, Path("prompts").glob("*.md"))]:
        committed = subprocess.run(["git", "show", f"HEAD:{name.replace(chr(92), '/')}"] ,
                                   check=True, capture_output=True).stdout
        if committed != Path(name).read_bytes():
            raise SystemExit(f"commit {name} before measuring test")
    if a.stage in ("02", "all"):
        # These are independent experiments; rerun only to new files to retain all raw rows.
        for filename in ("tokens", "sampling", "reasoning"):
            if Path(f"results/02-{filename}.jsonl").exists():
                raise SystemExit("stage 02 files already exist; use individual scripts with --out for a fresh run")
        run("scripts/tokens.py")
        run("scripts/sampling.py", "--id", "t07", "--runs", "10")
        run("scripts/reasoning.py", "--levels", "none,high", "--limit", "10")
    for alias in aliases:
        if a.stage in ("03", "all"):
            for version in ("v0", "v1", "v2", "v4"):
                run("-m", "bench.run", "--prompt", f"prompts/{version}.md", "--model", alias,
                    "--split", "test", "--resume")
        if a.stage in ("04", "all"):
            for mode in ("A", "B"):
                run("-m", "bench.run", "--prompt", "prompts/v4.md", "--model", alias,
                    "--split", "test", "--mode", mode, "--resume")
        if a.stage in ("05", "all"):
            for tools in ("station_status,booking_status", "none"):
                run("-m", "bench.run", "--prompt", "prompts/t1.md", "--model", alias,
                    "--data", "data/tool_cases.jsonl", "--split", "tool", "--tools", tools, "--resume")


if __name__ == "__main__":
    main()
