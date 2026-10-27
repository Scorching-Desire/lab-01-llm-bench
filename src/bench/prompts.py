"""Промпти: Markdown-файл з рядком «version: …» і розділами «## system» та «## user»."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from bench.data import Example, sha256_file


@dataclass
class Prompt:
    version: str
    sha256: str
    system: str
    user: str


def load_prompt(path: str | Path) -> Prompt:
    """Читає файл (UTF-8): version з рядка «version: vN», тексти розділів «## system» і «## user», sha256 файлу.

    Немає рядка version або одного з розділів — ValueError з поясненням.
    """
    text = Path(path).read_text(encoding="utf-8")
    version = re.search(r"^version:\s*(\S+)\s*$", text, re.M)
    sections = re.search(r"^## system\s*\n(.*?)^## user\s*\n(.*)\Z", text, re.M | re.S)
    if not version or not sections:
        raise ValueError(f"{path}: required version, ## system, ## user")
    if "<<input>>" not in sections[2]:
        raise ValueError(f"{path}: missing <<input>>")
    return Prompt(version[1], sha256_file(path), sections[1].strip(), sections[2].strip())


def format_examples(examples: list[Example]) -> str:
    """Few-shot блок для <<examples>>: лише приклади dev, у тому самому форматі відповіді, що просить промпт."""
    if any(ex.split != "dev" for ex in examples):
        raise ValueError("few-shot examples must be dev")
    return "\n\n".join(f"Вхід: {ex.input}\nВідповідь: " +
                        json.dumps({"label": ex.expected}, ensure_ascii=False) for ex in examples)


def render(prompt: Prompt, example: Example, dev_examples: list[Example]) -> list[dict]:
    """[{"role": "system", …}, {"role": "user", …}] з підставленими <<input>> і <<examples>>.

    Заміна — str.replace, не str.format: у JSON-прикладах є фігурні дужки.
    Якщо шаблон обгортає вхід тегом (<tag><<input>></tag>), закриваючий тег у самому вході
    замініть на &lt;/tag&gt; (без урахування регістру), щоб вхід не міг «вийти» за розмежування.
    """
    value = example.input
    for tag in re.findall(r"<(\w+)>\s*<<input>>\s*</\1>", prompt.user):
        value = re.sub(rf"</{re.escape(tag)}>", f"&lt;/{tag}&gt;", value, flags=re.I)
    # Substitute input last: placeholders inside untrusted input remain literal.
    user = prompt.user.replace("<<examples>>", format_examples(dev_examples)).replace("<<input>>", value)
    return [{"role": "system", "content": prompt.system}, {"role": "user", "content": user}]
