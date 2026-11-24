"""Convert merged weights to GGUF Q8 and import them into local Ollama."""

import subprocess
import sys
from pathlib import Path


def main():
    root = Path("models/lab3").resolve()
    if not (root / "merged/model.safetensors").is_file():
        raise SystemExit("run train_lora.py before importing")
    converted = root / "merged-lora-q8.gguf"
    if not converted.exists():
        subprocess.run([sys.executable, str(root / "llama.cpp/convert_hf_to_gguf.py"), str(root / "merged"),
                        "--outfile", str(converted), "--outtype", "q8_0"], check=True)
    modelfile = root / "Modelfile"
    modelfile.write_text(f'FROM "{converted.as_posix()}"\n'
                        "PARAMETER num_ctx 16384\nPARAMETER temperature 0\nPARAMETER seed 7\n",
                        encoding="utf-8")
    subprocess.run(["ollama", "create", "lab3-qwen06-lora", "-f", str(modelfile)], check=True)


if __name__ == "__main__":
    main()
