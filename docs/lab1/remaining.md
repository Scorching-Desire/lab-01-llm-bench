# Що відкладено й як завершити

Користувач відновив дозвіл на Gemini 2026-10-27. Ключ і доступність gemini-3.8-flash перевірено; реальні dev-проби розпочато. Перший OpenAI-сумісний виклик правильний, але затримка 145955 мс. Продовження матриці залежить від фактичних відповідей і квоти, а не від попередньої заборони.

Gemini-матриця для продовження наведена нижче (в межах квоти; `--resume` обов’язковий). Ці команди зараз **не виконувались**:

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
- Пройти 4×5 чат-порівняння за chat-comparison.md; перевірити privacy settings, зберегти дослівні перші відповіді й скриншоти без персональних даних. Докладний порядок — chat-guide.md; готові промпти — chat/prompts/.
- Особисто пройти усний захист без ШІ. Минулі щотижневі знімки SHA не відтворюються новими комітами.

Не позначати ці вимоги виконаними лише тому, що код або локальні тести зелені.
