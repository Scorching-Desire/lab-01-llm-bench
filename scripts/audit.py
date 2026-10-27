"""Check the official evidence package; missing evidence is a failure, never a fabricated pass."""
import argparse
import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path

from bench import data, prompts, score

REQUIRED = ["README.md", "pyproject.toml", "uv.lock", ".python-version", ".env.example", ".gitignore",
            ".github/workflows/tests.yml", *[f"docs/lab1/{name}.md" for name in
                ("README", "env", "task", "models", "chat-comparison", "basics", "prompts", "structured", "tools", "ai-usage")],
            *[f"src/bench/{name}.py" for name in ("clients", "models", "data", "score", "prompts", "schema", "run", "tools", "agent_loop")],
            *[f"tests/{name}.py" for name in ("conftest", "test_score", "test_clients", "test_run", "test_agent_loop")]]


@lru_cache(maxsize=None)
def committed_hash(sha, file):
    old = subprocess.run(["git", "show", f"{sha}:{file}"], capture_output=True, check=False)
    return hashlib.sha256(old.stdout).hexdigest() if old.returncode == 0 else None


def check_results():
    errors = []
    golden = {ex.id: ex for ex in data.load_jsonl("data/golden.jsonl") + data.load_jsonl("data/tool_cases.jsonl")}
    paths = [*Path("results").glob("*.jsonl"), *Path("results/reproduction").glob("*.jsonl"),
             *Path("results/exploratory").glob("*.jsonl")]
    for path in sorted(paths):
        for line, r in enumerate(data.read_rows(path), 1):
            prefix = f"{path}:{line}"
            missing = set(data.FIELDS) - r.keys()
            if missing:
                errors.append(f"{prefix}: missing fields {sorted(missing)}")
                continue
            if not r["ts"] or not r["git_sha"]:
                errors.append(f"{prefix}: missing timestamp/git SHA")
            if r["id"] in golden and not r["error_type"]:
                ex = golden[r["id"]]
                expected = score.is_correct(ex.expected, r["parsed"])
                if expected != r["correct"]:
                    errors.append(f"{prefix}: correct disagrees with deterministic scorer")
            if path.name.startswith(("03-", "04-", "05-")):
                version = r["prompt_version"]
                current = prompts.load_prompt(f"prompts/{version}.md")
                if current.sha256 != r["prompt_sha256"]:
                    errors.append(f"{prefix}: prompt hash mismatch")
                for file, expected_hash in [(f"prompts/{version}.md", r["prompt_sha256"]),
                    ("data/tool_cases.jsonl" if path.name.startswith("05-") else "data/golden.jsonl", r["dataset_sha256"])]:
                    if committed_hash(r["git_sha"], file) != expected_hash:
                        errors.append(f"{prefix}: {file} not committed at recorded SHA")
    return errors


