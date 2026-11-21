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

from . import huduma, whatsapp
from .anzisha import anzisha_harusi, mahali_pa_picha
from .forms import AnzishaForm, IngizaForm, MchangoForm, MgeniForm
from .ingiza import ingiza_csv
from .kadi import tengeneza_kadi
from .models import Harusi, Mchango, Mgeni, Ujumbe, WhatsAppHali, safisha_simu

log = logging.getLogger("michango")

VICHUJIO = {
    "wote": ("Wote", lambda qs: qs),
    "hawajatumiwa": ("Hawajatumiwa kadi", lambda qs: qs.filter(kadi_imetumwa__isnull=True)),
    "wametumiwa": ("Wametumiwa kadi", lambda qs: qs.filter(kadi_imetumwa__isnull=False)),
    "wamechangia": ("Wamechangia", lambda qs: qs.filter(jumla_iliyotolewa__gt=0)),
    "hawajachangia": ("Hawajachangia", lambda qs: qs.filter(jumla_iliyotolewa=0)),
    "wana_salio": ("Wana salio la ahadi", lambda qs: qs.filter(jumla_iliyotolewa__gt=0, ahadi__gt=F("jumla_iliyotolewa"))),
    "bila_simu": ("Hawana namba", lambda qs: qs.filter(simu="")),
}


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
    michango = Mchango.objects.filter(mgeni__harusi=harusi).select_related("mgeni")[:8]
    jumbe = Ujumbe.objects.filter(mgeni__harusi=harusi).select_related("mgeni")[:8]
    wakubwa = harusi.wageni.na_jumla().filter(jumla_iliyotolewa__gt=0).order_by("-jumla_iliyotolewa")[:5]
    siku_zilizobaki = (harusi.tarehe_mwisho - timezone.localdate()).days
    return render(
        request,
        "michango/dashibodi.html",
        {"harusi": harusi, "t": t, "michango": michango, "jumbe": jumbe, "wakubwa": wakubwa,
         "siku_zilizobaki": siku_zilizobaki, "wa": WhatsAppHali.pata() if t["whatsapp_backend"] == "baileys" else None},
    )


@harusi_au_setup
def wageni(request, harusi):
    kichujio = request.GET.get("hali", "wote")
    if kichujio not in VICHUJIO:
        kichujio = "wote"
    q = request.GET.get("q", "").strip()
    qs = harusi.wageni.na_jumla()
    qs = VICHUJIO[kichujio][1](qs)
    if q:
        simu = safisha_simu(q) if any(c.isdigit() for c in q) else ""
        cond = Q(jina__icontains=q)
        if simu:
            cond |= Q(simu__contains=simu)
        qs = qs.filter(cond)
    page = Paginator(qs.order_by("jina"), 50).get_page(request.GET.get("ukurasa"))
    vichujio = [(k, v[0]) for k, v in VICHUJIO.items()]
    return render(
        request,
        "michango/wageni.html",
        {"harusi": harusi, "page": page, "kichujio": kichujio, "q": q, "vichujio": vichujio},
    )


@require_POST
@harusi_au_setup
def wageni_kitendo(request, harusi):
    """Vitendo kwa wageni waliochaguliwa."""
    ids = request.POST.getlist("chagua")
    kitendo = request.POST.get("kitendo")
    rudi = request.POST.get("rudi") or reverse("wageni")
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
    return render(
        request,
        "michango/mgeni.html",
        {"harusi": harusi, "m": m, "form": form, "michango": m.michango.all(), "jumbe": m.jumbe.all()[:30]},
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
    return render(request, "michango/mchango_fomu.html", {"harusi": harusi, "form": form, "mg": mg})


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
    """Inaitwa na scheduler (GitHub Actions, cron-job.org, n.k.) mara 2 kwa siku.

    Tuma siri kwenye header: `Authorization: Bearer <CRON_SECRET>`.
    """
    siri = settings.CRON_SECRET
    header = request.headers.get("Authorization", "")
    if not siri or not hmac.compare_digest(header, f"Bearer {siri}"):
        return HttpResponseForbidden("Siri si sahihi.")
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
