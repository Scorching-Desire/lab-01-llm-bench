"""Local embeddings using Ollama /api/embed with explicit truncation rejection."""

import json
import math
import os
import urllib.request


def embed(texts, model="bge-m3:latest"):
    base = os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1").rstrip("/").removesuffix("/v1")
    body = json.dumps(dict(model=model, input=texts, truncate=False, keep_alive="10m")).encode("utf-8")
    request = urllib.request.Request(base + "/api/embed", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        vectors = json.load(response)["embeddings"]
    if len(vectors) != len(texts) or any(not v or any(not math.isfinite(x) for x in v) for v in vectors):
        raise ValueError("invalid embedding response")
    return vectors
