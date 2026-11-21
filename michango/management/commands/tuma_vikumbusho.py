from django.core.management.base import BaseCommand

from michango.huduma import tuma_vikumbusho
from michango.models import Harusi


class Command(BaseCommand):
    help = "Tuma vikumbusho vya mchango WhatsApp. Endesha mara 2 kwa siku, mfano saa 3 asubuhi na saa 12 jioni."

    def handle(self, *args, **opts):
        for h in Harusi.objects.all():
            r = tuma_vikumbusho(h)
            if r.sababu:
                self.stdout.write(f"{h}: {r.sababu}")
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"{h}: vimetumwa {r.vimetumwa}, vimerukwa {r.vimerukwa}, vimeshindwa {r.vimeshindwa}")
                )
            for k in r.makosa[:20]:
                self.stderr.write(f"  {k}")