def check_chat():
    path = Path("docs/lab1/chat/review.json")
    if not path.is_file():
        return False, "missing chat review manifest"
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
        source = Path(review["submitted_transcript"])
        assert data.sha256_file(source) == review["submitted_transcript_sha256"]
        assert data.sha256_file("data/golden.jsonl") == review["golden_sha256"]
        golden = {ex.id: ex for ex in data.load_jsonl("data/golden.jsonl")}
        records = review["records"]
        surfaces = {"ChatGPT", "Claude", "Gemini", "ollama"}
        ids = {"t01", "t07", "t08", "t24", "t25"}
        assert len(records) == 20
        assert {(r["surface"], r["id"]) for r in records} == {(s, i) for s in surfaces for i in ids}
        assert len({r["screenshot"] for r in records}) == 20
        for record in records:
            screenshot = Path(record["screenshot"])
            assert screenshot.suffix == ".png" and screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            assert data.sha256_file(screenshot) == record["screenshot_sha256"]
            assert record["expected"] == golden[record["id"]].expected
            assert record["parsed"] == score.parse_output(record["response_text"])
            assert record["correct"] == score.is_correct(record["expected"], record["parsed"])
        assert any(not r["correct"] for r in records)
        assert review["screenshots_visually_reviewed"] == 20
        assert review["student_confirmed_completion"]
        assert all(review["privacy_training_disabled"].get(s) is True for s in ("ChatGPT", "Claude", "Gemini"))
    except (KeyError, ValueError, TypeError, OSError, AssertionError) as exc:
        return False, f"chat evidence validation failed: {type(exc).__name__}: {exc}"
    correct = sum(r["correct"] for r in records)
    return True, (f"20 records/PNG hashes and scores checked; {correct}/20 correct, {20-correct} errors; "
                  "privacy confirmed by student; model-ID/crop limitations in chat-comparison.md")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    a = ap.parse_args()
    selection_path = Path("docs/lab1/cloud-selection.json")
    selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.exists() else {}
    cloud_compatible = selection.get("openai_alias", "gemini")
    cloud_native = selection.get("native_alias", "gemini-native")
    rows = []

    def add(name, ok, detail):
        rows.append((name, "OK" if ok else "MISSING", detail))

    missing = [p for p in REQUIRED if not Path(p).is_file()]
    add("Required files", not missing, ", ".join(missing) or "present")
    result_errors = check_results()
    add("Raw result provenance and scoring", not result_errors, "; ".join(result_errors[:8]) or "all existing rows checked")
    for name, minimum in [("tokens", 20), ("sampling", 40), ("reasoning", 20)]:
        result = data.read_rows(f"results/02-{name}.jsonl")
        add(f"02 {name}", len(result) >= minimum, f"{len(result)} rows, need >= {minimum}")
    for alias in ("local", "local-fast", cloud_compatible):
        target = 25 if alias.startswith("local") else 15
        for version in ("v0", "v1", "v2", "v4"):
            result = data.read_rows(f"results/03-{version}-{alias}.jsonl")
            count = len({r["id"] for r in result if not r["error_type"]})
            add(f"03 {version} {alias}", count == target, f"{count}/{target} unique successful ids")
    for alias in ("local", "local-fast", cloud_native):
        target = 25 if alias.startswith("local") else 15
        for mode in ("A", "B"):
            result = data.read_rows(f"results/04-{mode}-{alias}.jsonl")
            count = len({r["id"] for r in result if not r["error_type"]})
            add(f"04 {mode} {alias}", count == target, f"{count}/{target} successful ids")
    for alias in ("local", "local-fast", cloud_native):
        for mode in ("tools", "notools"):
            result = data.read_rows(f"results/05-t1-{alias}-{mode}.jsonl")
            count = len({r["id"] for r in result if not r["error_type"]})
            add(f"05 {mode} {alias}", count == 8, f"{count}/8 successful ids")
    chat_ok, chat_detail = check_chat()
    add("Chat comparison records and screenshots", chat_ok, chat_detail)
    review_path = Path("docs/lab1/annotation-review.json")
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    reviewed = (review.get("golden_labels") == 33 and review.get("tool_labels") == 8
                and all(data.sha256_file(path) == digest for path, digest in review.get("dataset_sha256", {}).items())
                and len(review.get("dataset_sha256", {})) == 2)
    add("Student label review", reviewed, "explicit student confirmation and matching dataset hashes in annotation-review.json")
    add("Group registration", False, "user will add it manually; no confirmation recorded")
    add("Weekly snapshots and oral defense", False, "historical attendance/snapshots and personal defense cannot be manufactured")
    table = "| Check | Status | Evidence |\n|---|---|---|\n" + "\n".join(
        f"| {name} | {state} | {detail.replace('|', '/')} |" for name, state, detail in rows) + "\n"
    print(table)
    if a.out:
        Path(a.out).write_text("# Evidence audit\n\n" + table, encoding="utf-8")
    raise SystemExit(int(any(state != "OK" for _, state, _ in rows)))


if __name__ == "__main__":
    main()
