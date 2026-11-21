"""Kuanzisha harusi ya kwanza kwa kutumia kadi ya bluu iliyo ndani ya repo."""
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files import File

from .models import Harusi

KADI_YA_BLUU = Path(settings.BASE_DIR) / "templates" / "bluu.jpg"


def anzisha_harusi(*, jina, mwenye_harusi, familia, tarehe_mwisho: date, malipo) -> Harusi:
    h = Harusi(
        jina=jina,
        mwenye_harusi=mwenye_harusi,
        familia=familia,
        tarehe_mwisho=tarehe_mwisho,
        maelekezo_malipo=malipo,
    )
    # Picha inapakiwa kwanza (Supabase); ikishindwa, hakuna harusi nusu inayobaki kwenye database.
    with KADI_YA_BLUU.open("rb") as f:
        h.kadi_template.save("kadi-bluu.jpg", File(f), save=False)
    h.save()
    return h


def mahali_pa_picha() -> str:
    backend = settings.STORAGES["default"]["BACKEND"]
    return "supabase" if backend.endswith("SupabaseStorage") else "folda"
