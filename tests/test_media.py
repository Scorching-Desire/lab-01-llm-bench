import io

import pypdfium2 as pdfium
import pytest
from PIL import Image

from bench import media


def test_rejects_oversized(tmp_path):
    p = tmp_path / "big.png"
    p.write_bytes(b"\x89PNG\r\n" + b"0" * media.MAX_BYTES)
    with pytest.raises(media.MediaError):
        media.encode(str(p))


def test_rasterizes_pdf(tmp_path):
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(595, 842)
    buf = io.BytesIO()
    pdf.save(buf)
    src = tmp_path / "doc.pdf"
    src.write_bytes(buf.getvalue())
    pages = media.rasterize(str(src), str(tmp_path), dpi=72)
    assert len(pages) == 1
    with Image.open(pages[0]) as img:
        assert max(img.size) <= media.MAX_SIDE


def test_strips_exif(tmp_path):
    src, out = tmp_path / "in.jpg", tmp_path / "out.jpg"
    img = Image.new("RGB", (40, 30), "white")
    exif = img.getexif()
    exif[271] = "Camera X"          # Make — щоб було що знімати
    img.save(src, exif=exif)
    with Image.open(src) as f:
        assert dict(f.getexif())    # метадані на вході справді є
        media.save(f, str(out))
    with Image.open(out) as f:
        assert not dict(f.getexif())