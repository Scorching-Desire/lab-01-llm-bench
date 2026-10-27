# Токени, вибірка й міркування

## Токени: множник ua/en
<!-- report:begin tokens -->
_Немає результатів — запустіть прогін._
<!-- report:end -->

Лічильник локальної моделі віднімає prompt_tokens порожнього user-повідомлення; ті самі 10 пар обробляє o200k_base.

## Вибірка
<!-- report:begin sampling -->
_Немає результатів — запустіть прогін._
<!-- report:end -->

Один hard t07; 10 повторів кожної з чотирьох конфігурацій; оцінка за нормалізованими відповідями.

## Міркування
<!-- report:begin reasoning -->
_Немає результатів — запустіть прогін._
<!-- report:end -->

Усі 10 hard test; none проти high; max_tokens=4096; вихідні токени включають міркування.

## Параметри, які модель реально приймає
| Модель | temperature / seed | Міркування | Підстава |
|---|---|---|---|
| local qwen3:1.7b | Перевіряються 0/1 і 7/відсутній | thinking.values=[false,true]; none/high | Власні рядки sampling/reasoning; local-probe.json |
| local-large qwen3:4b | 0 і seed=7 | none не вимкнув, high явно заданий | Проба на короткому dev-запиті, API show: [true] |
| Gemini | Параметри вибірки не надсилаються | low у реєстрі; live відкладено | Документація; живих свідчень немає |

Джерела (2026-10-27): https://docs.ollama.com/api/openai-compatibility ; https://docs.ollama.com/capabilities/thinking ; https://ai.google.dev/gemini-api/docs/generate-content/thinking .

## Висновок для кроку 03
Основна модель local=qwen3:1.7b, temperature=0, seed=7, reasoning_effort=none, max_tokens=4096, num_ctx=16384. Рішення попереднє до аналізу вимірів; 4B не використовується для none/high через встановлений шаблон.

## Чому це може не відтворитися
Лише 10 мовних пар, один hard у sampling і 10 hard у reasoning. Теги моделі можуть змінитися: digest та контекст збережено в local-probe.json. Міркування обирається на test — це загроза валідності подальшого вибору; потрібен новий незалежний набір.
