# Перевірка Lab 03

Локальні перевірки виконано 24 листопада 2026 року на Windows / Python 3.13.18. База Lab 02 — 5fd166097772004b0e6b2d2e53378860e08e1595. Сирі виміри збережені комітом 14ba490035ce292aaabadd8a0d2e832fa940235e.

## Автоматичні перевірки

| Команда | Фактичний результат |
|---|---|
| `python -m uv sync --locked` | Успіх без torch/peft та без зміни uv.lock |
| `python -m uv run pytest` | 76 passed, 2 skipped із 78; imagegen і tune необов’язкові |
| `python -m uv sync --locked --extra tune`, `python -m uv run --extra tune pytest` | 77 passed, 1 skipped; перевірено справжню конфігурацію PEFT |
| `python -m uv run ruff check .` | All checks passed |
| `python -m uv run python -m compileall -q src scripts` | Код 0 |
| `python -m uv build` | Побудовано sdist і wheel, вони не комітяться |
| `python -m uv run python scripts/validate_corpus.py --attacks data/lab3/attacks.jsonl` | 24 документи, 216 фрагментів, 240783 байти, 8 dev / 25 test, OK |
| `python -m uv run python scripts/check_leak.py` | 0 leaks, Jaccard threshold=0.85 |
| `python -m uv run python scripts/audit_lab3.py` | 200 frozen test rows, 20 attacks, 32 real training steps |
| `python -m uv run python scripts/audit_lab2.py` | 334 benchmark rows, 90 step-02 cells, 3 generated pairs |
| validate_golden.py та чотири validate_docs.py для наборів Lab 02 | Усі OK |
| `python -m uv run python scripts/audit.py` | Технічні докази Lab 01 OK; реєстрація, знімки й особистий захист залишаються MISSING |

Тест check_leak перевіряє вихід CLI 1 зі згадкою test-id на штучному витоку та вихід 0 на дозволеному корпусному записі. Тести індексу й answer використовують fake embedder/chat і працюють без мережі. Живі виклики виконували окремі скрипти, а не pytest.

## Збереження попередньої роботи

Команди порівняння з базою Lab 02 для data/golden.jsonl, data/lab2/synth.jsonl, src/bench/schema_fields.py та попередніх tests/ з `--diff-filter=MDR` завершилися з кодом 0. Нові тести додано окремо. Відтворення всіх звітних блоків не змінює docs/lab1 і docs/lab2. Результати записували тільки скрипти; історичні вимірювання збережено.

Файли секретів не відкривалися. `.env`, `.index/` і `models/lab3/` ігноруються; бінарні ваги та навчальне середовище відсутні серед відстежуваних файлів. Для аудиту адаптера використовуються SHA, байти й метадані у 05-training.jsonl / 05-artifacts.jsonl, а не включення ваг у репозиторій.

## Чистий клон і публікація

Після фіксації звіту виконується окремий локальний клон із повною історією та без .index/. У ньому потрібно виконати дві команди розділу Lab 03 кореневого README, потім тести, аудит і повну перегенерацію звітів. Точний перевірений SHA і результат цієї перевірки додаються окремим записом нижче.

Push і CI нового SHA ще не підтверджені: AGENTS.md вимагає окремого явного дозволу на git push. Зелені локальні тести не позначаються як зелений GitHub Actions. Реєстрацію в таблиці групи й захист виконує студент; викладацькі історичні знімки не виготовлялися.
