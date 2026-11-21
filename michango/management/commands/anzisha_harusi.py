from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from michango.models import Harusi

KADI_YA_BLUU = Path(settings.BASE_DIR) / "templates" / "bluu.jpg"


class Command(BaseCommand):
    help = "Anzisha harusi ya kwanza ukitumia kadi ya bluu iliyopo kwenye repo (unaweza kubadilisha kila kitu baadaye kwenye admin)."

    def add_arguments(self, parser):
        parser.add_argument("--jina", default="Harusi ya Richard Ngelula")
        parser.add_argument("--mwenye-harusi", default="Richard Ngelula")
        parser.add_argument("--familia", default="Familia ya Bw. & Bi. Michael Mchome wa Korogwe")
        parser.add_argument("--tarehe-mwisho", default="2026-11-30")
        parser.add_argument("--malipo", default="", help="Mfano: M-Pesa 0754 000 000 (Michael Mchome)")

    def handle(self, *args, **o):
        if Harusi.objects.exists():
            self.stdout.write("Tayari kuna harusi. Ibadilishe kwenye /admin/.")
            return
        h = Harusi(
            jina=o["jina"],
            mwenye_harusi=o["mwenye_harusi"],
            familia=o["familia"],
            tarehe_mwisho=date.fromisoformat(o["tarehe_mwisho"]),
            maelekezo_malipo=o["malipo"] or "Wasiliana na familia kwa maelekezo ya malipo",
        )
        with KADI_YA_BLUU.open("rb") as f:
            h.kadi_template.save("kadi-bluu.jpg", File(f), save=False)
        h.save()
        self.stdout.write(self.style.SUCCESS(f"Harusi '{h}' imeanzishwa."))
        if not o["malipo"]:
            self.stdout.write(self.style.WARNING("Kumbuka kuweka maelekezo ya malipo kwenye /admin/ kabla ya kutuma ujumbe."))
