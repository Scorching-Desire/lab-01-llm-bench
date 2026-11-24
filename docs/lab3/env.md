# Середовище Lab 03

Дата прогонів 24 листопада 2026 року. Windows, AMD Ryzen 5 7640HS, NVIDIA RTX 4060 Laptop GPU з 8188 MiB VRAM. Перед роботою nvidia-smi показав 7885 MiB вільної відеопам’яті. Win32_OperatingSystem показав 28 377 980 KiB вільної та 41 093 492 KiB загальної фізичної пам’яті. Драйвер NVIDIA 581.86.

Реально перевірені версії CLI — Ollama 0.40.17 та uv 0.13.6. Python середовища курсу 3.13.18.

Чат працює локально в Ollama з qwen3:0.6b, digest 7df6b6e09427. Embeddings — bge-m3:latest, digest 790764642607, завантажений 24 листопада. Реальний ollama ps показав чат із CONTEXT=16384, 100% GPU, 2.4 GB і embedder із CONTEXT=8192, 100% GPU, 689 MB. Це розміри резидентних моделей за Ollama. Версії Python та пакетів фіксує uv.lock.

Пакети навчання є необов’язковою групою tune. Для NVIDIA створено окреме ігнороване середовище models/lab3/tune-env з torch 2.10.0+cu128, CUDA 12.8, peft 0.22.0, transformers 5.24.0. Воно перевірило cuda.is_available()=True. Звичайне середовище uv використовує загальний lock і працює без груп tune/imagegen.
