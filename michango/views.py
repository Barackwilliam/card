import csv
import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import huduma, jumbe, whatsapp
from .anzisha import anzisha_harusi, mahali_pa_picha
from .forms import (
    AnzishaForm, HarusiForm, IngizaForm, KadiForm, KumbushaForm, MchangoForm, MgeniForm, PichaYaKadiForm, UjumbeForm,
)
from .ingiza import ingiza_csv
from .kadi import tengeneza_kadi
from .models import Harusi, Mchango, Mgeni, Ujumbe, WhatsAppHali, safisha_simu

log = logging.getLogger("michango")

VICHUJIO = {
    "wote": ("Wote", lambda qs: qs),
    "hawajatumiwa": ("Hawajatumiwa kadi", lambda qs: qs.filter(kadi_imetumwa__isnull=True)),
    "wametumiwa": ("Wametumiwa kadi", lambda qs: qs.filter(kadi_imetumwa__isnull=False)),
    "hawajachangia": ("Hawajachangia", lambda qs: qs.filter(jumla_iliyotolewa=0)),
    "wamechangia": ("Wamechangia", lambda qs: qs.filter(jumla_iliyotolewa__gt=0)),
    "wana_salio": ("Wana salio", lambda qs: qs.filter(jumla_iliyotolewa__gt=0, ahadi__gt=F("jumla_iliyotolewa"))),
    "bila_simu": ("Bila namba", lambda qs: qs.filter(simu="")),
}


def _wageni_wa_kichujio(harusi, kichujio, q):
    qs = VICHUJIO.get(kichujio, VICHUJIO["wote"])[1](harusi.wageni.na_jumla())
    if q:
        simu = safisha_simu(q) if any(c.isdigit() for c in q) else ""
        cond = Q(jina__icontains=q)
        if simu:
            cond |= Q(simu__contains=simu)
        qs = qs.filter(cond)
    return qs


def harusi_au_setup(view):
    """Hakikisha kuna harusi; vinginevyo onyesha ukurasa wa kuanzisha."""

    def wrapper(request, *args, **kwargs):
        harusi = Harusi.ya_sasa()
        if not harusi:
            return anzisha(request)
        return view(request, harusi, *args, **kwargs)

    wrapper.__name__ = view.__name__
    return login_required(wrapper)


def anzisha(request):
    """Ukurasa wa kuanzisha harusi ya kwanza (unaonekana mpaka harusi iwepo)."""
    kosa = ""
    if request.method == "POST" and request.user.is_staff and not Harusi.objects.exists():
        form = AnzishaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                anzisha_harusi(
                    jina=d["jina"], mwenye_harusi=d["mwenye_harusi"], familia=d["familia"],
                    tarehe_mwisho=d["tarehe_mwisho"], malipo=d["malipo"],
                )
            except Exception as e:  # onyesha kosa halisi (mfano la Supabase) badala ya kulificha kwenye logs
                log.exception("Kuanzisha harusi kumeshindwa")
                kosa = f"{type(e).__name__}: {e}"
            else:
                messages.success(request, "Harusi imeanzishwa.")
                return redirect("dashibodi")
    else:
        form = AnzishaForm()
    return render(
        request,
        "michango/hakuna_harusi.html",
        {"form": form, "kosa": kosa, "mahali_pa_picha": mahali_pa_picha(), "debug": settings.DEBUG},
    )


