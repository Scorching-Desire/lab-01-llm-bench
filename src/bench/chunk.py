"""Deterministic paragraph-aware character windows preserving source offsets."""

CHUNK_CHARS = 1100
OVERLAP = 180


def split_text(text, size=CHUNK_CHARS, overlap=OVERLAP):
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("require size > overlap >= 0")
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary + 2
        yield {"text": text[start:end], "start": start, "end": end}
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
