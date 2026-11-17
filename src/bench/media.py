"""Медіа Лабораторної 2 (крок 01): межі, рендер, деградація, частини запиту.

Збірка набору:
  uv run python -m bench.media --data data/golden.jsonl --tags q15,injection
      --channels text,clean --font data/lab2/fonts/<шрифт>.ttf --out data/lab2/docs.jsonl
"""
import argparse
import base64
import json
import mimetypes
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from bench import data

MAX_BYTES = 2 * 1024 * 1024          # 2 МБ на файл
MAX_SIDE = 1280                      # довга сторона; щаблини стелі — 1024, далі 768
MAX_DIR_BYTES = 40 * 1024 * 1024     # 40 МБ на data/lab2/media/
PAGE = (1240, 1754)                  # A4 при 150 dpi
OK_MIME = ("image/png", "image/jpeg", "image/webp")


class MediaError(ValueError):
    """Вхід не придатний: завеликий файл, невідомий тип, зламане зображення."""


def save(img: Image.Image, out: str, max_side: int = MAX_SIDE, **opts) -> str:
    """Довга сторона ≤ max_side, нове зображення без метаданих, перевірка межі розміру."""
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    clean = Image.new("RGB", img.size, "white")   # info порожній → EXIF і GPS не переносяться
    clean.paste(img)
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    clean.save(p, **opts)
    if p.stat().st_size > MAX_BYTES:
        raise MediaError(f"{p}: {p.stat().st_size} Б > {MAX_BYTES} Б")
    return p.as_posix()


def render(text: str, font_path: str, out: str, size: int = 26, max_side: int = MAX_SIDE, background=None) -> str:
    """Канал clean: чистий рендер тексту шрифтом із data/lab2/fonts/."""
    font = ImageFont.truetype(font_path, size)    # OSError, якщо шрифту немає — це навмисно
    img = Image.new("RGB", PAGE, "white")
    if background is not None:
        img = Image.blend(img, background.convert("RGB").resize(PAGE), 0.28)
    draw, y = ImageDraw.Draw(img), 70
    for line in [line for block in text.split("\n") for line in (textwrap.wrap(block, 64) or [""])]:
        draw.text((70, y), line, fill="black", font=font)
        y += int(size * 1.5)
    return save(img, out, max_side)


def degrade(src: str, out: str, angle: float = 1.5, sigma: int = 14,
            quality: int = 55, max_side: int = MAX_SIDE) -> str:
    """Канал scan: нахил, шум, втрати JPEG. Ці три числа записуються в docs/lab2/data.md."""
    with Image.open(src) as f:
        img = f.convert("RGB").rotate(angle, fillcolor="white")
    rng = random.Random(20261117)
    pixels = bytes(max(0, min(255, round(rng.gauss(128, sigma)))) for _ in range(img.width * img.height))
    noise = Image.frombytes("L", img.size, pixels).convert("RGB")
    img = ImageChops.add(img, noise, scale=1.0, offset=-128)
    return save(img, out, max_side, quality=quality)


def rasterize(pdf_path: str, out_dir: str, dpi: int = 150, max_side: int = MAX_SIDE) -> list[str]:
    """PDF → PNG посторінково: локальні рушії приймають зображення, а не PDF."""
    import pypdfium2 as pdfium
    stem = Path(pdf_path).stem
    with pdfium.PdfDocument(pdf_path) as pdf:
        return [save(page.render(scale=dpi / 72).to_pil(), f"{out_dir}/{stem}.p{n}.png", max_side)
                for n, page in enumerate(pdf, start=1)]


def encode(path: str) -> tuple[str, bytes]:
    """(mime, сирі байти) з перевіркою межі — спільний вхід для обох форм API."""
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise MediaError(f"{path}: {len(raw)} Б > {MAX_BYTES} Б")
    mime = mimetypes.guess_type(path)[0]
    if mime not in OK_MIME:
        raise MediaError(f"{path}: тип {mime!r} не з {OK_MIME}")
    try:
        with Image.open(Path(path)) as image:
            if Image.MIME.get(image.format) != mime or max(image.size) > MAX_SIDE:
                raise MediaError(f"{path}: incorrect MIME or image dimensions")
            image.verify()
    except OSError as exc:
        raise MediaError(f"{path}: invalid image") from exc
    return mime, raw


def part(path: str, api: str, url_as_object: bool = True):
    """Частина запиту: gemini_native — сирі байти (base64 робить SDK); openai_chat — data-URI."""
    mime, raw = encode(path)
    if api == "gemini_native":
        from google.genai import types
        return types.Part.from_bytes(data=raw, mime_type=mime)
    url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    return {"type": "image_url", "image_url": {"url": url} if url_as_object else url}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/golden.jsonl")
    ap.add_argument("--tags", default="q15,injection", help="рядки test із будь-яким із цих тегів")
    ap.add_argument("--channels", default="text,clean")
    ap.add_argument("--font", required=True)
    ap.add_argument("--label-field", default="label", help="поле вашої схеми, у яке йде мітка Л1")
    ap.add_argument("--max-side", type=int, default=MAX_SIDE)
    ap.add_argument("--out", default="data/lab2/docs.jsonl")
    a = ap.parse_args()
    wanted, media_dir, rows = set(a.tags.split(",")), "data/lab2/media", []
    for ex in data.load_jsonl(a.data):
        if ex.split != "test" or not wanted & set(ex.tags):
            continue
        # clean рендериться завжди: канал scan робиться з нього
        clean = render(ex.input, a.font, f"{media_dir}/{ex.id}.clean.png", max_side=a.max_side)
        exp = ex.expected if isinstance(ex.expected, dict) else {a.label_field: ex.expected}
        for ch in a.channels.split(","):
            f = None if ch == "text" else (clean if ch == "clean" else degrade(
                clean, f"{media_dir}/{ex.id}.scan.jpg", max_side=a.max_side))
            rows.append({"id": f"{ex.id}.{ch}", "src_id": ex.id, "channel": ch, "input": ex.input,
                         "input_file": f, "input_sha256": data.sha256_file(f) if f else None,
                         "expected": exp, "split": ex.split, "tags": ex.tags})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as out:
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{a.out}: {len(rows)} рядків · канали {a.channels} · довга сторона {a.max_side} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
