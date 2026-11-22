"""Matoleo matatu ya kikumbusho (wasiochangia) yaliyoombwa na familia.

Mfumo unayapokezana kwa bahati nasibu ili wageni wasipokee ujumbe uleule kabisa.
Vikumbusho vilivyoko kwenye foleni kwa wasiochangia vinaandikwa upya.
"""
import re

from django.db import migrations
from django.db.models import Sum

MATOLEO = [
    """HABARI ZA LEO, {JINA}!

Tunakukumbusha kuhusu mchango wa harusi ya ndugu yetu {bwana_harusi}. Tarehe ya mwisho ya kupokea michango ni {tarehe}.

NAMBA ZA MALIPO

📱 M-PESA
Namba: 0767753553
Jina: Richard Ngelula

📱 AIRTEL MONEY
Namba: 0681965636
Jina: Richard Ngelula

Kama umeshachangia, tafadhali puuza ujumbe huu. Asante sana!""",
    """SALAAM {JINA},

Tunakukumbusha maandalizi ya harusi ya {bwana_harusi} yanaendelea vizuri, na mchango wako bado unakaribishwa kwa moyo mkunjufu kabla ya {tarehe}.

Unaweza kutuma kupitia:
📱 M-PESA: 0767753553 (Richard Ngelula)
📱 AIRTEL MONEY: 0681965636 (Richard Ngelula)

Tunathamini sana ushirikiano wako. Mungu akubariki!""",
    """HABARI YAKO, {JINA}!

Siku ya furaha ya {bwana_harusi} inakaribia, na tungependa sana uwe sehemu yake. Tunaomba mchango wako ufike kabla ya tarehe {tarehe}.

NAMBA ZA MALIPO
📱 M-PESA – 0767753553 (Richard Ngelula)
📱 AIRTEL MONEY – 0681965636 (Richard Ngelula)

Kama tayari umechangia, tunakushukuru sana na tafadhali puuza ujumbe huu.

ASANTE KWA UPENDO WAKO!""",
]
ACHA = "(Jibu ACHA kama hutaki kupokea vikumbusho.)"


def jaza(t, harusi, mgeni):
    t = (
        t.replace("{JINA}", mgeni.jina.upper())
        .replace("{jina}", mgeni.jina)
        .replace("{bwana_harusi}", harusi.mwenye_harusi)
        .replace("{tarehe}", harusi.tarehe_mwisho.strftime("%d.%m.%Y"))
    )
    return t if re.search(r"\bacha\b", t, re.IGNORECASE) else t + "\n" + ACHA


def weka(apps, schema_editor):
    Harusi = apps.get_model("michango", "Harusi")
    Ujumbe = apps.get_model("michango", "Ujumbe")
    for h in Harusi.objects.all():
        h.ujumbe_kikumbusho = "\n---\n".join(MATOLEO)
        h.save(update_fields=["ujumbe_kikumbusho"])
        foleni = Ujumbe.objects.filter(mgeni__harusi=h, aina="kikumbusho", hali="kwenye_foleni").select_related("mgeni")
        for u in foleni:
            if u.mgeni.michango.aggregate(s=Sum("kiasi"))["s"]:
                continue  # wenye salio wana ujumbe wao (ujumbe_salio)
            u.maandishi = jaza(MATOLEO[u.pk % len(MATOLEO)], h, u.mgeni)
            u.save(update_fields=["maandishi"])


class Migration(migrations.Migration):
    dependencies = [("michango", "0006_ujumbe_wa_kadi")]
    operations = [migrations.RunPython(weka, migrations.RunPython.noop)]