@harusi_au_setup
def dashibodi(request, harusi):
    t = huduma.takwimu(harusi)
    michango = Mchango.objects.filter(mgeni__harusi=harusi).select_related("mgeni")[:6]
    siku_zilizobaki = (harusi.tarehe_mwisho - timezone.localdate()).days
    wa = WhatsAppHali.pata() if t["whatsapp_backend"] == "baileys" else None
    wa_tayari = (wa.hali == "imeunganishwa" and wa.worker_yuko_hewani) if wa else t["whatsapp_backend"] == "cloud"
    hatua = [
        {"jina": "Ingiza orodha ya wageni", "imekamilika": t["wageni"] > 0, "url": reverse("ingiza")},
        {"jina": "Weka namba ya kupokea michango", "imekamilika": not harusi.maelekezo_malipo.startswith("Wasiliana"),
         "url": reverse("mipangilio") + "?sehemu=harusi"},
        {"jina": "Chagua muonekano wa jina kwenye kadi", "imekamilika": harusi.wageni.exclude(kadi="").exists() or t["wametumiwa"] > 0,
         "url": reverse("mipangilio") + "?sehemu=kadi"},
        {"jina": "Unganisha WhatsApp", "imekamilika": wa_tayari, "url": reverse("whatsapp")},
        {"jina": "Tuma kadi kwa wageni", "imekamilika": t["wametumiwa"] > 0,
         "url": reverse("wageni") + "?hali=hawajatumiwa&chagua=1"},
    ]
    return render(
        request,
        "michango/dashibodi.html",
        {"harusi": harusi, "t": t, "michango": michango, "siku_zilizobaki": siku_zilizobaki, "wa": wa,
         "wa_tayari": wa_tayari, "hatua": hatua, "hatua_zimebaki": sum(not h["imekamilika"] for h in hatua)},
    )


@harusi_au_setup
def wageni(request, harusi):
    kichujio = request.GET.get("hali", "wote")
    if kichujio not in VICHUJIO:
        kichujio = "wote"
    q = request.GET.get("q", "").strip()
    qs = _wageni_wa_kichujio(harusi, kichujio, q)
    page = Paginator(qs.order_by("jina"), 50).get_page(request.GET.get("ukurasa"))
    msingi = harusi.wageni.na_jumla()
    vichujio = [(k, v[0], v[1](msingi).count()) for k, v in VICHUJIO.items()]
    return render(
        request,
        "michango/wageni.html",
        {"harusi": harusi, "page": page, "kichujio": kichujio, "q": q, "vichujio": vichujio,
         "chagua": request.GET.get("chagua") == "1", "jumla": page.paginator.count,
         "orodha_ya_kunakili": huduma.maandishi_ya_orodha(harusi, kichujio, list(_panga(qs, kichujio)[:500])),
         "bila_namba": msingi.filter(simu="").count()},
    )


def _panga(qs, kichujio):
    return qs.order_by("-jumla_iliyotolewa", "jina") if kichujio in ("wamechangia", "wana_salio") else qs.order_by("jina")


@harusi_au_setup
def wageni_pdf(request, harusi):
    """Pakua orodha ya kichujio kama PDF iliyopambwa."""
    from .pdf import VICHWA, tengeneza_pdf

    kichujio = request.GET.get("hali", "wote")
    if kichujio not in VICHUJIO:
        kichujio = "wote"
    qs = _panga(_wageni_wa_kichujio(harusi, kichujio, request.GET.get("q", "").strip()), kichujio)
    data = tengeneza_pdf(harusi, kichujio, qs, huduma.takwimu(harusi))
    jina = f"{VICHWA.get(kichujio, VICHWA['wote'])[0]} - {harusi.jina}.pdf"
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{jina}"'
    return resp


@harusi_au_setup
def bila_namba(request, harusi):
    """Wageni wasio na namba: nakili orodha kwa WhatsApp, na weka namba zao papo hapo."""
    if request.method == "POST":
        m = get_object_or_404(harusi.wageni, pk=request.POST.get("mgeni"), simu="")
        form = MgeniForm({"jina": m.jina, "simu": request.POST.get("simu", ""), "ahadi": m.ahadi or "",
                          "maelezo": m.maelezo}, instance=m, harusi=harusi)
        if not request.POST.get("simu", "").strip():
            messages.warning(request, "Andika namba kwanza.")
        elif form.is_valid():
            form.save()
            messages.success(request, f"Namba ya {m.jina} imehifadhiwa.")
        else:
            messages.error(request, f"{m.jina}: {' '.join(form.errors.get('simu', ['Namba si sahihi.']))}")
        return redirect("bila_namba")
    wageni = list(harusi.wageni.na_jumla().filter(simu="").order_by("jina"))
    return render(request, "michango/bila_namba.html", {
        "harusi": harusi, "wageni": wageni,
        "maandishi": huduma.maandishi_ya_orodha(harusi, "bila_simu", wageni),
    })


