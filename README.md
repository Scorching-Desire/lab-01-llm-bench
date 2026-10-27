# lab-01-llm-bench

Lab 01: відтворюваний LLM bench для маршрутизації звернень навчального makerspace.
[Офіційне завдання](https://koldovsky.github.io/2026-2027-practical-genai-agentic-course/labs/01-llm-bench).
Звіт і чесний статус кожної вимоги: [docs/lab1/README.md](docs/lab1/README.md).

## Відтворення головної таблиці з новими викликами — 3 команди

Передумови: Python 3.13 через uv, запущений Ollama з qwen3:1.7b і контекстом 16384. `LOCAL_MODEL` у локальному .env має відповідати картці. Ключ хмарної моделі для цих команд не потрібен. `python -m uv` використано, щоб команди працювали й без uv.exe у PATH; потрібен установленний пакет uv (`python -m pip install --user uv`).

```powershell
python -m uv sync --locked
python -m uv run python -m bench.run --prompt prompts/v4.md --model local --split test --mode B
python -m uv run python scripts/report.py structured
```

Runner дописує наступні attempt; report бере останню успішну відповідь/id. Для продовження перерваного виміру додайте `--resume` до другої команди. Повторний прогін може змінити числа; хеші й параметри дозволяють пояснити розбіжність.

## Перегенерація закомічених таблиць без моделей

```powershell
python -m uv sync --locked
python -m uv run python scripts/report.py
```

## Перевірки

```powershell
python -m uv run pytest
python -m uv run ruff check .
python -m uv run python scripts/validate_golden.py --tools data/tool_cases.jsonl
python -m uv run python scripts/audit.py
```

`audit.py` повертає ненульовий код за пропущених обов’язкових доказів; це не замінюється зеленими unit tests.
Повна локальна матриця: `python -m uv run python scripts/benchmark.py --stage all`. Крок 02 повторно запускайте окремими скриптами в нові --out; кроки 03–05 підтримують resume.

## Локальний сервер

```powershell
$env:OLLAMA_CONTEXT_LENGTH = '16384'
$env:OLLAMA_NUM_PARALLEL = '1'
ollama serve
```

Тримайте сервер запущеним; змінні повинні бути в середовищі процесу сервера. `python -m uv run python scripts/local_probe.py` перевіряє канарку без хмарних викликів. `check_env.py --live` викликає також хмару, тому під час відкладеного Gemini його не запускаємо.
На машині виконання портативний Ollama встановлено в `%LOCALAPPDATA%/Lab01-Ollama`; бінарні файли й моделі не входять у git.

## Хмара й секрети

Скопіюйте .env.example у .env лише якщо .env ще не існує. Впишіть ключ локально; .env не комітиться. Користувач відновив дозвіл на Gemini: реальні dev-проби успішні, cloud matrix запущено; умови та 503 high-demand описані у docs/lab1/gemini.md. Повнота залежить від audit.md. Команди відновлення — remaining.md.

Для ручного чат-порівняння: [покрокова інструкція](docs/lab1/chat-guide.md), [5 готових промптів](docs/lab1/chat/prompts/).
