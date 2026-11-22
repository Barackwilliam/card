"""Huduma kuu: kutuma kadi, vikumbusho na shukrani, na kuhesabu takwimu."""
import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from . import jumbe, whatsapp
from .kadi import tengeneza_kadi
from .models import Harusi, Mchango, Mgeni, Ujumbe

log = logging.getLogger("michango")

# Saa ambazo vikumbusho vinaruhusiwa kutumwa (saa za Tanzania)
SAA_YA_KUANZA = 8
SAA_YA_MWISHO = 20


def tsh(n) -> str:
    return f"{int(n or 0):,}"


def tarehe(d) -> str:
    return d.strftime("%d.%m.%Y")


def url_kamili(file_field) -> str:
    url = file_field.url
    if url.startswith("http"):
        return url
    return settings.SITE_URL + (url if url.startswith("/") else "/" + url)


def _rekodi(mgeni, aina, m: whatsapp.Matokeo) -> Ujumbe:
    hali = "jaribio" if m.jaribio else ("umetumwa" if m.ok else "umeshindwa")
    return Ujumbe.objects.create(mgeni=mgeni, aina=aina, hali=hali, wa_id=m.wa_id, kosa=m.kosa)


UJUMBE_WA_MTUMIAJI = {
    "kadi": "ujumbe_kadi",
    "kikumbusho": "ujumbe_kikumbusho",
    "kikumbusho_salio": "ujumbe_salio",
    "shukrani": "ujumbe_shukrani",
}


def _tuma(mgeni, aina, template, params, picha_url=None, maandishi=None) -> Ujumbe:
    """Tuma kwa njia iliyochaguliwa.

    Baileys: ujumbe unaandaliwa na kuwekwa kwenye foleni; worker anautuma polepole
    na kusasisha hali. Cloud API / majaribio: unatumwa (au kuigizwa) papo hapo.
    """
    if whatsapp.backend() == "baileys":
        return Ujumbe.objects.create(
            mgeni=mgeni, aina=aina, hali="kwenye_foleni", simu=mgeni.simu,
            maandishi=jumbe.tunga(
                template, params,
                maandishi if maandishi is not None else getattr(mgeni.harusi, UJUMBE_WA_MTUMIAJI[template], ""),
            ),
            picha_url=picha_url or "",
        )
    return _rekodi(mgeni, aina, whatsapp.tuma_template(mgeni.simu, template, params, picha_url=picha_url))


def kwa_nini_hawezi_kutumiwa(mgeni) -> str | None:
    if not mgeni.simu:
        return "Hana namba ya simu."
    if mgeni.amejitoa:
        return "Ameomba asitumiwe ujumbe."
    return None


def tuma_kadi(mgeni: Mgeni) -> Ujumbe | None:
    """Tengeneza (kama haipo) na tuma kadi kwa WhatsApp. Hurudisha kumbukumbu ya ujumbe."""
    if kwa_nini_hawezi_kutumiwa(mgeni):
        return None
    iliyopo = mgeni.jumbe.filter(aina="kadi", hali="kwenye_foleni").first()
    if iliyopo:  # usiweke kadi mara mbili kwenye foleni
        return iliyopo
    if not mgeni.kadi:
        tengeneza_kadi(mgeni)
    h = mgeni.harusi
    u = _tuma(
        mgeni, "kadi", "kadi",
        [mgeni.jina, h.mwenye_harusi, tarehe(h.tarehe_mwisho), h.maelekezo_malipo],
        picha_url=url_kamili(mgeni.kadi),
    )
    # Baileys: worker anaweka alama baada ya kutuma kweli.
    if u.hali == "umetumwa":
        mgeni.kadi_imetumwa = timezone.now()
        mgeni.save(update_fields=["kadi_imetumwa"])
    return u


JARIBIO_KWA_SIKU = 3


def majaribio_yaliyobaki(harusi) -> int:
    leo = Ujumbe.objects.filter(mgeni__harusi=harusi, haraka=True, updated__date=timezone.localdate()).count()
    return max(JARIBIO_KWA_SIKU - leo, 0)