@require_POST
@harusi_au_setup
def wageni_kitendo(request, harusi):
    """Vitendo kwa wageni waliochaguliwa."""
    ids = request.POST.getlist("chagua")
    kitendo = request.POST.get("kitendo")
    rudi = request.POST.get("rudi") or reverse("wageni")
    if request.POST.get("wote_wa_kichujio") == "1":
        # "Chagua wote": wote wanaolingana na kichujio, si ukurasa huu tu
        ids = list(_wageni_wa_kichujio(harusi, request.POST.get("hali", "wote"), request.POST.get("q", "").strip())
                   .values_list("pk", flat=True))
    chaguliwa = harusi.wageni.filter(pk__in=ids)
    if not ids:
        messages.warning(request, "Chagua angalau mgeni mmoja kwanza.")
        return redirect(rudi)

    if kitendo == "tuma_kadi":
        tumwa, jaribio, shindwa, rukwa, foleni = 0, 0, 0, 0, 0
        for m in chaguliwa.select_related("harusi"):
            u = huduma.tuma_kadi(m)
            if not u:
                rukwa += 1
            elif u.hali == "kwenye_foleni":
                foleni += 1
            elif u.hali == "jaribio":
                jaribio += 1
            elif u.hali == "umeshindwa":
                shindwa += 1
            else:
                tumwa += 1
        if tumwa:
            messages.success(request, f"Kadi {tumwa} zimetumwa WhatsApp.")
        if foleni:
            messages.success(
                request,
                f"Kadi {foleni} zimewekwa kwenye foleni. Zitatumwa polepole (moja kila dakika 1-2) ili kulinda namba.",
            )
        if jaribio:
            messages.info(request, f"Majaribio: kadi {jaribio} zimetengenezwa lakini hazijatumwa (WhatsApp haijaunganishwa).")
        if shindwa:
            messages.error(request, f"Kadi {shindwa} zimeshindwa kutumwa. Angalia sababu kwenye ukurasa wa mgeni.")
        if rukwa:
            messages.warning(request, f"Wageni {rukwa} wamerukwa: hawana namba au wameomba wasitumiwe ujumbe.")
    elif kitendo == "alama_imetumwa":
        n = chaguliwa.filter(kadi_imetumwa__isnull=True).update(kadi_imetumwa=timezone.now())
        messages.success(request, f"Wageni {n} wamewekwa alama kuwa wametumiwa kadi.")
    elif kitendo == "tengeneza_kadi":
        from PIL import Image

        with harusi.kadi_template.open("rb") as f:
            tpl = Image.open(f)
            tpl.load()
        for m in chaguliwa:
            tengeneza_kadi(m, tpl)
        messages.success(request, f"Kadi {chaguliwa.count()} zimetengenezwa upya.")
    else:
        messages.error(request, "Kitendo hakijulikani.")
    return redirect(rudi)


@harusi_au_setup
def mgeni(request, harusi, pk):
    m = get_object_or_404(harusi.wageni.na_jumla(), pk=pk)
    form = MchangoForm(harusi=harusi, mgeni=m, initial={"mgeni": m})
    historia = [{"aina": "mchango", "muda": c.created, "c": c} for c in m.michango.all()]
    historia += [{"aina": "ujumbe", "muda": j.created, "j": j} for j in m.jumbe.exclude(hali="jaribio")[:40]]
    historia.sort(key=lambda x: x["muda"], reverse=True)
    return render(
        request,
        "michango/mgeni.html",
        {"harusi": harusi, "m": m, "form": form, "michango": m.michango.all(), "historia": historia,
         "kiasi_haraka": [10000, 20000, 50000, 100000, 200000]},
    )


@harusi_au_setup
def mgeni_fomu(request, harusi, pk=None):
    m = get_object_or_404(harusi.wageni, pk=pk) if pk else Mgeni(harusi=harusi)
    jina_la_zamani = m.jina
    if request.method == "POST":
        form = MgeniForm(request.POST, instance=m, harusi=harusi)
        if form.is_valid():
            m = form.save()
            if pk and m.kadi and m.jina != jina_la_zamani:
                tengeneza_kadi(m)
                messages.info(request, "Jina limebadilika, kadi imetengenezwa upya.")
            messages.success(request, f"{m.jina} amehifadhiwa.")
            return redirect("mgeni", pk=m.pk)
    else:
        form = MgeniForm(instance=m, harusi=harusi)
    return render(request, "michango/mgeni_fomu.html", {"harusi": harusi, "form": form, "m": m if pk else None})


