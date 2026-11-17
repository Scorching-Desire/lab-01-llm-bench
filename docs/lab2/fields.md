# Крок 04 · Точність за полями

Точний збіг документа вимагає ok або empty_ok на всіх шести полях. Наперед закомічені правила у f3233bb. Модель не отримує expected. A має інструкцію JSON у запиті, B додає нативну JSON Schema. Поле note оцінюється окремо за точністю та повнотою правильних непорожніх значень.

<!-- report:begin fields -->
| Прогін | Поле | n | Частка і 95% ДІ | Precision | Recall |
| --- | --- | --- | --- | --- | --- |
| 04-fields-A-local-vision-extract.jsonl | doc_no | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision-extract.jsonl | total | 22 | 10/22 [0.27; 0.65] | — | — |
| 04-fields-A-local-vision-extract.jsonl | issued_on | 22 | 14/22 [0.43; 0.80] | — | — |
| 04-fields-A-local-vision-extract.jsonl | items | 22 | 11/22 [0.31; 0.69] | — | — |
| 04-fields-A-local-vision-extract.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-A-local-vision-extract.jsonl | label | 22 | 13/22 [0.39; 0.77] | — | — |
| 04-fields-A-local-vision-extract.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision-extract.jsonl | валідно, але хибно | 22 | 22/22 [0.85; 1.00] | — | — |
| 04-fields-A-local-vision.jsonl | doc_no | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | total | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | issued_on | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | items | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-A-local-vision.jsonl | label | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-A-local-vision.jsonl | валідно, але хибно | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | doc_no | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | total | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | issued_on | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | items | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | note | 15 | 15/15 [0.80; 1.00] | 9/9 [0.70; 1.00] | 9/9 [0.70; 1.00] |
| 04-fields-B-gemini-lite-native.jsonl | label | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | точний збіг документа | 15 | 15/15 [0.80; 1.00] | — | — |
| 04-fields-B-gemini-lite-native.jsonl | валідно, але хибно | 15 | 0/15 [0.00; 0.20] | — | — |
| 04-fields-B-local-vision-extract.jsonl | doc_no | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision-extract.jsonl | total | 22 | 10/22 [0.27; 0.65] | — | — |
| 04-fields-B-local-vision-extract.jsonl | issued_on | 22 | 14/22 [0.43; 0.80] | — | — |
| 04-fields-B-local-vision-extract.jsonl | items | 22 | 11/22 [0.31; 0.69] | — | — |
| 04-fields-B-local-vision-extract.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-B-local-vision-extract.jsonl | label | 22 | 13/22 [0.39; 0.77] | — | — |
| 04-fields-B-local-vision-extract.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision-extract.jsonl | валідно, але хибно | 22 | 22/22 [0.85; 1.00] | — | — |
| 04-fields-B-local-vision.jsonl | doc_no | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | total | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | issued_on | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | items | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-B-local-vision.jsonl | label | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-B-local-vision.jsonl | валідно, але хибно | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | doc_no | 22 | 21/22 [0.78; 0.99] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | total | 22 | 11/22 [0.31; 0.69] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | issued_on | 22 | 13/22 [0.39; 0.77] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | items | 22 | 10/22 [0.27; 0.65] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-v2-A-local-vision-extract.jsonl | label | 22 | 12/22 [0.35; 0.73] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-v2-A-local-vision-extract.jsonl | валідно, але хибно | 22 | 21/22 [0.78; 0.99] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | doc_no | 22 | 21/22 [0.78; 0.99] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | total | 22 | 11/22 [0.31; 0.69] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | issued_on | 22 | 13/22 [0.39; 0.77] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | items | 22 | 10/22 [0.27; 0.65] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | note | 22 | 11/22 [0.31; 0.69] | 0/0 — | 0/11 [0.00; 0.26] |
| 04-fields-v2-B-local-vision-extract.jsonl | label | 22 | 12/22 [0.35; 0.73] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | точний збіг документа | 22 | 0/22 [0.00; 0.15] | — | — |
| 04-fields-v2-B-local-vision-extract.jsonl | валідно, але хибно | 22 | 21/22 [0.78; 0.99] | — | — |

| Прогін | n | Валідні | Медіана мс | $/документ |
| --- | --- | --- | --- | --- |
| 04-fields-A-local-vision-extract.jsonl | 22 | 22 | 542.5 | $0.000000 |
| 04-fields-A-local-vision.jsonl | 22 | 0 | 3285.5 | $0.000000 |
| 04-fields-B-gemini-lite-native.jsonl | 15 | 15 | 4909 | $0.000645 |
| 04-fields-B-local-vision-extract.jsonl | 22 | 22 | 534.0 | $0.000000 |
| 04-fields-B-local-vision.jsonl | 22 | 0 | 3160.5 | $0.000000 |
| 04-fields-v2-A-local-vision-extract.jsonl | 22 | 21 | 1052.5 | $0.000000 |
| 04-fields-v2-B-local-vision-extract.jsonl | 22 | 21 | 620.5 | $0.000000 |
<!-- report:end -->

Початковий Bonsai мав thinking за замовчуванням і ліміт 512. В A та B усі 44 рядки завершилися length без JSON. Це збережені виміри. Окремий alias local-vision-extract закомічено до нових вимірів із reasoning_effort=none і 1536 токенами. V1 після цієї зміни повернув 22/22 валідних в кожному режимі. A і B мали 0/22 точних збігів через підставлений номер MS-0000. Нативна схема контролює форму цього номера й дозволяє його.

У v2 прибрано буквальний приклад номера. Три dev-кейси дали 3/3 правильних номерів проти 0/3 v1. Наступний контрольний test v2/B дав 21/22 правильних номерів, 11/22 правильних сум і 10/22 правильних списків. Точний збіг документів залишився 0/22. Це діагностична зміна після v1. Повтор використовує ті самі тестові id, тому його висновки потребують окремого незалежного набору.

Gemini native B v1 отримав 15/15 точних збігів на qc. Серед них шість незручних документів. У v2/B Bonsai має 10/22 правильних списків із ДІ [0.27;0.65], а 11/22 правильних сум мають ДІ [0.31;0.69]. Інтервали перетинаються. Щоб мати приблизно ±10 в. п. для частки біля 0.5, потрібно близько 97 незалежних документів за звичайним плановим наближенням.
