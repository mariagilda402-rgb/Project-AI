from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.services.vision import VisionService


def test_png_to_groq_jpeg_data_url_small():
    im = Image.new("RGB", (64, 48), color=(40, 80, 120))
    buf = BytesIO()
    im.save(buf, format="PNG")
    url = VisionService._png_to_groq_jpeg_data_url(buf.getvalue())
    assert url.startswith("data:image/jpeg;base64,")
    assert len(url) < 500_000
