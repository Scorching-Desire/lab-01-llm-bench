"""Build a seeded dataset of fictional makerspace receipts."""

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

from bench import data, media, score
from bench.schema_fields import DocFields

SEED = 20261117
FONT = "data/lab2/fonts/NotoSans.ttf"
ROOT = Path("data/lab2")
AWKWARD = ("empty", "twins", "date_format", "long_list", "comma_number", "boundary")
ITEMS = ("Втулка", "Ролик", "Кабель", "Зчитувач", "Фільтр", "Шайба", "Адаптер")


def build(seed):
    rng = random.Random(seed)
    rows = []
    for index in range(30):
        split = "dev" if index < 8 else "test"
        awkward = AWKWARD[index - 8] if 8 <= index < 14 else None
        tags = [awkward] if awkward else []
        if 8 <= index < 23:
            tags.append("qc")
        label = rng.choice(score.LABELS)
        if awkward == "empty":
            label = "ремонт"
        note = "Огляд у навчальній майстерні" if label == "інше" or index % 3 == 0 else None
        if awkward == "empty":
            note = None
        issued = date(2026, 1, 1) + timedelta(days=rng.randrange(300))
        total = 100000 if awkward == "boundary" else rng.randrange(1010, 299999) / 100
        items = rng.sample(ITEMS, 6 if awkward == "long_list" else rng.randrange(1, 4))
        fields = dict(doc_no=f"MS-{1000 + index}", total=total, issued_on=issued.isoformat(),
                      items=items, note=note, label=label)
        DocFields.model_validate(fields)
        date_text = (issued.isoformat(), issued.strftime("%d.%m.%Y"),
                     f"{issued.day} {score.MONTHS_UK[issued.month - 1]} {issued.year} р.")[index % 3]
        if awkward == "date_format":
            date_text = f"{issued.day} {score.MONTHS_UK[issued.month - 1]} {issued.year} р."
        amount = f"{total:,.2f}".replace(",", " ").replace(".", ",") if index % 2 == 0 or awkward == "comma_number" else str(total)
        sections = [f"Номер: {fields['doc_no']}", f"Дата: {date_text}", f"Підсумок: {amount} грн",
                    "Позиції:\n" + "\n".join(f"• {item}" for item in items), f"Маршрут: {label}"]
        if awkward == "twins":
            sections.append(f"Аванс: {total / 2:.2f} грн")
        if note:
            sections.append(f"Примітка: {note}")
        rng.shuffle(sections)
        heading = ("Квитанція makerspace", "Реєстр сервісу makerspace", "Квитанція майстерні")[index % 3]
        case = f"s{index:03}"
        rows.append(dict(id=case, src_id=case, split=split, tags=tags, variant="plain",
                         input=heading + "\n\n" + "\n\n".join(sections), expected=fields))
    return rows


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--compare-values")
    parser.add_argument("--bg", type=int, choices=range(3, 9))
    args = parser.parse_args()
    rows = build(args.seed)
    if args.compare_values:
        old = data.read_rows(args.compare_values)
        fields = [(r["id"], r["split"], r["tags"], r["expected"]) for r in rows]
        prior = [(r["id"], r["split"], r["tags"], r["expected"]) for r in old]
        print(f"{len(rows)} records; values match: {fields == prior}")
        return int(fields != prior)
    images = []
    for index, row in enumerate(rows):
        path = ROOT / "media" / f"{row['id']}.clean.png"
        media.render(row["input"], FONT, str(path), size=(26, 28, 30)[index % 3])
        images.append(dict(row, channel="clean", input_file=path.as_posix(), input_sha256=data.sha256_file(path)))
        row.update(channel="text", input_file=None, input_sha256=None)
    write_jsonl(ROOT / "synth.jsonl", rows)
    write_jsonl(ROOT / "synth-images.jsonl", images)
    if args.bg:
        from bench import image_background as bg

        pipe = bg.load_pipe()
        chosen = random.Random(args.seed).sample(images[8:], args.bg)
        variants, manifest = [], []
        for plain in chosen:
            index = int(plain["id"][1:])
            seed = args.seed + index
            background, seconds = bg.make_background(pipe, seed)
            path = ROOT / "media" / f"{plain['id']}.gen.png"
            media.render(plain["input"], FONT, str(path), size=(26, 28, 30)[index % 3], background=background)
            manifest.append(bg.manifest_row(path, plain["id"], seed, seconds, pipe))
            variants.extend([plain, dict(plain, id=f"{plain['id']}.gen", variant="gen",
                                         input_file=path.as_posix(), input_sha256=data.sha256_file(path))])
            print(f"{plain['id']}: {seconds:.2f} seconds", flush=True)
        write_jsonl(ROOT / "synth-variants.jsonl", variants)
        write_jsonl(ROOT / "generated.jsonl", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
