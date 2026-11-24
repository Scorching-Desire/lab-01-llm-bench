"""Import an unadapted HF checkpoint through the same Q8 pipeline as the adapter."""

import subprocess
import sys
from pathlib import Path


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    root = Path("models/lab3").resolve()
    base = root / "base-hf"
    base.mkdir(parents=True, exist_ok=True)
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype="float16")
    model.save_pretrained(base, safe_serialization=True)
    AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B").save_pretrained(base)
    converted = root / "base-q8.gguf"
    subprocess.run([sys.executable, str(root / "llama.cpp/convert_hf_to_gguf.py"), str(base),
                    "--outfile", str(converted), "--outtype", "q8_0"], check=True)
    modelfile = root / "BaseModelfile"
    modelfile.write_text(f'FROM "{converted.as_posix()}"\n'
                        "PARAMETER num_ctx 16384\nPARAMETER temperature 0\nPARAMETER seed 7\n",
                        encoding="utf-8")
    subprocess.run(["ollama", "create", "lab3-qwen06-base", "-f", str(modelfile)], check=True)


if __name__ == "__main__":
    main()
