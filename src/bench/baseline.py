"""Fixed keyword baseline; declared before the first test inference."""
from bench.score import norm

KEYWORDS = {
    "ремонт": ("ремонт", "несправ", "злам", "не працю", "полагод", "скрег", "вібру"),
    "доступ": ("доступ", "перепуст", "картк", "pin", "код вход", "дозвіл", "шафк"),
    "оплата": ("оплат", "рахун", "кошт", "списан", "передоплат", "нарахув", "квитанц", "переплат"),
}


def predict(text):
    text = norm(text)
    for label, stems in KEYWORDS.items():
        if any(stem in text for stem in stems):
            return label
    return "інше"
