# Реальна LoRA та локальний запуск

На цій машині пройдено гілку навчання. NVIDIA RTX 4060 Laptop GPU має capability 8.9. Правильна CUDA-збірка torch 2.10.0+cu128 показала CUDA 12.8 і cuda.is_available()=True. Перед навчанням torch.cuda.mem_get_info() повернув 7441743872 вільних і 8585216000 загальних байтів VRAM. Звичайна CPU-збірка torch у загальному lock не використовувалася для цього висновку.

## Дані та параметри

32 навчальні пари складаються з 8 dev-запитів і 24 описів процедури приймання за корпусом. Походження кожного рядка записане в src_split, src_query_id, src_doc_ids. Test-запити та їхні канонічні expected відсутні в навчальних відповідях. check_leak.py відхиляє збіг test-питання, появу його expected у assistant та близький user-запит із Jaccard ≥0.85 на множинах слів після casefold і вилучення пунктуації. Цей поріг закомічено в 8abb2b8 до запуску навчання. Тести перевіряють витік, дозволений текст корпусу і обидва боки порога.

| Параметр | Виміряне або задане значення |
|---|---|
| Базова модель HF | Qwen/Qwen3-0.6B, Apache-2.0 |
| Базовий тег Ollama | qwen3:0.6b, digest 7df6b6e09427, Q4_K_M |
| LoRA | rank=8, alpha=8, q_proj і v_proj, bias=none |
| Оптимізатор | AdamW, lr=0.0001, clip norm=1.0 |
| Навчання | 32 кроки, seed=20261124, один запис на крок, max_length=1536 |
| Параметри, що навчалися | 1146880 |
| Час кроку | медіана 0.37155 с, сума 34.256 с |
| Повний час, включно з підготовкою | 190.359 с |
| Loss першого / останнього кроку | 1.6391 / 1.7304, різні навчальні записи |
| Файл адаптера | models/lab3/adapter/adapter_model.safetensors |
| Розмір адаптера | 4602248 байтів |
| SHA-256 | 60f6ce52f8289780e39c156ee4e94eda4e4c4ccf5a933db6e7a90e2f8c2579e9 |

Результат і 32 виміряні тривалості збережені у results/lab3/05-training.jsonl. Числа loss різних записів не використовуються як оцінка узагальнення. Прогноз часу на N кроків за медіаною становить N×0.37155 с і є арифметикою.

## Імпорт і відтворення

Прямий імпорт safetensors через поточний Ollama 0.40.17 спершу відхилив --quantize q4_K_M. Наступний імпорт int4 повернув «MLX runtime is not available: failed to load MLX dynamic library». Після цього використано підтримуваний шлях GGUF.

Адаптер злито з HF-базою через merge_and_unload. Конвертер llama.cpp із commit 9578bd3fe48b793cf193c2e4615ec2f24a2ea92a створив GGUF Q8_0. Його імпортовано як lab3-qwen06-lora:latest. model_reported цього тега відрізняється від qwen3:0.6b, adapter_sha256 присутній у кожному рядку лінії. Ваги, GGUF, навчальне середовище та копія llama.cpp розташовані в ігнорованій models/lab3/.

Для повтору навчання на цій Windows-машині створити окреме Python 3.13 середовище, встановити CUDA-збірку torch 2.10.0+cu128 з офіційного індексу PyTorch та peft 0.22.0, transformers 5.24.0, accelerate 1.16.0, sentencepiece 0.2.3. CLI scripts/train_lora.py виконує реальне навчання, scripts/import_lab3_adapter.py — конвертацію й імпорт. Група tune описує залежності, але звичайні тести та звіти їх не потребують. Конвертер перевірено через його --help перед запуском.

Команди з кореня репозиторію для нового середовища та відсутньої копії llama.cpp:

```powershell
python -m uv venv --python 3.13 models/lab3/tune-env
python -m uv pip install --python models/lab3/tune-env/Scripts/python.exe torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128
python -m uv pip install --python models/lab3/tune-env/Scripts/python.exe peft==0.22.0 transformers==5.24.0 accelerate==1.16.0 sentencepiece==0.2.3
git clone https://github.com/ggml-org/llama.cpp.git models/lab3/llama.cpp
git -C models/lab3/llama.cpp checkout 9578bd3fe48b793cf193c2e4615ec2f24a2ea92a
python -m uv pip install --python models/lab3/tune-env/Scripts/python.exe -r models/lab3/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
python -m uv run python scripts/check_leak.py
models/lab3/tune-env/Scripts/python.exe scripts/train_lora.py
models/lab3/tune-env/Scripts/python.exe scripts/import_lab3_adapter.py
models/lab3/tune-env/Scripts/python.exe scripts/import_lab3_base.py
```

Повтор навчання дописує новий запис у 05-training.jsonl і створює новий адаптер. Його SHA потрібно передати в новий файл вимірювання, не змішувати з історичним 04-q8-lora.jsonl. На Linux шлях до Python цього середовища закінчується на `bin/python`.

## Контроль початкової бази

Початкові файли 04-prompting/rag/lora використовували готовий Q4_K_M і адаптований Q8_0. Після виявлення цієї різниці окремий протокол Q8 закомічено в b19b5f6. Скрипт import_lab3_base.py імпортував неадаптований Qwen/Qwen3-0.6B із кешованої ревізії c1899de289a04d12100db370d81485cdf75e47ca тим самим Q8_0 конвертером. Шаблони обох імпортів мають однаковий SHA a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8. Архітектура, квантизація й розміри моделі узгоджені. Це засвідчено в 05-artifacts.jsonl. Звітні 04-q8-* містять нові прогони всіх трьох ліній за цим контролем.

Залишаються обмеження вибірки й навчання. 32 пари охоплюють 8 відповідей dev і 24 процедурні абзаци. Вони не навчають усі факти 24 повних регламентів. Висновок стосується цього малого режиму LoRA. Контроль квантизації вибрано після первинних тестів за технічною причиною, що розкрито в protocol.md. Повтор використовує ті самі test-питання, тому потрібна незалежна перевірка узагальнення.

Першоджерела переглянуто 24 листопада 2026 року — [модель Qwen](https://huggingface.co/Qwen/Qwen3-0.6B), [PEFT LoRA](https://huggingface.co/docs/peft/developer_guides/lora), [імпорт Ollama](https://docs.ollama.com/import).