@require_POST
@harusi_au_setup
def mgeni_kitendo(request, harusi, pk):
    m = get_object_or_404(harusi.wageni, pk=pk)
    kitendo = request.POST.get("kitendo")
    if kitendo == "tuma_kadi":
        u = huduma.tuma_kadi(m)
        _taarifa_ujumbe(request, u, m, "Kadi")
    elif kitendo == "kikumbusho":
        u = huduma.tuma_kikumbusho(m)
        _taarifa_ujumbe(request, u, m, "Kikumbusho")
    elif kitendo == "jaribio_sasa":
        u, sababu = huduma.tuma_jaribio_sasa(m)
        if sababu:
            messages.warning(request, sababu)
        else:
            messages.success(
                request,
                f"Jaribio limepelekwa mbele ya foleni. Kadi itafika kwa {m.jina} ndani ya dakika 1-2 "
                f"(kama WhatsApp imeunganishwa). Majaribio yaliyobaki leo: {huduma.majaribio_yaliyobaki(harusi)}.",
            )
    elif kitendo == "tengeneza_kadi":
        tengeneza_kadi(m)
        messages.success(request, "Kadi imetengenezwa upya.")
    elif kitendo == "alama_imetumwa":
        m.kadi_imetumwa = timezone.now()
        m.save(update_fields=["kadi_imetumwa"])
        messages.success(request, "Imewekwa alama: ametumiwa kadi.")
    elif kitendo == "ondoa_alama":
        m.kadi_imetumwa = None
        m.save(update_fields=["kadi_imetumwa"])
        messages.success(request, "Alama ya kutumiwa kadi imeondolewa.")
    return redirect("mgeni", pk=m.pk)


def _taarifa_ujumbe(request, u, m, nini):
    if u is None:
        messages.warning(request, huduma.kwa_nini_hawezi_kutumiwa(m) or "Haikutumwa.")
    elif u.hali == "kwenye_foleni":
        messages.success(request, f"{nini} imewekwa kwenye foleni, itatumwa kwa {m.jina} hivi punde.")
    elif u.hali == "jaribio":
        messages.info(request, f"Majaribio: {nini.lower()} haikutumwa kwa sababu WhatsApp haijaunganishwa.")
    elif u.hali == "umeshindwa":
        messages.error(request, f"{nini} imeshindwa kutumwa: {u.kosa}")
    else:
        messages.success(request, f"{nini} imetumwa kwa {m.jina}.")


@harusi_au_setup
def mchango_mpya(request, harusi):
    mgeni_pk = request.POST.get("mgeni") or request.GET.get("mgeni")
    mg = harusi.wageni.filter(pk=mgeni_pk).first() if mgeni_pk else None
    if request.method == "POST":
        form = MchangoForm(request.POST, harusi=harusi, mgeni=mg)
        if form.is_valid():
            ch = form.save(commit=False)
            ch.aliyeingiza = request.user
            ch.save()
            messages.success(request, f"Mchango wa TSh {ch.kiasi:,} kutoka kwa {ch.mgeni.jina} umehifadhiwa.")
            if form.cleaned_data.get("tuma_shukrani"):
                u = huduma.tuma_shukrani(ch)
                if u and u.hali == "kwenye_foleni":
                    messages.success(request, "Ujumbe wa shukrani umewekwa kwenye foleni.")
                elif u and u.hali == "umeshindwa":
                    messages.error(request, f"Shukrani haikutumwa: {u.kosa}")
                elif u and u.hali == "jaribio":
                    messages.info(request, "Majaribio: shukrani haikutumwa (WhatsApp haijaunganishwa).")
                elif u:
                    messages.success(request, "Ujumbe wa shukrani umetumwa.")
            return redirect(request.POST.get("rudi") or reverse("mgeni", args=[ch.mgeni_id]))
    else:
        form = MchangoForm(harusi=harusi, mgeni=mg)
    orodha = [] if mg else list(harusi.wageni.order_by("jina").values("pk", "jina", "simu"))
    return render(
        request,
        "michango/mchango_fomu.html",
        {"harusi": harusi, "form": form, "mg": mg, "orodha": orodha, "kiasi_haraka": [10000, 20000, 50000, 100000, 200000]},
    )


