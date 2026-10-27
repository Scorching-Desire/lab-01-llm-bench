"""Оцінювання: нормалізація, інтервал Вілсона, розбір відповіді й перевірка правильності."""
import json
import math
import re
import unicodedata


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
