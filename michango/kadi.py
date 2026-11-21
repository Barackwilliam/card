"""Kutengeneza kadi ya mgeni: kuandika jina lake juu ya picha ya kadi ya harusi."""
import io
import re
import time
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent / "fonts"


def _hex_to_rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def chora_kadi(template: Image.Image, jina: str, *, x, y, ukubwa, upana_max, rangi, fonti) -> Image.Image:
    """Rudisha nakala ya template ikiwa na jina limeandikwa.

    x, y na upana_max ni sehemu ya upana/urefu wa picha (0-1); y ni mstari wa chini
    wa herufi. Ukubwa umepimwa kwa picha yenye upana wa 1024px. Jina refu
    linapunguzwa ukubwa mpaka litoshee upana_max.
    """
    img = template.convert("RGB").copy()
    W, H = img.size
    draw = ImageDraw.Draw(img)
    px = max(int(round(ukubwa * W / 1024)), 8)
    max_w = upana_max * W
    font_path = str(FONTS_DIR / fonti)
    font = ImageFont.truetype(font_path, px)
    while draw.textlength(jina, font=font) > max_w and px > 10:
        px -= 1
        font = ImageFont.truetype(font_path, px)
    draw.text((x * W, y * H), jina, font=font, fill=_hex_to_rgb(rangi), anchor="ms")
    return img


def jina_la_faili(mgeni) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "-", mgeni.jina).strip("-").lower() or "mgeni"
    # muda kwenye jina ili kadi mpya isichanganywe na ya zamani iliyohifadhiwa (cache)
    return f"h{mgeni.harusi_id}/{mgeni.pk}-{safe}-{int(time.time())}.jpg"


def tengeneza_kadi(mgeni, template_img: Image.Image | None = None) -> None:
    """Tengeneza kadi ya mgeni na uihifadhi (Supabase bucket au media/)."""
    h = mgeni.harusi
    if template_img is None:
        with h.kadi_template.open("rb") as f:
            template_img = Image.open(f)
            template_img.load()
    img = chora_kadi(
        template_img,
        mgeni.jina,
        x=h.jina_x,
        y=h.jina_y,
        ukubwa=h.jina_ukubwa,
        upana_max=h.jina_upana_max,
        rangi=h.jina_rangi,
        fonti=h.jina_fonti,
    )
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    if mgeni.kadi:
        mgeni.kadi.delete(save=False)
    mgeni.kadi.save(jina_la_faili(mgeni), ContentFile(buf.getvalue()), save=True)