@require_POST
@harusi_au_setup
def mchango_futa(request, harusi, pk):
    ch = get_object_or_404(Mchango, pk=pk, mgeni__harusi=harusi)
    mgeni_pk = ch.mgeni_id
    ch.delete()
    messages.success(request, "Mchango umefutwa.")
    return redirect("mgeni", pk=mgeni_pk)


@harusi_au_setup
def michango(request, harusi):
    qs = Mchango.objects.filter(mgeni__harusi=harusi).select_related("mgeni", "aliyeingiza")
    njia = request.GET.get("njia", "")
    if njia:
        qs = qs.filter(njia=njia)
    if request.GET.get("pakua") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="michango.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["Tarehe", "Jina", "Simu", "Kiasi", "Njia", "Namba ya muamala", "Maelezo"])
        for c in qs:
            w.writerow([c.tarehe, c.mgeni.jina, c.mgeni.simu, c.kiasi, c.get_njia_display(), c.kumbukumbu, c.maelezo])
        return resp
    jumla = qs.aggregate(s=Sum("kiasi"))["s"] or 0
    page = Paginator(qs, 50).get_page(request.GET.get("ukurasa"))
    return render(
        request,
        "michango/michango.html",
        {"harusi": harusi, "page": page, "jumla": jumla, "njia": njia, "njia_zote": Mchango.NJIA},
    )


@harusi_au_setup
def ingiza(request, harusi):
    if request.method == "POST":
        form = IngizaForm(request.POST, request.FILES)
        if form.is_valid():
            res = ingiza_csv(harusi, form.cleaned_data["faili"].read(), request.user)
            messages.success(
                request,
                f"Wageni wapya {res.wapya}, waliosasishwa {res.wamesasishwa}, michango iliyoingizwa {res.michango}.",
            )
            for k in res.makosa:
                messages.error(request, k)
            return redirect("wageni")
    else:
        form = IngizaForm()
    return render(request, "michango/ingiza.html", {"harusi": harusi, "form": form})


@harusi_au_setup
def tuma_vikumbusho_sasa(request, harusi):
    if request.method != "POST":
        return redirect("dashibodi")
    res = huduma.tuma_vikumbusho(harusi)
    if res.sababu:
        messages.warning(request, f"Hakuna kikumbusho kilichotumwa: {res.sababu}")
    else:
        messages.success(
            request,
            f"Vikumbusho vimetumwa: {res.vimetumwa}. Vimerukwa (tayari wamekumbushwa): {res.vimerukwa}. Vimeshindwa: {res.vimeshindwa}.",
        )
    return redirect("dashibodi")


def _mfano_wa_vishika(harusi):
    """Thamani za mfano za kuonyesha ujumbe utakavyoonekana (onyesho la WhatsApp)."""
    jina = harusi.wageni.order_by("-pk").values_list("jina", flat=True).first() or "Neema Mollel"
    return {
        "jina": jina, "JINA": jina.upper(), "bwana_harusi": harusi.mwenye_harusi, "tarehe": huduma.tarehe(harusi.tarehe_mwisho),
        "malipo": harusi.maelekezo_malipo, "salio": "60,000", "ametoa": "40,000", "kiasi": "50,000", "jumla": "90,000",
    }


