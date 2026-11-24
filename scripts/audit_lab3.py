"""Audit frozen provenance, query coverage and literal RAG evidence."""

import hashlib
import subprocess
from functools import cache
from pathlib import Path

from bench import data, score

BASE = "5fd166097772004b0e6b2d2e53378860e08e1595"
CONFIG = "src/bench/retrieval_config.py"
CORE = "prompts/lab3-core-v1.md"


@cache
def committed(sha, path):
    return subprocess.check_output(["git", "show", f"{sha}:{path}"])


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    subprocess.run(["git", "diff", "--exit-code", BASE, "HEAD", "--", "data/golden.jsonl",
                    "data/lab2/synth.jsonl", "src/bench/schema_fields.py"], check=True)
    subprocess.run(["git", "diff", "--exit-code", "--diff-filter=MDR", BASE, "HEAD", "--", "tests/"], check=True)
    indexed = {c["chunk_id"]: c for c in data.read_rows("data/lab3/chunks.jsonl")}
    query_rows = data.read_rows("data/lab3/queries.jsonl")
    query_by_id = {q["id"]: q for q in query_rows}
    test_ids = {q["id"] for q in query_rows if q["split"] == "test"}
    total = 0
    for filename in ("01-lex", "01-dense", "02-single-best", "02-rrf", "03-rag-q8",
                     "04-q8-prompting", "04-q8-rag", "04-q8-lora"):
        path = Path(f"results/lab3/{filename}.jsonl")
        rows = data.read_rows(path)
        successful = {r["id"] for r in rows if not r["error_type"]}
        require(successful == test_ids, f"{path}: incomplete test IDs")
        for row in rows:
            total += 1
            where = f"{path}:{row['id']}"
            sha = row["git_sha"]
            require(hashlib.sha256(committed(sha, "data/lab3/queries.jsonl")).hexdigest() == row["dataset_sha256"],
                    f"{where}: uncommitted dataset")
            require(hashlib.sha256(committed(sha, CONFIG)).hexdigest() == row["config_sha256"] == data.sha256_file(CONFIG),
                    f"{where}: configuration changed")
            require(committed(sha, "data/lab3/manifest.jsonl") == Path("data/lab3/manifest.jsonl").read_bytes(),
                    f"{where}: corpus manifest changed")
            if filename.startswith(("03", "04")):
                require(hashlib.sha256(committed(sha, CORE)).hexdigest() == row["core_prompt_sha256"] == data.sha256_file(CORE),
                        f"{where}: core changed")
                require(committed(sha, "src/bench/score.py") == committed("HEAD", "src/bench/score.py"),
                        f"{where}: scoring changed")
                require(committed(sha, "docs/lab3/hypotheses.md") == Path("docs/lab3/hypotheses.md").read_bytes(),
                        f"{where}: hypotheses changed")
                expected = query_by_id[row["id"]]
                correct = row["status"] == "refused" if "absent" in row["tags"] else score.answer_correct(
                    expected["expected"], row["answer_text"])
                require(correct == row["correct"], f"{where}: scorer mismatch")
                for citation in row["citations"]:
                    source = indexed.get(citation["chunk_id"])
                    require(source is not None and source["doc_id"] == citation["doc_id"]
                            and citation["chunk_id"] in row["retrieved"] and citation["quote"] in source["text"]
                            and citation["quote"].strip(), f"{where}: invalid citation")
                require(row["status"] != "grounded" or row["citations"], f"{where}: ungrounded status")
                require(row["params"]["num_ctx"] == 16384, f"{where}: missing explicit context")
    attacks = data.read_rows("results/lab3/03-attacks-q8.jsonl")
    require({r["id"] for r in attacks} == {r["id"] for r in data.read_rows("data/lab3/attacks.jsonl")},
            "attack pool incomplete")
    adaptation = data.read_rows("results/lab3/05-training.jsonl")[-1]
    require(adaptation["status"] == "trained" and len(adaptation["step_seconds"]) == 32,
            "training evidence incomplete")
    require(all(row["adapter_sha256"] == adaptation["adapter_sha256"]
                for row in data.read_rows("results/lab3/04-q8-lora.jsonl")),
            "adapter fingerprint mismatch")
    reported = {line: {r["model_reported"] for r in data.read_rows(f"results/lab3/04-q8-{line}.jsonl")}
                for line in ("prompting", "rag", "lora")}
    require(reported["prompting"] == reported["rag"] and reported["lora"].isdisjoint(reported["prompting"])
            and all(None not in names for names in reported.values()), "base/adapter runtime identity mismatch")
    artifacts = data.read_rows("results/lab3/05-artifacts.jsonl")[-1]
    imported = [m for m in artifacts["models"] if m["name"].startswith("lab3-")]
    require(len(imported) == 2 and imported[0]["template_sha256"] == imported[1]["template_sha256"]
            and all(m["details"]["quantization_level"] == "Q8_0" for m in imported),
            "matched Q8 import metadata missing")
    require(subprocess.check_output(["git", "ls-files", ".index", "models/lab3"]).strip() == b"",
            "derived artifacts tracked")
    print(f"OK: {total} frozen test rows, {len(attacks)} attacks, 32 real training steps")


if __name__ == "__main__":
    main()
