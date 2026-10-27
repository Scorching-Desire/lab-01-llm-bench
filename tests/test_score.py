import pytest

from bench.score import is_correct, norm, parse_output, wilson_ci


def test_norm_apostrophes_spaces_case():
    assert norm("  Кур’єр   ПРИЇХАВ ") == norm("кур'єр приїхав") == "кур'єр приїхав"
    assert norm("пʼять") == "п'ять"


def test_norm_nfc():
    decomposed = "\u0438\u0306"  # «и» + комбінована бреве
    assert norm(decomposed) == "й"


def test_wilson_zero_n():
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_known_value():
    low, high = wilson_ci(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)


def test_wilson_bounds():
    assert wilson_ci(10, 10)[1] == 1.0
    assert wilson_ci(0, 10)[0] == 0.0


@pytest.mark.parametrize("text, label", [  # ілюстрація: підставте мітки своєї задачі
    ('{"label": "ремонт"}', "ремонт"),
    ('```json\n{"label": "доступ"}\n```', "доступ"),
    ("<think>може, ремонт?</think>Доступ", "доступ"),
    ("Відповідь: інше.", "інше"),
    ("Це **інше**: не ремонт і не доступ.", "інше"),
    ("Це не ремонт, а доступ", None),  # дві мітки — неоднозначно
    ("не знаю", None),
])
def test_parse_output(text, label):
    assert parse_output(text) == label


def test_is_correct():
    assert is_correct("ремонт", {"label": "Ремонт"})
    assert is_correct("інше", '{"label": "  Інше "}')
    assert not is_correct("ремонт", {"label": "доступ"})
    assert not is_correct("ремонт", None)