@harusi_au_setup
def kumbusha(request, harusi):
    """Andika ujumbe wa kikumbusho na uutume kwa kundi la wageni."""
    kundi = request.POST.get("kundi") or request.GET.get("kundi") or "hawajachangia"
    if kundi not in dict(KumbushaForm.KUNDI):
        kundi = "hawajachangia"
    hifadhiwa = {"hawajachangia": harusi.ujumbe_kikumbusho, "wana_salio": harusi.ujumbe_salio}
    mifano = {"hawajachangia": jumbe.MFANO["kikumbusho"], "wana_salio": jumbe.MFANO["kikumbusho_salio"]}
    if request.method == "POST":
        form = KumbushaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            if d["hifadhi"]:
                setattr(harusi, "ujumbe_salio" if d["kundi"] == "wana_salio" else "ujumbe_kikumbusho", d["maandishi"])
                harusi.save(update_fields=["ujumbe_salio", "ujumbe_kikumbusho"])
            res = huduma.tuma_vikumbusho(harusi, kundi=d["kundi"], maandishi=d["maandishi"], ruhusu_nje_ya_saa=True)
            if res.sababu:
                messages.warning(request, f"Hakuna kikumbusho kilichotumwa: {res.sababu}")
                return redirect(reverse("kumbusha") + f"?kundi={d['kundi']}")
            if res.vimetumwa:
                saa = timezone.localtime().hour
                lini = " Vitaanza kutumwa saa 2 asubuhi." if not (huduma.SAA_YA_KUANZA <= saa < huduma.SAA_YA_MWISHO) else ""
                messages.success(request, f"Vikumbusho {res.vimetumwa} vimeandaliwa na vinatumwa polepole.{lini}")
            if res.vimerukwa:
                messages.info(request, f"Watu {res.vimerukwa} wamerukwa kwa sababu tayari wamekumbushwa leo au wamefikia kikomo.")
            if not res.vimetumwa and not res.vimerukwa:
                messages.info(request, "Hakuna mtu wa kukumbusha kwenye kundi hili kwa sasa.")
            return redirect("whatsapp" if whatsapp.backend() == "baileys" else "dashibodi")
    else:
        form = KumbushaForm(initial={"kundi": kundi, "maandishi": hifadhiwa[kundi] or mifano[kundi]})
    idadi = {k: huduma.wanaostahili(harusi, k).count() for k, _ in KumbushaForm.KUNDI}
    return render(
        request,
        "michango/kumbusha.html",
        {"harusi": harusi, "form": form, "kundi": kundi, "idadi": idadi, "backend": whatsapp.backend(),
         "maandishi_ya_kundi": {k: hifadhiwa[k] or mifano[k] for k in hifadhiwa},
         "vishika_vya_kundi": {"hawajachangia": jumbe.vishika_vya("kikumbusho"), "wana_salio": jumbe.vishika_vya("kikumbusho_salio")},
         "maelezo_vishika": jumbe.MAELEZO_YA_VISHIKA, "mfano": _mfano_wa_vishika(harusi)},
    )


@harusi_au_setup
def mipangilio(request, harusi):
    """Mipangilio yote kwa lugha rahisi: harusi, muonekano wa kadi, ujumbe."""
    sehemu = request.GET.get("sehemu") or request.POST.get("sehemu") or "harusi"
    if sehemu not in ("harusi", "kadi", "ujumbe"):
        sehemu = "harusi"
    forms_ = {
        "harusi": HarusiForm(instance=harusi),
        "kadi": KadiForm(instance=harusi),
        "ujumbe": UjumbeForm(instance=harusi),
    }
    picha_form = PichaYaKadiForm()
    if request.method == "POST":
        if sehemu == "kadi" and request.POST.get("kitendo") == "picha":
            picha_form = PichaYaKadiForm(request.POST, request.FILES)
            if picha_form.is_valid():
                harusi.kadi_template.save(f"kadi-{harusi.pk}.jpg", picha_form.cleaned_data["picha"], save=True)
                _kadi_zimebadilika(request, harusi)
                messages.success(request, "Picha ya kadi imebadilishwa. Sasa sogeza jina mahali panapofaa.")
                return redirect(reverse("mipangilio") + "?sehemu=kadi")
        else:
            cls = {"harusi": HarusiForm, "kadi": KadiForm, "ujumbe": UjumbeForm}[sehemu]
            form = cls(request.POST, instance=harusi)
            if form.is_valid():
                form.save()
                if sehemu == "kadi" and form.cleaned_data.get("tengeneza_upya"):
                    _kadi_zimebadilika(request, harusi)
                messages.success(request, "Imehifadhiwa.")
                return redirect(reverse("mipangilio") + f"?sehemu={sehemu}")
            forms_[sehemu] = form
    mfano = harusi.wageni.order_by("-pk").values_list("jina", flat=True).first() or "Neema Mollel"
    return render(
        request,
        "michango/mipangilio.html",
        {"harusi": harusi, "sehemu": sehemu, "forms": forms_, "picha_form": picha_form,
         "fonti": [{"faili": f, "jina": j, "css": c} for f, j, c in Harusi.FONTI_ZOTE], "jina_mfano": mfano,
         "rangi": ["#0d1b4d", "#13235e", "#1f2f7a", "#7a5a12", "#b8892b", "#000000", "#ffffff", "#8b1e3f"],
         "backend": whatsapp.backend(), "mfano": _mfano_wa_vishika(harusi), "maelezo_vishika": jumbe.MAELEZO_YA_VISHIKA,
         "sehemu_za_ujumbe": [
             {"jina": "ujumbe_kadi", "kichwa": "Ujumbe unaoambatana na kadi", "template": "kadi", "kikumbusho": False},
             {"jina": "ujumbe_kikumbusho", "kichwa": "Kikumbusho: hawajachangia", "template": "kikumbusho", "kikumbusho": True},
             {"jina": "ujumbe_salio", "kichwa": "Kikumbusho: wenye salio la ahadi", "template": "kikumbusho_salio", "kikumbusho": True},
             {"jina": "ujumbe_shukrani", "kichwa": "Shukrani mtu akichangia", "template": "shukrani", "kikumbusho": False},
         ],
         "vishika": {k: jumbe.vishika_vya(k) for k in jumbe.VISHIKA}, "mifano_ya_ujumbe": jumbe.MFANO},
    )


