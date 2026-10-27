# Що відкладено й як завершити

Gemini не викликається за прямою вказівкою користувача від 2026-10-27. Це не збій ключа. Код нативної та OpenAI-сумісної гілок проходить offline tests; живі хмарні метрики відсутні.

Після окремої вказівки відновити Gemini потрібно виконати матрицю нижче (в межах квоти; `--resume` обов’язковий). Ці команди зараз **не виконувались**:

```powershell
foreach ($v in 'v0','v1','v2','v4') {
  uv run python -m bench.run --prompt "prompts/$v.md" --model gemini --split test --tag q15 --resume
}
foreach ($m in 'A','B') {
  uv run python -m bench.run --prompt prompts/v4.md --model gemini-native --split test --tag q15 --mode $m --resume
}
foreach ($t in 'station_status,booking_status','none') {
  uv run python -m bench.run --prompt prompts/t1.md --model gemini-native --data data/tool_cases.jsonl --split tool --tools $t --resume
}
uv run python scripts/report.py
```

Далі оновити числовий аналіз та аудит, запустити тести й перевірити CI, зробити новий commit/push. Дві локальні моделі не замінюють вимогу двох живих форм API.

Особисті дії студента, які асистент не може засвідчити замість нього:

- Перевірку 33 golden і 8 tool міток студент підтвердив 2026-10-27, змін 0 (annotation-review.json). Подальша зміна expected потребує журналу та нових результатів.
- Підтвердити власну тему та внести її й URL репозиторію у таблицю групи (користувач робить вручну).
- Пройти 4×5 чат-порівняння за chat-comparison.md; перевірити privacy settings, зберегти дослівні перші відповіді й скриншоти без персональних даних. Gemini наразі відкладений також для цього пункту.
- Особисто пройти усний захист без ШІ. Минулі щотижневі знімки SHA не відтворюються новими комітами.

Не позначати ці вимоги виконаними лише тому, що код або локальні тести зелені.