def tuma_jaribio_sasa(mgeni: Mgeni) -> tuple[Ujumbe | None, str]:
    """Tuma kadi ya jaribio mara moja (mbele ya foleni, hata usiku). Kwa Baileys tu, mara 3 kwa siku."""
    if whatsapp.backend() != "baileys":
        return None, "Jaribio la haraka linapatikana kwa WhatsApp ya namba ya kawaida tu."
    sababu = kwa_nini_hawezi_kutumiwa(mgeni)
    if sababu:
        return None, sababu
    if majaribio_yaliyobaki(mgeni.harusi) <= 0:
        return None, f"Umefikia majaribio {JARIBIO_KWA_SIKU} ya leo. Jaribu kesho, au subiri saa 2 asubuhi foleni ianze."
    u = tuma_kadi(mgeni)
    if u and u.hali == "kwenye_foleni":
        u.haraka = True
        u.save(update_fields=["haraka", "updated"])
    return u, ""


def tuma_kikumbusho(mgeni: Mgeni, maandishi: str | None = None) -> Ujumbe | None:
    """maandishi: ujumbe ulioandikwa sasa hivi (ukurasa wa Kumbusha); usipotolewa, wa Mipangilio unatumika."""
    if kwa_nini_hawezi_kutumiwa(mgeni):
        return None
    h = mgeni.harusi
    jumla = mgeni.jumla
    if jumla and mgeni.ahadi and mgeni.ahadi > jumla:
        return _tuma(
            mgeni, "kikumbusho", "kikumbusho_salio",
            [mgeni.jina, tsh(jumla), h.mwenye_harusi, tsh(mgeni.ahadi - jumla), tarehe(h.tarehe_mwisho), h.maelekezo_malipo],
            maandishi=maandishi,
        )
    return _tuma(
        mgeni, "kikumbusho", "kikumbusho",
        [mgeni.jina, h.mwenye_harusi, tarehe(h.tarehe_mwisho), h.maelekezo_malipo],
        maandishi=maandishi,
    )


def tuma_shukrani(mchango: Mchango) -> Ujumbe | None:
    mgeni = mchango.mgeni
    if not mgeni.harusi.shukrani_zimewashwa or kwa_nini_hawezi_kutumiwa(mgeni):
        return None
    return _tuma(
        mgeni, "shukrani", "shukrani",
        [mgeni.jina, tsh(mchango.kiasi), mgeni.harusi.mwenye_harusi, tsh(mgeni.jumla)],
    )


@dataclass
class MatokeoVikumbusho:
    vimetumwa: int = 0
    vimeshindwa: int = 0
    vimerukwa: int = 0
    sababu: str = ""
    makosa: list = field(default_factory=list)


MAKUNDI = {
    "hawajachangia": lambda qs: qs.filter(jumla_iliyotolewa=0),
    "wana_salio": lambda qs: qs.filter(jumla_iliyotolewa__gt=0),
}


def wanaostahili(harusi: Harusi, kundi: str | None = None):
    qs = harusi.wageni.wanaostahili_kikumbusho()
    return MAKUNDI[kundi](qs) if kundi in MAKUNDI else qs


