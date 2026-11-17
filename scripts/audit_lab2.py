"""Check Lab 02 measurement coverage, hashes and deterministic scores."""

import hashlib
import subprocess
from functools import cache
from pathlib import Path

from bench import data, score

RESULTS = Path("results/lab2")
BASE = "cac1ac44b27d87d6cef5ea3eacdcb64f13711739"
SCORER = "f3233bb"


@cache
def blob_hash(sha, path):
    blob = subprocess.check_output(["git", "show", f"{sha}:{path}"])
    return hashlib.sha256(blob).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    subprocess.run(["git", "diff", "--exit-code", BASE, "HEAD", "--",
                    "data/golden.jsonl", "scripts/validate_golden.py"], check=True)
    subprocess.run(["git", "diff", "--exit-code", "--diff-filter=MDR", BASE, "HEAD", "--", "tests/"], check=True)
    corpus = {path.as_posix(): data.read_rows(path) for path in Path("data/lab2").glob("*.jsonl")
              if path.name != "generated.jsonl"}
    corpus_hashes = {data.sha256_file(path): path for path in corpus}
    indexed = {path: {r["id"]: r for r in rows} for path, rows in corpus.items()}
    hashes = set()
    successful = set()
    count = 0
    for file in sorted(RESULTS.glob("[0-9][0-9]-*.jsonl")):
        for number, row in enumerate(data.read_rows(file), 1):
            where = f"{file}:{number}"
            dataset = corpus_hashes.get(row["dataset_sha256"])
            require(dataset is not None, f"{where}: unrecognized dataset")
            prompt = f"prompts/{row['prompt_version']}.md"
            sha = row["git_sha"]
            require(blob_hash(sha, prompt) == row["prompt_sha256"], f"{where}: prompt hash mismatch")
            require(blob_hash(sha, dataset) == row["dataset_sha256"], f"{where}: dataset hash mismatch")
            source = indexed[dataset][row["id"]]
            require(row["channel"] == source["channel"] and row["media_sha256"] == source["input_sha256"],
                    f"{where}: media or channel mismatch")
            if file.name.startswith("02-"):
                hashes.add(row["prompt_sha256"])
                if not row["error_type"]:
                    successful.add((row["alias"], row["channel"], row["src_id"]))
            if file.name.startswith(("04-", "05-")):
                require(blob_hash(sha, "src/bench/score.py") == blob_hash(SCORER, "src/bench/score.py"),
                        f"{where}: scorer changed after freeze")
                if not row["error_type"]:
                    got = row["parsed"] or {}
                    codes = {key: score.compare_field(key, value, got.get(key))
                             for key, value in source["expected"].items()}
                    require(codes == row["fields_correct"], f"{where}: field scores differ")
                    exact = row["parsed"] is not None and all(value in {"ok", "empty_ok"} for value in codes.values())
                    require(row["correct"] == exact, f"{where}: exact-score mismatch")
            count += 1
    scope = corpus["data/lab2/docs.jsonl"]
    expected = {(alias, r["channel"], r["src_id"]) for r in scope for alias in ("local-vision", "gemini-lite-native")}
    require(successful == expected and len(hashes) == 1, "incomplete step 02 or mixed prompts")
    for file, n in {
        "04-fields-A-local-vision-extract.jsonl": 22,
        "04-fields-B-local-vision-extract.jsonl": 22,
        "04-fields-B-gemini-lite-native.jsonl": 15,
        "04-gen-local-vision-extract.jsonl": 6,
        "05-repair-local-vision-extract.jsonl": 22,
        "service-gemini.jsonl": 3,
    }.items():
        observed = {r["id"] for r in data.read_rows(RESULTS / file) if not r["error_type"]}
        require(len(observed) == n, f"{file}: expected {n}, found {len(observed)}")
    manifest = data.read_rows("data/lab2/generated.jsonl")
    require(3 <= len(manifest) <= 8, "generated image count out of range")
    variants = corpus["data/lab2/synth-variants.jsonl"]
    for image in manifest:
        pair = [row for row in variants if row["src_id"] == image["record_id"]]
        require(len(pair) == 2 and {row["variant"] for row in pair} == {"plain", "gen"}
                and pair[0]["expected"] == pair[1]["expected"]
                and data.sha256_file(image["file"]) == image["sha256"], "bad generated pair or hash")
    print(f"OK: {count} benchmark rows checked, 90 step-02 cells and {len(manifest)} generated pairs")


if __name__ == "__main__":
    main()
