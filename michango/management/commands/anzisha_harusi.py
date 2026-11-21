from datetime import date

from django.core.management.base import BaseCommand

from michango.anzisha import anzisha_harusi
from michango.models import Harusi


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
        h = anzisha_harusi(
            jina=o["jina"],
            mwenye_harusi=o["mwenye_harusi"],
            familia=o["familia"],
            tarehe_mwisho=date.fromisoformat(o["tarehe_mwisho"]),
            malipo=o["malipo"] or "Wasiliana na familia kwa maelekezo ya malipo",
        )
        self.stdout.write(self.style.SUCCESS(f"Harusi '{h}' imeanzishwa."))
        if not o["malipo"]:
            self.stdout.write(self.style.WARNING("Kumbuka kuweka maelekezo ya malipo kwenye /admin/ kabla ya kutuma ujumbe."))
