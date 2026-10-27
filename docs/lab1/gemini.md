# Gemini: початок реальних прогонів

Користувач відновив дозвіл 2026-10-27. Ключ лишається у .env, не в коді й не в git. ID gemini-3.8-flash та незмінні промпти/мітки збережені.

## Dev-перевірка

| API | id | Правильно | Затримка, мс | Сирий файл |
|---|---|---|---|---|
| gemini_native | d01 | True | 297821 | results/dev/gemini-native-smoke.jsonl |
| openai_chat | d01 | True | 145955 | results/dev/gemini-smoke.jsonl |

## Транспорт і умови вимірювання
- Перші відповіді тривали приблизно 146 і 298 секунд; GET моделей через REST та OpenAI SDK водночас працював швидко. Діагностичні native REST/SSE запити не завершилися за 25/20 секунд. Це не виміри якості й не підмішані до test-таблиць.
- Перша test-спроба native B повернула 503 UNAVAILABLE: «This model is currently experiencing high demand». Її не видалено; наступна успішна спроба t01 дописана як attempt=2.
- Хмарна матриця працює з **налаштованою максимальною concurrency=16**, загальний допуск не швидше 6 HTTP-запитів/хв, max_tokens=4096, reasoning/thinking low. Локальні дані лишаються з concurrency=1; пряме порівняння затримок має цю загрозу валідності.
- Усі append/read захищені lock для потоків одного процесу; пропущені до відправлення завдання не отримують вигаданих рядків. Окремі tool-виклики також проходять спільне обмеження RPM.
- Стандартний runner повторює тимчасові 503/timeout до п’яти спроб; вичерпана квота припиняє нові завдання. Серверна помилка, що не зникла після повторів, також зупиняє видачу нових кейсів; уже надіслані завершуються.
- Модель 2.5 Flash не вибиралася замість 3.8: її одинична діагностична POST-перевірка повернула 404. Основні aliases/ID не підмінювались.

## Продовження й перевірка
```powershell
python -m uv run python scripts/cloud_benchmark.py --workers 16 --max-rpm 6
python -m uv run python scripts/report.py
python -m uv run python scripts/audit.py
```
`--resume` виконується диспетчером для кожного id. При відновленні треба лишити ту саму concurrency, інакше потрібні окремі файли для нової експериментальної умови. Повноту визначає audit.py, а не наявність одного успішного запиту.

Стан результатів і кількість доступних test-відповідей див. у згенерованих structured.md / prompts.md / tools.md та audit.md. Наразі матриця ще виконується; її завершення не оголошується наперед.

Джерела (2026-10-27): https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash ; https://ai.google.dev/gemini-api/docs/openai ; https://ai.google.dev/gemini-api/docs/rate-limits .