def _kadi_zimebadilika(request, harusi):
    """Muonekano umebadilika: kadi za zamani zitatengenezwa upya zikitumwa au zikifunguliwa."""
    harusi.wageni.exclude(kadi="").update(kadi="")
    n = Ujumbe.objects.filter(mgeni__harusi=harusi, aina="kadi", hali="kwenye_foleni").update(
        hali="imeghairiwa", kosa="Muonekano wa kadi ulibadilishwa; tuma tena"
    )
    if n:
        messages.warning(request, f"Kadi {n} zilizokuwa zinasubiri kutumwa zimesimamishwa ili zisiende na muonekano wa zamani. Zitume tena.")


@harusi_au_setup
def whatsapp_hali(request, harusi):
    """Hali ya Baileys: QR ya kuunganisha, foleni, na kusitisha/kuendelea."""
    hali = WhatsAppHali.pata()
    if request.method == "POST" and request.user.is_staff:
        kitendo = request.POST.get("kitendo")
        if kitendo == "sitisha":
            hali.imesitishwa = True
            hali.save(update_fields=["imesitishwa", "updated"])
            messages.success(request, "Utumaji umesitishwa. Hakuna ujumbe utakaotumwa mpaka ubofye Endelea.")
        elif kitendo == "endelea":
            hali.imesitishwa = False
            hali.imesimamishwa_mpaka = None
            hali.sababu_ya_kusimama = ""
            hali.save(update_fields=["imesitishwa", "imesimamishwa_mpaka", "sababu_ya_kusimama", "updated"])
            messages.success(request, "Utumaji umeendelea.")
        elif kitendo == "futa_foleni":
            n = Ujumbe.objects.filter(mgeni__harusi=harusi, hali="kwenye_foleni").update(
                hali="imeghairiwa", kosa="Imeghairiwa na msimamizi"
            )
            messages.success(request, f"Jumbe {n} zimeondolewa kwenye foleni.")
        return redirect("whatsapp")
    leo = timezone.localdate()
    jumbe = Ujumbe.objects.filter(mgeni__harusi=harusi)
    ctx = {
        "harusi": harusi,
        "hali": hali,
        "backend": whatsapp.backend(),
        "foleni": jumbe.filter(hali="kwenye_foleni").count(),
        "zilizotumwa_leo": jumbe.filter(umetumwa_at__date=leo).count(),
        "zilizoshindwa_leo": jumbe.filter(hali="umeshindwa", updated__date=leo).count(),
        "za_karibuni": jumbe.exclude(hali="jaribio").select_related("mgeni")[:15],
        "ndani_ya_saa": huduma.SAA_YA_KUANZA <= timezone.localtime().hour < huduma.SAA_YA_MWISHO,
        "sasa": timezone.now(),
    }
    if request.GET.get("json"):
        return JsonResponse({"hali": hali.hali, "qr": hali.qr, "foleni": ctx["foleni"], "hewani": hali.worker_yuko_hewani})
    return render(request, "michango/whatsapp.html", ctx)


# ---------- Kwa huduma za nje ----------


