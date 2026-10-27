"""Measure local context without making any cloud request."""
import json
import os
import subprocess
from pathlib import Path

from check_env import canary, http_json, safely
from dotenv import load_dotenv


def main():
    load_dotenv()
    base = os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.environ.get("LOCAL_MODEL", "qwen3:4b")
    ok, detail = safely(lambda: canary(base, model))
    server = base.removesuffix("/v1")
    show = http_json(server + "/api/show", {"model": model}, timeout=30)
    evidence = {"model": model, "canary_ok": ok, "detail": detail,
                "thinking": show.get("thinking"), "capabilities": show.get("capabilities"),
                "model_info": show.get("model_info"), "version": http_json(server + "/api/version"),
                "loaded": http_json(server + "/api/ps")}
    # Metadata is not a benchmark result row; it lives in docs, outside results/*.jsonl.
    target = Path("docs/lab1/local-probe.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"local canary: {ok}; {detail}", flush=True)
    if not ok:
        raise SystemExit(1)
    # check_env's --live would call Gemini, so it is deliberately not used here.
    subprocess.run(["git", "status", "--short"], check=True)


if __name__ == "__main__":
    main()
