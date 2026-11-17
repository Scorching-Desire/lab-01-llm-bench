"""Validate Lab 02 datasets and their media against the frozen Lab 01 corpus."""

import argparse
from collections import Counter
from pathlib import Path

from pydantic import ValidationError
from validate_golden import check_file, summary

from bench import data, media
from bench.schema_fields import DocFields

ROOT = Path(__file__).resolve().parents[1]
AWKWARD = {"empty", "twins", "date_format", "long_list", "comma_number", "boundary"}


def validate(path):
    rows, errors = check_file(str(path), {"dev", "test"})
    media_root = ROOT / "data/lab2/media"
    counts = Counter(r.get("channel") for r in rows)
    print(summary(rows), f"channels: {dict(counts)}")
    if path.name == "docs.jsonl":
        golden, problems = check_file(str(ROOT / "data/golden.jsonl"), {"dev", "test"})
        errors.extend(problems)
        expected = {r["id"]: r for r in golden if r["split"] == "test" and {"q15", "injection"}.intersection(r["tags"])}
        pairs = [(r.get("src_id"), r.get("channel")) for r in rows]
        channels = {"text", "clean"} | ({"scan"} if "scan" in counts else set())
        if len(set(pairs)) != len(pairs) or set(pairs) != {(key, ch) for key in expected for ch in channels}:
            errors.append("incomplete or duplicated source/channel matrix")
        for row in rows:
            original = expected.get(row.get("src_id"))
            if not original or row["input"] != original["input"] or row["expected"] != {"label": original["expected"]}:
                errors.append(f"{row['id']}: differs from Lab 01")
    else:
        for row in rows:
            try:
                DocFields.model_validate(row["expected"])
            except ValidationError as exc:
                errors.append(f"{row['id']}: {exc}")
        if path.name in {"synth.jsonl", "synth-images.jsonl"}:
            splits = Counter(r["split"] for r in rows)
            qc = [r for r in rows if "qc" in r["tags"]]
            if splits["dev"] != 8 or splits["test"] < 22 or len(qc) != 15 or any(r["split"] != "test" for r in qc):
                errors.append("expected dev=8, test>=22 and exactly 15 test qc")
            if sum(bool(AWKWARD.intersection(r["tags"])) for r in qc) < 6:
                errors.append("qc requires six awkward documents")
    for row in rows:
        path_value = row.get("input_file")
        channel = row.get("channel")
        if channel == "text":
            if path_value is not None or row.get("input_sha256") is not None:
                errors.append(f"{row['id']}: text must have no media")
            continue
        if channel not in {"clean", "scan"} or not isinstance(path_value, str):
            errors.append(f"{row['id']}: invalid image channel or missing media")
            continue
        image_path = (ROOT / path_value).resolve()
        try:
            if not image_path.is_relative_to(media_root.resolve()):
                raise ValueError("image outside dataset directory")
            media.encode(str(image_path))
            if data.sha256_file(image_path) != row.get("input_sha256"):
                raise ValueError("image SHA-256 mismatch")
        except (ValueError, OSError) as exc:
            errors.append(f"{row['id']}: {exc}")
    size = sum(p.stat().st_size for p in media_root.rglob("*") if p.is_file())
    print(f"media: {size} bytes")
    if size > media.MAX_DIR_BYTES:
        errors.append("media directory exceeds 40 MiB")
    if not any((ROOT / "data/lab2/fonts").glob("LICENSE*")):
        errors.append("missing font license")
    attrs = ROOT / ".gitattributes"
    if attrs.exists() and "filter=lfs" in attrs.read_text(encoding="utf-8"):
        errors.append("Git LFS is forbidden")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("data/lab2/docs.jsonl"))
    args = parser.parse_args()
    errors = validate(ROOT / args.path)
    for error in errors:
        print("ПОМИЛКА", error)
    print(f"помилок: {len(errors)}" if errors else "OK")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
