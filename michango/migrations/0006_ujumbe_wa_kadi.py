"""Ujumbe wa kadi ulioombwa na familia, na kuandika upya kadi zilizoko kwenye foleni."""
from django.db import migrations

UJUMBE_WA_KADI = """HABARI ZA LEO, {JINA}!

Tunayo furaha kukujulisha kuhusu maandalizi ya harusi ya ndugu yetu {bwana_harusi}. Tunakuomba uwe sehemu ya kufanikisha siku hii muhimu kwa kutoa mchango wako.

Hii ndiyo kadi yako ya mchango.

Tunaomba mchango wako ufike kabla ya tarehe {tarehe}.

NAMBA ZA MALIPO

📱 M-PESA
Namba: 0767753553
Jina: Richard Ngelula

📱 AIRTEL MONEY
Namba: 0681965636
Jina: Richard Ngelula

Tunathamini sana upendo, ushirikiano na mchango wako katika kufanikisha tukio hili muhimu.

ASANTE SANA KWA KUWA SEHEMU YA FURAHA YETU!"""


def jaza(harusi, mgeni):
    return (
        UJUMBE_WA_KADI.replace("{JINA}", mgeni.jina.upper())
        .replace("{bwana_harusi}", harusi.mwenye_harusi)
        .replace("{tarehe}", harusi.tarehe_mwisho.strftime("%d.%m.%Y"))
    )


def weka(apps, schema_editor):
    Harusi = apps.get_model("michango", "Harusi")
    Ujumbe = apps.get_model("michango", "Ujumbe")
    for h in Harusi.objects.all():
        h.ujumbe_kadi = UJUMBE_WA_KADI
        h.save(update_fields=["ujumbe_kadi"])
        for u in Ujumbe.objects.filter(mgeni__harusi=h, aina="kadi", hali="kwenye_foleni").select_related("mgeni"):
            u.maandishi = jaza(h, u.mgeni)
            u.save(update_fields=["maandishi"])


class Migration(migrations.Migration):
    dependencies = [("michango", "0005_jaribio_la_haraka")]
    operations = [migrations.RunPython(weka, migrations.RunPython.noop)]
