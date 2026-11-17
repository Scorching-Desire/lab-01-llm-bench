"""Оцінювання: нормалізація, інтервал Вілсона, розбір відповіді й перевірка правильності."""
import json
import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def norm(s: str) -> str:
    """NFC, апострофи ’ і ʼ → ', стискання пробілів, casefold."""
    s = unicodedata.normalize("NFC", s).replace("’", "'").replace("ʼ", "'")
    return " ".join(s.split()).casefold()


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% інтервал Вілсона для частки k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, center - half), min(1.0, center + half))




LABELS = ("ремонт", "доступ", "оплата", "інше")

MONTHS_UK = ("січня", "лютого", "березня", "квітня", "травня", "червня",
             "липня", "серпня", "вересня", "жовтня", "листопада", "грудня")


def norm_number(value):
    text = re.sub(r"\s+", "", str(value).casefold()).removesuffix("грн").replace(",", ".")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def norm_date(value):
    text = norm(str(value))
    for style in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, style).date()
        except ValueError:
            continue
    match = re.fullmatch(r"(\d{1,2}) ([а-яіїєґ]+) (\d{4})(?: р\.?)?", text)
    if match and match[2] in MONTHS_UK:
        try:
            return date(int(match[3]), MONTHS_UK.index(match[2]) + 1, int(match[1]))
        except ValueError:
            return None
    return None


def norm_list(values):
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        return None
    return tuple(sorted(norm(item) for item in values))


def norm_text(value):
    return norm(value) if isinstance(value, str) else None


FIELD_RULES = dict(doc_no=norm_text, total=norm_number, issued_on=norm_date,
                   items=norm_list, note=norm_text, label=norm_text)


def compare_field(name, expected, got):
    empty = (None, "", [])
    if expected in empty:
        return "empty_ok" if got in empty else "spurious"
    if got in empty:
        return "missing"
    rule = FIELD_RULES[name]
    normalized = rule(expected)
    return "ok" if normalized is not None and normalized == rule(got) else "wrong"


def clean(text: str) -> str:
    """Прибирає блоки <think>…</think> і огорожу ```json … ```."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S)
    return fence.group(1) if fence else text


def parse_output(text: str) -> object | None:
    """Мітка з відповіді: JSON {"label": …}, рівно одна мітка **жирним** або рівно одна мітка в тексті; інакше None."""
    body = clean(text)
    try:
        data = json.loads(body)
        if isinstance(data, dict) and isinstance(data.get("label"), str):
            return next((label for label in LABELS if norm(label) == norm(data["label"])), None)
    except json.JSONDecodeError:
        pass
    for pattern in (r"\*\*{}\*\*", r"(?<!\w){}(?!\w)"):  # багатослівна відповідь: спершу виділена мітка
        found = [label for label in LABELS if re.search(pattern.format(re.escape(label)), norm(body))]
        if found:
            return found[0] if len(found) == 1 else None
    return None


def is_correct(expected, parsed_or_text) -> bool:
    if isinstance(parsed_or_text, dict):
        got = parsed_or_text.get("label")
    elif isinstance(parsed_or_text, str):
        got = parse_output(parsed_or_text)
    else:
        got = None
    return isinstance(got, str) and norm(got) == norm(str(expected))
