# Середовище стенду

- Дата: 2026-10-27
- ОС: Windows-11-10.0.26100-SP0
- Python: 3.13.17
- RAM: 39.2 ГБ
- Локальний рушій: Ollama (http://localhost:11434/v1)
- Модель: qwen3:1.7b
- Контекст: 16384
- SDK: openai 3.39.0 · google-genai 2.33.0 · pydantic 2.14.1 · tiktoken 0.14.0 · python-dotenv 1.2.4

| # | Перевірка | Стан | Деталі |
|---|---|---|---|
| 1 | Python ≥ 3.13 | OK | 3.13.17 |
| 2 | git у PATH | OK | git version 2.55.0.windows.3 |
| 3 | import bench | OK | імпортується |
| 4 | .env існує | OK | поруч із pyproject.toml; шаблон — .env.example |
| 5 | хмарний ключ | OK | GEMINI_API_KEY: задано · OPENROUTER_API_KEY: не задано · OPENROUTER_MODEL: не задано |
| 6 | локальний сервер і модель | OK | Ollama (http://localhost:11434/v1) · qwen3:1.7b: є серед 2 |
| 7 | контекст ≥ 16384 | OK | LOCAL_NUM_CTX=16384 · OLLAMA_CONTEXT_LENGTH=16384 |
| 8 | канарка контексту | — | запустіть з --live |
| 9 | хмарний виклик | — | запустіть з --live |