def tuma_vikumbusho(harusi: Harusi, sasa=None, kundi=None, maandishi=None, ruhusu_nje_ya_saa=False) -> MatokeoVikumbusho:
    """Tuma vikumbusho kwa wanaostahili.

    Inaweza kuitwa mara nyingi kwa siku (mfano saa 3 asubuhi na saa 12 jioni).
    Mgeni mmoja hapokei zaidi ya `vikumbusho_kwa_siku`, na kuna pengo la chini
    kati ya kikumbusho kimoja na kingine, hivyo kuitwa mara mbili kwa bahati mbaya
    hakumtumii mtu ujumbe mara mbili.
    """
    sasa = sasa or timezone.now()
    leo_local = timezone.localtime(sasa)
    res = MatokeoVikumbusho()

    if not harusi.vikumbusho_vimewashwa or harusi.vikumbusho_kwa_siku == 0:
        res.sababu = "Vikumbusho vimezimwa."
        return res
    if leo_local.date() > harusi.tarehe_mwisho:
        res.sababu = "Muda wa kuchangia umeisha."
        return res
    # Baileys: worker hutuma saa 2 asubuhi - 2 usiku tu, hivyo kuweka foleni usiku ni salama.
    usiku_sawa = ruhusu_nje_ya_saa and whatsapp.backend() == "baileys"
    if not usiku_sawa and not (SAA_YA_KUANZA <= leo_local.hour < SAA_YA_MWISHO):
        res.sababu = f"Nje ya saa za kutuma ({SAA_YA_KUANZA}:00-{SAA_YA_MWISHO}:00)."
        return res

    mwanzo_wa_siku = leo_local.replace(hour=0, minute=0, second=0, microsecond=0)
    pengo = timedelta(hours=max((SAA_YA_MWISHO - SAA_YA_KUANZA) / harusi.vikumbusho_kwa_siku - 1, 1))
    hesabika = ~Q(jumbe__hali__in=Ujumbe.HALI_ZISIZOHESABIKA)

    wageni = (
        wanaostahili(harusi, kundi)
        .annotate(
            vya_leo=Count(
                "jumbe",
                filter=Q(jumbe__aina="kikumbusho", jumbe__created__gte=mwanzo_wa_siku) & hesabika,
                distinct=True,
            ),
            vyote=Count("jumbe", filter=Q(jumbe__aina="kikumbusho") & hesabika, distinct=True),
            vya_foleni=Count("jumbe", filter=Q(jumbe__hali="kwenye_foleni"), distinct=True),
        )
        .select_related("harusi")
    )
    for mgeni in wageni:
        if (
            mgeni.vya_leo >= harusi.vikumbusho_kwa_siku
            or mgeni.vyote >= harusi.vikumbusho_jumla_max
            or mgeni.vya_foleni  # bado ana ujumbe unaosubiri kutumwa
        ):
            res.vimerukwa += 1
            continue
        mwisho = (
            mgeni.jumbe.filter(aina__in=["kikumbusho", "kadi"])
            .exclude(hali__in=Ujumbe.HALI_ZISIZOHESABIKA)
            .order_by("-created")
            .first()
        )
        if mwisho and sasa - mwisho.created < pengo:
            res.vimerukwa += 1
            continue
        u = tuma_kikumbusho(mgeni, maandishi)
        if u and u.hali != "umeshindwa":
            res.vimetumwa += 1
        else:
            res.vimeshindwa += 1
            if u:
                res.makosa.append(f"{mgeni.jina}: {u.kosa}")
    log.info("Vikumbusho: %s", res)
    return res


def takwimu(harusi: Harusi) -> dict:
    wageni = harusi.wageni.all()
    michango = Mchango.objects.filter(mgeni__harusi=harusi)
    jumla_michango = michango.aggregate(s=Sum("kiasi"))["s"] or 0
    ahadi = wageni.aggregate(s=Sum("ahadi"))["s"] or 0
    na_jumla = list(harusi.wageni.na_jumla().values("ahadi", "jumla_iliyotolewa"))
    salio_ahadi = sum(max((r["ahadi"] or 0) - r["jumla_iliyotolewa"], 0) for r in na_jumla)
    wote = wageni.count()
    wamechangia = wageni.filter(michango__isnull=False).distinct().count()
    kwa_njia = list(
        michango.values("njia").annotate(s=Sum("kiasi"), n=Count("id")).order_by("-s")
    )
    majina_njia = dict(Mchango.NJIA)
    for r in kwa_njia:
        r["jina"] = majina_njia.get(r["njia"], r["njia"])
    return {
        "wageni": wote,
        "wametumiwa": wageni.filter(kadi_imetumwa__isnull=False).count(),
        "hawajatumiwa": wageni.filter(kadi_imetumwa__isnull=True).count(),
        "wamechangia": wamechangia,
        "hawajachangia": wote - wamechangia,
        "jumla_michango": jumla_michango,
        "idadi_michango": michango.count(),
        "ahadi": ahadi,
        "salio_ahadi": salio_ahadi,
        "asilimia_wamechangia": round(100 * wamechangia / wote) if wote else 0,
        "kwa_njia": kwa_njia,
        "jumbe_leo": Ujumbe.objects.filter(
            mgeni__harusi=harusi, created__date=timezone.localdate()
        ).exclude(hali__in=Ujumbe.HALI_ZISIZOHESABIKA).count(),
        "jumbe_zilizoshindwa": Ujumbe.objects.filter(mgeni__harusi=harusi, hali="umeshindwa").count(),
        "jumbe_foleni": Ujumbe.objects.filter(mgeni__harusi=harusi, hali="kwenye_foleni").count(),
        "whatsapp_hewani": whatsapp.iko_hewani(),
        "whatsapp_backend": whatsapp.backend(),
    }
