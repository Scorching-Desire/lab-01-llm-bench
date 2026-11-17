"""Shared extraction entry point for the dataset runner and the service CLI."""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from bench import clients, data, models, prompts, score
from bench.schema import TicketLabel


def extract(document, prompt, *, model, mode, repair=False, chat=clients.chat):
    media = None if document.channel == "text" else [document.input_file]
    if media:
        from bench.media import MediaError

        if not media[0] or data.sha256_file(media[0]) != document.input_sha256:
            raise MediaError("missing image or SHA-256 mismatch")
        document = replace(document, input="[документ подано зображенням]")
    messages = prompts.render(prompt, document, [])
    fields = prompt.version.startswith("lab2-fields-")
    if fields:
        from bench.schema_fields import DocFields

        schema = DocFields
    else:
        schema = TicketLabel
    constraint = schema if mode == "B" else None

    def parse(turn):
        try:
            payload = json.loads(score.clean(turn.text or ""))
            schema.model_validate(payload)
            return payload
        except (ValueError, ValidationError):
            return None

    turn = chat(model, messages, schema=constraint, media=media)
    before = parse(turn)
    turns = [turn]
    if not fields:
        return before, before, turns, None

    from bench import verify

    flags = verify.check(before)
    final = before
    error = None
    if flags and before is not None and repair:
        feedback = "\n".join(f"{flag['code']}: {flag['message']}" for flag in flags)
        try:
            retry = chat(model, [*messages, {"role": "user", "content": feedback}],
                         schema=constraint, media=media, max_tokens=512, timeout=60)
            turns.append(retry)
            replacement = parse(retry)
            if replacement is None:
                error = "invalid"
            else:
                final = replacement
        except Exception as exc:
            from bench.run import error_type

            error = error_type(exc)
    after = verify.check(final)
    return final, before, turns, dict(flags_before=flags, flags_after=after, repaired=len(turns) > 1,
                                      repair_error=error, status="invalid" if final is None else
                                      "flagged" if after else "verified")


def benchmark_row(example, prompt, common, attempt, repair, chat, out):
    from bench.media import MediaError
    from bench.run import with_retries

    row = data.new_row(**common, id=example.id, src_id=example.src_id, split=example.split,
                       tags=example.tags, channel=example.channel, media=example.input_file,
                       media_sha256=example.input_sha256, variant=example.variant, attempt=attempt,
                       repair_enabled=repair, fields_correct=None, verify=None)
    start = time.perf_counter()
    # The service sees only the input document. Scoring runs after extraction.
    document = replace(example, expected=None)
    result, error = with_retries(lambda: extract(document, prompt, model=common["alias"],
                                                mode=common["mode"], repair=repair, chat=chat), attempts=1)
    row.update(ts=data.utc_now(), latency_ms=round((time.perf_counter() - start) * 1000))
    if error:
        row.update(error_type="media" if error[1].startswith(MediaError.__name__ + ":") else error[0], error=error[1])
        return row
    final, before, turns, verification = result
    turn = turns[-1]
    row.update(parsed=final, output_raw=turn.text, schema_valid=final is not None,
               model_reported=turn.model_reported, finish_reason=turn.finish_reason)
    for name in ("input", "output", "reasoning", "cached"):
        counts = [getattr(t.usage, name) for t in turns if getattr(t.usage, name) is not None]
        row[f"{name}_tokens"] = sum(counts) if counts else None
    if verification is not None:
        row["verify"] = verification
    if repair and verification is not None:
        trace = Path(out).parent / "traces" / f"{common['run_id']}.jsonl"
        for index, item in enumerate(turns, 1):
            data.append_row(trace, dict(id=example.id, step=index, output=item.text,
                                        latency_ms=item.latency_ms, finish_reason=item.finish_reason))
    if not isinstance(example.expected, dict) or verification is None:
        target = example.expected.get("label") if isinstance(example.expected, dict) else example.expected
        row["correct"] = score.is_correct(target, final) if target is not None else None
        return row
    row["fields_correct"] = {key: score.compare_field(key, value, (final or {}).get(key))
                             for key, value in example.expected.items()}
    row["correct"] = final is not None and all(v in {"ok", "empty_ok"} for v in row["fields_correct"].values())
    verification["fields_correct_before"] = {
        key: score.compare_field(key, value, (before or {}).get(key)) for key, value in example.expected.items()
    }
    return row


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="path", required=True)
    parser.add_argument("--model", default="local-vision-extract")
    parser.add_argument("--mode", choices=["A", "B"], default="B")
    parser.add_argument("--prompt", default="prompts/lab2-fields-v1.md")
    parser.add_argument("--no-repair", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    path = Path(args.path)
    channel = "text" if path.suffix.lower() == ".txt" else "clean"
    example = data.Example(path.stem, path.read_text(encoding="utf-8") if channel == "text" else "",
                           None, "service", [], channel=channel,
                           input_file=str(path) if channel != "text" else None,
                           input_sha256=data.sha256_file(path) if channel != "text" else None)
    spec = models.get(args.model)
    prompt = prompts.load_prompt(args.prompt)
    common = dict(run_id=f"service-{data.utc_now().replace(':', '-')}", git_sha=data.git_sha(),
                  dataset_sha256=data.sha256_file(path), prompt_version=prompt.version, prompt_sha256=prompt.sha256,
                  alias=spec.alias, api=spec.api, model_requested=spec.model, mode=args.mode,
                  params={**spec.params, "num_ctx": spec.num_ctx}, concurrency=1)
    row = benchmark_row(example, prompt, common, 1, not args.no_repair, clients.chat,
                        args.out or "results/lab2/service.jsonl")
    if args.out:
        data.append_row(args.out, row)
    print(json.dumps(row, ensure_ascii=False))
    return int(bool(row["error_type"]))


if __name__ == "__main__":
    raise SystemExit(main())
