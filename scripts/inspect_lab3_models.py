"""Record local artifact fingerprints and runtime metadata without publishing weights."""

import hashlib
import json
import urllib.request
from pathlib import Path

from bench import data


def main():
    names = ("qwen3:0.6b", "bge-m3:latest", "lab3-qwen06-base:latest", "lab3-qwen06-lora:latest")
    models = []
    for name in names:
        request = urllib.request.Request("http://localhost:11434/api/show",
                    data=json.dumps(dict(model=name)).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            record = json.load(response)
        models.append(dict(name=name, details=record.get("details"), model_info=record.get("model_info"),
                           template_sha256=hashlib.sha256(record.get("template", "").encode()).hexdigest(),
                           parameters=record.get("parameters")))
    files = []
    for path in (Path("models/lab3/adapter/adapter_model.safetensors"),
                 Path("models/lab3/base-q8.gguf"), Path("models/lab3/merged-lora-q8.gguf")):
        files.append(dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=data.sha256_file(path)))
    data.append_row("results/lab3/05-artifacts.jsonl", dict(ts=data.utc_now(), git_sha=data.git_sha(), models=models, files=files))
    print([(m["name"], m["template_sha256"]) for m in models])


if __name__ == "__main__":
    main()