def afya(request):
    """Ukurasa mwepesi kwa cron-job.org: unaifanya huduma isilale, na unaonyesha hali ya worker."""
    data = {"ok": True, "whatsapp": whatsapp.backend()}
    if data["whatsapp"] == "baileys":
        try:
            h = WhatsAppHali.objects.filter(pk=1).first()
            data["worker_hewani"] = bool(h and h.worker_yuko_hewani)
            data["hali"] = h.hali if h else "haijaanza"
        except Exception:
            data["ok"] = False
    return JsonResponse(data)


@csrf_exempt
def cron_vikumbusho(request):
    """Inaitwa na scheduler (cron-job.org, GitHub Actions, n.k.) kuanzisha vikumbusho.

    Siri (CRON_SECRET) inaweza kutumwa kwa njia yoyote kati ya hizi:
      - header: `Authorization: Bearer <siri>`
      - kwenye URL: `/cron/vikumbusho/?siri=<siri>` (rahisi kwa cron-job.org)
    GET na POST zote zinakubaliwa. Ni salama kuiita mara nyingi: vikomo vya
    Mipangilio vinazuia mtu kutumiwa zaidi ya mara zilizoruhusiwa.
    """
    siri = (settings.CRON_SECRET or "").strip()
    if not siri:
        return HttpResponseForbidden(
            "CRON_SECRET haijawekwa kwenye server. Iongeze kwenye Render -> Environment, kisha deploy upya."
        )
    header = request.headers.get("Authorization", "").strip()
    iliyotumwa = header[7:].strip() if header.lower().startswith("bearer ") else request.GET.get("siri", "").strip()
    if not iliyotumwa:
        return HttpResponseForbidden(
            "Siri haikutumwa. Ongeza ?siri=<CRON_SECRET> mwishoni mwa URL, au header 'Authorization: Bearer <CRON_SECRET>'."
        )
    if not hmac.compare_digest(iliyotumwa, siri):
        return HttpResponseForbidden("Siri hailingani na CRON_SECRET ya server. Hakikisha umenakili neno lilelile.")
    matokeo = {}
    for h in Harusi.objects.all():
        r = huduma.tuma_vikumbusho(h)
        matokeo[h.jina] = {"vimetumwa": r.vimetumwa, "vimerukwa": r.vimerukwa, "vimeshindwa": r.vimeshindwa,
                           "sababu": r.sababu}
    return JsonResponse(matokeo)


HALI_ZA_WA = {"sent": "umetumwa", "delivered": "umefika", "read": "umesomwa", "failed": "umeshindwa"}
MANENO_YA_KUJITOA = {"acha", "stop", "sitaki", "unsubscribe", "ondoa"}


@csrf_exempt
def webhook_whatsapp(request):
    cfg = settings.WHATSAPP
    if request.method == "GET":
        if (
            request.GET.get("hub.mode") == "subscribe"
            and cfg["VERIFY_TOKEN"]
            and hmac.compare_digest(request.GET.get("hub.verify_token", ""), cfg["VERIFY_TOKEN"])
        ):
            return HttpResponse(request.GET.get("hub.challenge", ""))
        return HttpResponseForbidden()
    if request.method != "POST":
        return HttpResponse(status=405)
    if not whatsapp.sahihi_ni_halali(request.body, request.headers.get("X-Hub-Signature-256", "")):
        return HttpResponseForbidden()
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for st in value.get("statuses", []):
                hali = HALI_ZA_WA.get(st.get("status"))
                if not hali:
                    continue
                kosa = ""
                if st.get("errors"):
                    e = st["errors"][0]
                    kosa = f"{e.get('code')}: {e.get('title') or e.get('message', '')}"
                upd = {"hali": hali}
                if kosa:
                    upd["kosa"] = kosa
                Ujumbe.objects.filter(wa_id=st.get("id", "")).exclude(hali="umesomwa").update(**upd)
            for msg in value.get("messages", []):
                text = ""
                if msg.get("type") == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg.get("type") == "button":
                    text = msg.get("button", {}).get("text", "")
                if text.strip().lower() in MANENO_YA_KUJITOA:
                    simu = safisha_simu("+" + msg.get("from", ""))
                    n = Mgeni.objects.filter(simu=simu).update(amejitoa=True)
                    log.info("Mgeni %s ameomba kusitisha ujumbe (%s rekodi).", simu, n)
    return HttpResponse("ok")
