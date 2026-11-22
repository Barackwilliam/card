"""Ujumbe wa kikumbusho kwa wenye salio la ahadi, na namba mbili za malipo, kama ilivyoombwa na familia.

Vikumbusho vilivyoko kwenye foleni kwa wenye salio vinaandikwa upya.
"""
import re

from django.db import migrations
from django.db.models import Sum

UJUMBE_WA_SALIO = """HABARI YAKO {JINA}!

Tunapenda kukushukuru kwa mchango wako wa TSh {ametoa} kwa ajili ya harusi ya ndugu yetu {bwana_harusi}.

Tunapenda pia kukukumbusha kuwa salio la ahadi yako ni TSh {salio}, ambalo tunaomba likamilishwe kabla ya tarehe {tarehe}.

NAMBA ZA MALIPO:

{malipo}

Tunathamini sana moyo wako wa kujitoa, upendo na ushirikiano wako katika kufanikisha harusi hii.

Asante sana, Mungu akubariki!"""
MALIPO = """📱 M-PESA
Namba: 0767753553
Jina: Richard Ngelula

📱 AIRTEL MONEY
Namba: 0681965636
Jina: Richard Ngelula"""
ACHA = "(Jibu ACHA kama hutaki kupokea vikumbusho.)"


def jaza(h, mgeni, ametoa):
    t = (
        UJUMBE_WA_SALIO.replace("{JINA}", mgeni.jina.upper())
        .replace("{ametoa}", f"{ametoa:,}")
        .replace("{salio}", f"{max((mgeni.ahadi or 0) - ametoa, 0):,}")
        .replace("{bwana_harusi}", h.mwenye_harusi)
        .replace("{tarehe}", h.tarehe_mwisho.strftime("%d.%m.%Y"))
        .replace("{malipo}", h.maelekezo_malipo)
    )
    return t if re.search(r"\bacha\b", t, re.IGNORECASE) else t + "\n" + ACHA


def weka(apps, schema_editor):
    Harusi = apps.get_model("michango", "Harusi")
    Ujumbe = apps.get_model("michango", "Ujumbe")
    for h in Harusi.objects.all():
        h.ujumbe_salio = UJUMBE_WA_SALIO
        h.maelekezo_malipo = MALIPO
        h.save(update_fields=["ujumbe_salio", "maelekezo_malipo"])
        foleni = Ujumbe.objects.filter(mgeni__harusi=h, aina="kikumbusho", hali="kwenye_foleni").select_related("mgeni")
        for u in foleni:
            ametoa = u.mgeni.michango.aggregate(s=Sum("kiasi"))["s"] or 0
            if ametoa and u.mgeni.ahadi and u.mgeni.ahadi > ametoa:
                u.maandishi = jaza(h, u.mgeni, ametoa)
                u.save(update_fields=["maandishi"])


class Migration(migrations.Migration):
    dependencies = [("michango", "0008_malipo_mistari")]
    operations = [migrations.RunPython(weka, migrations.RunPython.noop)]
