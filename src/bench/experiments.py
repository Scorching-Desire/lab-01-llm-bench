"""Shared recording for real basic experiments, using the v2 Turn client."""
import uuid

from bench import data, models, score


def context(alias, dataset, kind):
    spec = models.get(alias)
    return dict(run_id=f"{data.utc_now().replace(':', '-')}_{kind}_{alias}_{uuid.uuid4().hex[:8]}",
                git_sha=data.git_sha(), dataset_sha256=data.sha256_file(dataset), alias=alias,
                api=spec.api, model_requested=spec.model, concurrency=1)


def record(path, common, example, turn, params, **extra):
    parsed = score.parse_output(turn.text or "")
    row = data.new_row(**common, ts=data.utc_now(), params=params, id=example.id, split=example.split,
                       tags=example.tags, model_reported=turn.model_reported, output_raw=turn.text,
                       parsed=parsed, correct=score.is_correct(example.expected, parsed),
                       finish_reason=turn.finish_reason, input_tokens=turn.usage.input,
                       output_tokens=turn.usage.output, reasoning_tokens=turn.usage.reasoning,
                       cached_tokens=turn.usage.cached, latency_ms=turn.latency_ms, attempt=1, **extra)
    data.append_row(path, row)
    print(f"{example.id}: {row['correct']}, {turn.finish_reason}, {turn.latency_ms} ms", flush=True)
