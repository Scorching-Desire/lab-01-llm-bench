"""Train and merge a real Qwen3 adapter using local CUDA, outside tracked artifacts."""

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/lab3/train.jsonl")
    parser.add_argument("--base", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--revision")
    parser.add_argument("--out", default="models/lab3/adapter")
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=32)
    args = parser.parse_args()
    if min(args.rank, args.alpha, args.max_steps) < 1:
        parser.error("rank, alpha and max-steps must be positive")
    revision = args.revision or ("c1899de289a04d12100db370d81485cdf75e47ca"
                                 if args.base == "Qwen/Qwen3-0.6B" else None)
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.perf_counter()
    evidence = dict(base=args.base, revision=revision, rank=args.rank, alpha=args.alpha, target_modules=["q_proj", "v_proj"],
                    steps=args.max_steps, torch=torch.__version__, cuda=torch.version.cuda,
                    cuda_available=torch.cuda.is_available(), step_seconds=[],
                    git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    dataset_sha256=hashlib.sha256(Path(args.data).read_bytes()).hexdigest())
    output = Path("results/lab3/05-training.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA runtime unavailable in selected training environment")
        free, total = torch.cuda.mem_get_info()
        evidence.update(free_bytes=free, total_bytes=total, capability=torch.cuda.get_device_capability(),
                        device=torch.cuda.get_device_name())
        rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines()]
        if any(row.get("src_split") not in {"dev", "corpus"} for row in rows):
            raise ValueError("unexpected training provenance")
        torch.manual_seed(20261124)
        tokenizer = AutoTokenizer.from_pretrained(args.base, revision=revision)
        tokenizer.pad_token = tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(args.base, revision=revision, dtype=torch.float16).to("cuda")
        evidence["base_revision"] = getattr(base.config, "_commit_hash", None)
        model = get_peft_model(base, LoraConfig(r=args.rank, lora_alpha=args.alpha,
                               target_modules=["q_proj", "v_proj"], bias="none", task_type="CAUSAL_LM"))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
        model.enable_input_require_grads()
        trainable = [p for p in model.parameters() if p.requires_grad]
        evidence["trainable_parameters"] = sum(p.numel() for p in trainable)
        optimizer = torch.optim.AdamW(trainable, lr=0.0001)
        model.train()
        losses = []
        for step in range(args.max_steps):
            entry = rows[step % len(rows)]
            messages = entry["messages"]
            prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False,
                                                     add_generation_prompt=True, enable_thinking=False)
            full = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False)
            inputs = tokenizer(full, return_tensors="pt", truncation=True, max_length=1536).to("cuda")
            prefix_length = len(tokenizer(prefix, add_special_tokens=False)["input_ids"])
            labels = inputs["input_ids"].clone()
            labels[:, :min(prefix_length, labels.shape[1])] = -100
            if (labels != -100).sum() == 0:
                raise ValueError("training target truncated entirely")
            tick = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            loss = model(**inputs, labels=labels).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            torch.cuda.synchronize()
            seconds = time.perf_counter() - tick
            evidence["step_seconds"].append(round(seconds, 4))
            losses.append(float(loss.detach()))
            print(f"step={step + 1} loss={losses[-1]:.4f} seconds={seconds:.3f}", flush=True)
        model.save_pretrained(args.out)
        tokenizer.save_pretrained(args.out)
        adapter = Path(args.out) / "adapter_model.safetensors"
        evidence.update(adapter_sha256=hashlib.sha256(adapter.read_bytes()).hexdigest(),
                        adapter_bytes=adapter.stat().st_size, adapter_path=adapter.as_posix(), losses=losses)
        merged = model.merge_and_unload().to("cpu")
        merged.config.use_cache = True
        merged.save_pretrained("models/lab3/merged", safe_serialization=True)
        tokenizer.save_pretrained("models/lab3/merged")
        evidence["status"] = "trained"
    except Exception as exc:
        import traceback

        evidence.update(status="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        print(evidence["traceback"], flush=True)
    evidence.update(seconds=round(time.perf_counter() - started, 3),
                    ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    environment=os.path.abspath(os.sys.executable))
    with output.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(evidence, ensure_ascii=False) + "\n")
    return int(evidence["status"] != "trained")


if __name__ == "__main__":
    raise SystemExit(main())
