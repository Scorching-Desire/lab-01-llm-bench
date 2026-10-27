# Картки моделей

Дата звернення до всіх наведених джерел: 2026-10-27. Дві закриті моделі та дві з відкритими вагами.

## local · qwen3:1.7b
- Провайдер ваг: Qwen/Alibaba; рушій Ollama 0.40.11. Роль: основна локальна модель з перемиканням міркування.
- Відкриті ваги, Apache-2.0. Вхід/вихід: текст/текст. Контекст ваг: 32768; фактично стенд: 16384.
- API: openai_chat; temperature=0, seed=7, reasoning_effort=none, max_tokens=512. Tools/schema/thinking підтримуються.
- price_in=0, price_out=0 USD/1M; без API-плати (електроенергія і придбання GPU не оцінювались). Дані локальні.
- Відсічення знань і дата зняття: не опубліковано у використаній картці.
- Джерела: https://huggingface.co/Qwen/Qwen3-1.7B ; https://ollama.com/library/qwen3:1.7b ; https://docs.ollama.com/api/openai-compatibility

## local-large · qwen3:4b
- Провайдер ваг Qwen/Alibaba; Ollama. Роль: більша локальна модель для порівняння.
- Відкриті ваги, Apache-2.0. Текст → текст. Upstream: 32768 нативно / 131072 із YaRN; фактичний контекст стенду 16384.
- price_in=0, price_out=0 USD/1M; джерело ціни реєстру https://ollama.com/library/qwen3 (2026-10-27). Дані локальні.
- У встановленого тега thinking.values=[true], шаблон завжди відкриває think. Проба none не вимкнула міркування. Тому high явно заданий; це інша експериментальна умова, а не порівняння лише розмірів ваг.
- Відсічення знань і дата зняття: не опубліковано у використаній картці.
- Джерела: https://huggingface.co/Qwen/Qwen3-4B ; https://ollama.com/library/qwen3:4b ; model-snapshots.json (метадані локального тега).
- Розбіжність із методичкою: у ній qwen3:4b рекомендовано для none/high; наш встановлений шаблон не підтримав none. Оригінальний тег користувача не змінювався.

## gemini / gemini-native · gemini-3.8-flash
- Google; закрита модель. Дві форми одного ID: OpenAI-сумісна та generateContent.
- Контекст до 1M, вихід до 64K. Вхід: текст, зображення, аудіо, відео; вихід: текст.
- Ціна реєстру: price_in=0.75, price_out=3.75 USD/1M, price_date=2026-10-27, price_src=https://ai.google.dev/gemini-api/docs/pricing . Це сценарна платна ціна; free tier безкоштовний, запити можуть використовуватися для покращення продуктів.
- З 2027-01-01 ціна 1.50/7.50. `report.py --price gemini=1.50/7.50 --price gemini-native=1.50/7.50` рахує сценарій без API-викликів.
- Knowledge cutoff: березень 2026, у деяких доменах січень 2025; дата зняття в використаній model card не вказана.
- Параметри: low; max_tokens=4096 в обох формах; temperature/top_p/seed не надсилаються. Після відновлення дозволу обидві dev-форми реально повернули правильну відповідь; 146/298 с, native B дав тимчасову 503 і успішний повтор. Повна матриця ще виконується, див. gemini.md.
- Джерела: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash ; https://ai.google.dev/gemini-api/docs/pricing ; https://deepmind.google/models/model-cards/gemini-3-8-flash/ ; https://ai.google.dev/gemini-api/docs/generate-content/thinking
- `latest-model` уже веде до Gemini 4 Argon; ID лабораторної свідомо зафіксований, автоматичного переходу немає.

## Claude Sonnet 5.5 · claude-sonnet-5-5
- Anthropic; закриті ваги. Довідкова картка, модель не викликалась і не має псевдоніма для вимірів.
- Контекст 1M; max output 128K. Вхід текст/зображення, вихід текст.
- Стандартна ціна 2/10 USD за 1M input/output. Cutoff червень 2026; retirement не раніше 2027-09-28.
- Джерело: https://platform.claude.com/docs/en/models/overview (2026-10-27).

## openrouter · конфігураційний псевдонім
Не активований; OPENROUTER_MODEL має бути заданий користувачем, ID/ліцензія/контекст до вибору невідомі. Не включений у результати чи рекомендації. Для :free реєстр має 0/0; перед платною моделлю треба оновити картку й ціни. `require_parameters=True` обов’язковий.
Джерела: https://openrouter.ai/docs/guides/routing/provider-selection ; https://openrouter.ai/docs/api_reference/limits .

## local-fast · qwen3:0.6b
- Qwen/Alibaba; відкриті ваги, Apache-2.0. Вхід/вихід текст/текст. Контекст upstream 32768, стенд 16384.
- Роль: швидкий другий локальний comparator. price_in=0, price_out=0 USD/1M; price_date=2026-10-27; price_src=https://ollama.com/library/qwen3 .
- temperature=0, seed=7, reasoning_effort=none, max_tokens=512; tools/schema/thinking за документацією. Відсічення знань і зняття у використаній картці не опубліковано.
- Джерело: https://huggingface.co/Qwen/Qwen3-0.6B (2026-10-27).

## Заміна повільного comparator
У 4B пілоті отримано 11 завершених рядків, медіана 16386.0 мс, максимум 3018 вихідних токенів. Подальші 4B-виклики зупинено через витрати часу; наявні рядки збережені без змін у results/exploratory/03-v0-local-large.jsonl. Вибір 0.6B зроблено за затримкою, а не за точністю; пілот не є повною абляцією й не включений у основну таблицю. Первинні промпти/мітки/гіпотези незмінні.

## gemini-lite / gemini-lite-native · gemini-3.1-flash-lite
- Google; закриті ваги. Дві форми: OpenAI-сумісна і generateContent. Вхід: текст, зображення, відео, аудіо, PDF; вихід: текст. Контекст 1048576, вихід до 65536.
- Structured outputs, function calling і thinking підтримуються. Стенд: low, max_tokens=4096, concurrency=1, max RPM=8; параметри вибірки не задаються.
- Free Tier: вхід/вихід без API-плати; запити можуть використовуватись для покращення продукту. Сценарна стандартна платна ціна реєстру: price_in=0.25, price_out=1.50 USD/1M для тексту; price_date=2026-10-27; price_src=https://ai.google.dev/gemini-api/docs/pricing .
- Квоту слід перевіряти власними запитами; успішна dev-проба не доводить доступність усієї добової матриці. Дату зняття у використаній API-сторінці не вказано; cutoff див. офіційну model card.
- Джерела (2026-10-27): https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite ; https://ai.google.dev/gemini-api/docs/pricing ; https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/ .
- Вибрано до test у cloud-selection.json через quota 20/day і 146–298 с на 3.8. Старі 3.8-виміри збережені окремо, ID у рядках не змінюється. Це зміна кандидата через доступність, а не за точністю на test.
