import hashlib
import hmac
import io
import json
import shutil
import tempfile
from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import huduma, whatsapp
from .ingiza import ingiza_csv
from .models import Harusi, Mchango, Mgeni, Ujumbe, safisha_simu

EAT = ZoneInfo("Africa/Dar_es_Salaam")
TMP_MEDIA = tempfile.mkdtemp()


def saa(h, d=date(2026, 11, 25)):
    return datetime(d.year, d.month, d.day, h, 0, tzinfo=EAT)


@override_settings(MEDIA_ROOT=TMP_MEDIA, CRON_SECRET="siri123")
class Msingi(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        buf = io.BytesIO()
        Image.new("RGB", (512, 768), "white").save(buf, "JPEG")
        self.h = Harusi(
            jina="Harusi ya Majaribio", mwenye_harusi="Richard Ngelula", tarehe_mwisho=date(2026, 11, 30),
            maelekezo_malipo="M-Pesa 0754 000 000",
        )
        self.h.kadi_template.save("t.jpg", ContentFile(buf.getvalue()), save=False)
        self.h.save()

    def mgeni(self, jina, simu="", ahadi=None, tumwa=True):
        m = Mgeni.objects.create(harusi=self.h, jina=jina, simu=simu, ahadi=ahadi)
        if tumwa:
            m.kadi_imetumwa = saa(9, date(2026, 11, 20))
            m.save()
        return m


class SimuTests(TestCase):
    def test_safisha_simu(self):
        self.assertEqual(safisha_simu("0754 123 456"), "255754123456")
        self.assertEqual(safisha_simu("+255 754-123-456"), "255754123456")
        self.assertEqual(safisha_simu("754123456"), "255754123456")
        self.assertEqual(safisha_simu("+420 600 000 001"), "420600000001")
        self.assertEqual(safisha_simu("00420600000001"), "420600000001")
        self.assertEqual(safisha_simu(""), "")


class TakwimuTests(Msingi):
    def test_jumla_na_salio(self):
        a = self.mgeni("A", "0711000001", ahadi=200_000)
        b = self.mgeni("B", "0711000002", ahadi=150_000)
        self.mgeni("C", "0711000003", tumwa=False)
        Mchango.objects.create(mgeni=a, kiasi=200_000)
        Mchango.objects.create(mgeni=b, kiasi=30_000)
        Mchango.objects.create(mgeni=b, kiasi=20_000)
        t = huduma.takwimu(self.h)
        self.assertEqual(t["wageni"], 3)
        self.assertEqual(t["wametumiwa"], 2)
        self.assertEqual(t["wamechangia"], 2)
        self.assertEqual(t["hawajachangia"], 1)
        self.assertEqual(t["jumla_michango"], 250_000)
        self.assertEqual(t["ahadi"], 350_000)
        self.assertEqual(t["salio_ahadi"], 100_000)

    def test_jumla_haizidishwi_na_jumbe(self):
        a = self.mgeni("A", "0711000001", ahadi=100_000)
        Mchango.objects.create(mgeni=a, kiasi=40_000)
        for _ in range(3):
            Ujumbe.objects.create(mgeni=a, aina="kikumbusho", hali="umetumwa")
        qs = self.h.wageni.wanaostahili_kikumbusho()
        self.assertEqual(qs.get().jumla_iliyotolewa, 40_000)


class VikumbushoTests(Msingi):
    def setUp(self):
        super().setUp()
        self.hajalipa = self.mgeni("Hajalipa", "0711000001")
        self.amelipa = self.mgeni("Amelipa", "0711000002")
        Mchango.objects.create(mgeni=self.amelipa, kiasi=50_000)
        self.sehemu = self.mgeni("Sehemu", "0711000003", ahadi=100_000)
        Mchango.objects.create(mgeni=self.sehemu, kiasi=40_000)
        self.mgeni("Hajatumiwa", "0711000004", tumwa=False)
        self.mgeni("Bila simu", "")
        m = self.mgeni("Amejitoa", "0711000005")
        m.amejitoa = True
        m.save()

    def tuma(self, h):
        with mock.patch("django.utils.timezone.now", return_value=h):
            return huduma.tuma_vikumbusho(self.h, sasa=h)

    def test_wanaostahili(self):
        majina = set(self.h.wageni.wanaostahili_kikumbusho().values_list("jina", flat=True))
        self.assertEqual(majina, {"Hajalipa", "Sehemu"})

    def test_mara_mbili_kwa_siku_tu(self):
        self.h.vikumbusho_kwa_siku = 2
        self.h.save()
        self.assertEqual(self.tuma(saa(9)).vimetumwa, 2)
        # kuitwa tena mara moja: pengo la saa halijafika
        self.assertEqual(self.tuma(saa(9) + timedelta(minutes=5)).vimetumwa, 0)
        self.assertEqual(self.tuma(saa(18)).vimetumwa, 2)
        # siku hiyo hiyo, ya tatu hairuhusiwi
        self.assertEqual(self.tuma(saa(19, ) + timedelta(minutes=59)).vimetumwa, 0)
        # kesho inaanza upya
        self.assertEqual(self.tuma(saa(9, date(2026, 11, 26))).vimetumwa, 2)
        self.assertEqual(Ujumbe.objects.filter(aina="kikumbusho").count(), 6)

    def test_chaguo_msingi_ni_mara_moja_kwa_siku(self):
        self.assertEqual(self.tuma(saa(9)).vimetumwa, 2)
        self.assertEqual(self.tuma(saa(18)).vimetumwa, 0)
        self.assertEqual(self.tuma(saa(9, date(2026, 11, 26))).vimetumwa, 2)

    def test_kikomo_cha_jumla(self):
        self.h.vikumbusho_jumla_max = 2
        self.h.save()
        for d in (25, 26, 27):
            self.tuma(saa(9, date(2026, 11, d)))
        self.assertEqual(Ujumbe.objects.filter(mgeni=self.hajalipa, aina="kikumbusho").count(), 2)

    def test_salio_linatumia_template_ya_salio(self):
        with mock.patch.object(whatsapp, "tuma_template", return_value=whatsapp.Matokeo(ok=True, jaribio=True)) as t:
            self.tuma(saa(9))
        aina = {c.args[0]: (c.args[1], c.args[2]) for c in t.call_args_list}
        self.assertEqual(aina["255711000001"][0], "kikumbusho")
        self.assertEqual(aina["255711000003"][0], "kikumbusho_salio")
        self.assertIn("60,000", aina["255711000003"][1])

    def test_hakuna_baada_ya_tarehe_ya_mwisho(self):
        r = self.tuma(saa(10, date(2026, 12, 1)))
        self.assertEqual(r.vimetumwa, 0)
        self.assertIn("umeisha", r.sababu)

    def test_hakuna_usiku(self):
        self.assertEqual(self.tuma(saa(22)).vimetumwa, 0)
        self.assertEqual(self.tuma(saa(6)).vimetumwa, 0)

    def test_vimezimwa(self):
        self.h.vikumbusho_vimewashwa = False
        self.h.save()
        self.assertEqual(self.tuma(saa(9)).vimetumwa, 0)

    def test_vilivyoshindwa_vinajaribiwa_tena(self):
        with mock.patch.object(whatsapp, "tuma_template", return_value=whatsapp.Matokeo(ok=False, kosa="x")):
            r = self.tuma(saa(9))
        self.assertEqual(r.vimeshindwa, 2)
        self.assertEqual(self.tuma(saa(9) + timedelta(minutes=10)).vimetumwa, 2)


class KadiTests(Msingi):
    def test_jaribio_halitii_alama(self):
        m = self.mgeni("Neema Mollel", "0711000001", tumwa=False)
        u = huduma.tuma_kadi(m)
        m.refresh_from_db()
        self.assertEqual(u.hali, "jaribio")
        self.assertIsNone(m.kadi_imetumwa)
        self.assertTrue(m.kadi)
        with m.kadi.open("rb") as f:
            self.assertEqual(Image.open(f).size, (512, 768))

    def test_kutuma_kweli_kunatia_alama(self):
        m = self.mgeni("Neema Mollel", "0711000001", tumwa=False)
        with mock.patch.object(whatsapp, "tuma_template", return_value=whatsapp.Matokeo(ok=True, wa_id="wamid.1")) as t:
            u = huduma.tuma_kadi(m)
        m.refresh_from_db()
        self.assertEqual(u.hali, "umetumwa")
        self.assertEqual(u.wa_id, "wamid.1")
        self.assertIsNotNone(m.kadi_imetumwa)
        self.assertTrue(t.call_args.kwargs["picha_url"].startswith("http"))

    def test_hatumiwi_bila_simu_au_akijitoa(self):
        self.assertIsNone(huduma.tuma_kadi(self.mgeni("A", "", tumwa=False)))
        m = self.mgeni("B", "0711000009", tumwa=False)
        m.amejitoa = True
        self.assertIsNone(huduma.tuma_kadi(m))

    @override_settings(WHATSAPP={**settings.WHATSAPP, "TOKEN": "t", "PHONE_NUMBER_ID": "1"})
    def test_payload_ya_whatsapp(self):
        resp = mock.Mock(ok=True, status_code=200)
        resp.json.return_value = {"messages": [{"id": "wamid.X"}]}
        with mock.patch("michango.whatsapp.requests.post", return_value=resp) as post:
            r = whatsapp.tuma_template("255711000001", "kadi", ["A", "B"], picha_url="https://x/k.jpg")
        self.assertTrue(r.ok)
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["to"], "255711000001")
        self.assertEqual(body["template"]["name"], "kadi_mchango")
        self.assertEqual(body["template"]["components"][0]["parameters"][0]["image"]["link"], "https://x/k.jpg")
        self.assertEqual([p["text"] for p in body["template"]["components"][1]["parameters"]], ["A", "B"])


class WebhookTests(Msingi):
    def test_hali_inasasishwa_na_kujitoa(self):
        m = self.mgeni("A", "0711000001")
        u = Ujumbe.objects.create(mgeni=m, aina="kadi", hali="umetumwa", wa_id="wamid.9")
        payload = {"entry": [{"changes": [{"value": {
            "statuses": [{"id": "wamid.9", "status": "read"}],
            "messages": [{"from": "255711000001", "type": "text", "text": {"body": " ACHA "}}],
        }}]}]}
        r = self.client.post(reverse("webhook_whatsapp"), json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        u.refresh_from_db()
        m.refresh_from_db()
        self.assertEqual(u.hali, "umesomwa")
        self.assertTrue(m.amejitoa)

    @override_settings(WHATSAPP={**settings.WHATSAPP, "APP_SECRET": "s", "VERIFY_TOKEN": "v"})
    def test_sahihi_na_uthibitisho(self):
        url = reverse("webhook_whatsapp")
        self.assertEqual(self.client.post(url, "{}", content_type="application/json").status_code, 403)
        sig = "sha256=" + hmac.new(b"s", b"{}", hashlib.sha256).hexdigest()
        r = self.client.post(url, "{}", content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sig)
        self.assertEqual(r.status_code, 200)
        r = self.client.get(url, {"hub.mode": "subscribe", "hub.verify_token": "v", "hub.challenge": "42"})
        self.assertEqual(r.content, b"42")
        r = self.client.get(url, {"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"})
        self.assertEqual(r.status_code, 403)


class CronTests(Msingi):
    def test_siri_inahitajika(self):
        url = reverse("cron_vikumbusho")
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.post(url, HTTP_AUTHORIZATION="Bearer kosa").status_code, 403)
        r = self.client.post(url, HTTP_AUTHORIZATION="Bearer siri123")
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.h.jina, r.json())


class IngizaTests(Msingi):
    def test_csv_na_kurudia_bila_kuongeza_pesa(self):
        data = "jina,simu,ahadi,ametoa\nJohn Mushi,0711000001,\"200,000\",200000\nAsha Said,0711000002,,\n".encode()
        r = ingiza_csv(self.h, data)
        self.assertEqual((r.wapya, r.michango), (2, 1))
        r = ingiza_csv(self.h, data)
        self.assertEqual((r.wapya, r.wamesasishwa, r.michango), (0, 2, 0))
        sam = Mgeni.objects.get(simu="255711000001")
        self.assertEqual(sam.ahadi, 200_000)
        self.assertEqual(sam.jumla, 200_000)

    def test_bila_vichwa_na_semicolon(self):
        r = ingiza_csv(self.h, "Juma Ali;0711000001\nMaria John;\n".encode())
        self.assertEqual(r.wapya, 2)


class KurasaTests(Msingi):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("mweka", password="nenosiri-zuri-123", is_staff=True)
        self.client.force_login(self.user)
        self.m = self.mgeni("Neema Mollel", "0711000003", ahadi=150_000)

    def test_kurasa_zinafunguka(self):
        for name in ["dashibodi", "wageni", "michango", "ingiza", "mchango_mpya", "mgeni_mpya"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for hali in ["hawajatumiwa", "wamechangia", "hawajachangia", "wana_salio", "bila_simu"]:
            self.assertEqual(self.client.get(reverse("wageni"), {"hali": hali, "q": "07"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("mgeni", args=[self.m.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("michango"), {"pakua": "csv"}).status_code, 200)

    def test_kuingiza_mchango_na_shukrani(self):
        r = self.client.post(reverse("mchango_mpya"), {
            "mgeni": self.m.pk, "kiasi": 50000, "tarehe": "2026-11-21", "njia": "mpesa", "tuma_shukrani": "on",
            "rudi": reverse("mgeni", args=[self.m.pk]),
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.m.jumla, 50_000)
        self.assertTrue(Ujumbe.objects.filter(mgeni=self.m, aina="shukrani").exists())
        r = self.client.get(reverse("dashibodi"))
        self.assertContains(r, "50,000")

    def test_namba_isirudiwe(self):
        r = self.client.post(reverse("mgeni_mpya"), {"jina": "Mwingine", "simu": "+255711000003"})
        self.assertContains(r, "tayari ni ya Neema Mollel")

    def test_lazima_uingie(self):
        self.client.logout()
        r = self.client.get(reverse("dashibodi"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])


class StorageTests(TestCase):
    @override_settings(SUPABASE_URL="https://abc.supabase.co")
    def test_link_ya_umma(self):
        from .storage import SupabaseStorage

        st = SupabaseStorage(bucket_name="kadi", access_key="k", secret_key="s", endpoint_url="https://abc.supabase.co/storage/v1/s3")
        self.assertEqual(st.url("kadi/h1/1-a b.jpg"), "https://abc.supabase.co/storage/v1/object/public/kadi/kadi/h1/1-a%20b.jpg")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class AnzishaTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("m", password="nenosiri-zuri-123", is_staff=True))
        self.data = {"jina": "Harusi ya Majaribio", "mwenye_harusi": "Bwana Harusi", "familia": "",
                     "tarehe_mwisho": "2026-11-30", "malipo": "M-Pesa 0711 000 000"}

    def test_fomu_inaonekana_na_inaanzisha(self):
        r = self.client.get(reverse("wageni"))
        self.assertContains(r, "Anzisha harusi")
        r = self.client.post(reverse("dashibodi"), self.data)
        self.assertRedirects(r, reverse("dashibodi"))
        h = Harusi.objects.get()
        self.assertEqual(h.mwenye_harusi, "Bwana Harusi")
        self.assertTrue(h.kadi_template.name)

    def test_kosa_la_storage_linaonyeshwa(self):
        with mock.patch("django.db.models.fields.files.FieldFile.save", side_effect=RuntimeError("NoSuchBucket: kadi")):
            r = self.client.post(reverse("dashibodi"), self.data)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "NoSuchBucket")
        self.assertContains(r, "Tengeneza bucket")
        self.assertFalse(Harusi.objects.exists())


@override_settings(WHATSAPP={**settings.WHATSAPP, "BACKEND": "baileys"})
class BaileysTests(Msingi):
    def setUp(self):
        super().setUp()
        self.m = self.mgeni("Neema Mollel", "0711000001", tumwa=False)

    def test_kadi_inaingia_foleni_bila_kutia_alama(self):
        u = huduma.tuma_kadi(self.m)
        self.m.refresh_from_db()
        self.assertEqual(u.hali, "kwenye_foleni")
        self.assertEqual(u.simu, "255711000001")
        self.assertIn("Neema Mollel", u.maandishi)
        self.assertIn("30.11.2026", u.maandishi)
        self.assertTrue(u.picha_url.startswith("http"))
        self.assertIsNone(self.m.kadi_imetumwa)  # worker ataweka baada ya kutuma kweli
        # kubofya tena hakuweki kadi ya pili kwenye foleni
        self.assertEqual(huduma.tuma_kadi(self.m).pk, u.pk)
        self.assertEqual(Ujumbe.objects.filter(mgeni=self.m).count(), 1)

    def test_maandishi_yanatofautiana(self):
        from . import jumbe

        params = ["Asha", "Richard", "30.11.2026", "M-Pesa 0711 000 000"]
        matoleo = {jumbe.tunga("kikumbusho", params) for _ in range(40)}
        self.assertGreater(len(matoleo), 5)
        for t in matoleo:
            self.assertIn("Asha", t)
            self.assertIn("ACHA", t)
            self.assertNotIn("http", t)  # hakuna link: zinaongeza alama ya spam
        self.assertIn("60,000", jumbe.tunga("kikumbusho_salio", ["A", "40,000", "R", "60,000", "30.11.2026", "M"]))

    def test_kikumbusho_hakirudiwi_kikiwa_bado_foleni(self):
        self.m.kadi_imetumwa = saa(9, date(2026, 11, 20))
        self.m.save()
        with mock.patch("django.utils.timezone.now", return_value=saa(9)):
            self.assertEqual(huduma.tuma_vikumbusho(self.h, sasa=saa(9)).vimetumwa, 1)
        with mock.patch("django.utils.timezone.now", return_value=saa(9, date(2026, 11, 26))):
            r = huduma.tuma_vikumbusho(self.h, sasa=saa(9, date(2026, 11, 26)))
        self.assertEqual(r.vimetumwa, 0)  # cha jana bado hakijatumwa (worker ilikuwa imezimwa)
        self.assertEqual(Ujumbe.objects.filter(mgeni=self.m, aina="kikumbusho").count(), 1)

    def test_afya(self):
        r = self.client.get(reverse("afya"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["whatsapp"], "baileys")
        self.assertFalse(r.json()["worker_hewani"])

    def test_ukurasa_wa_whatsapp(self):
        from .models import WhatsAppHali

        self.client.force_login(User.objects.create_user("w", password="nenosiri-zuri-123", is_staff=True))
        h = WhatsAppHali.pata()
        h.hali, h.qr = "inasubiri_qr", "2@abc,def"
        h.mapigo = timezone_now()
        h.save()
        r = self.client.get(reverse("whatsapp"))
        self.assertContains(r, 'data-qr="2@abc,def"')
        self.assertEqual(self.client.get(reverse("whatsapp"), {"json": 1}).json()["hali"], "inasubiri_qr")
        huduma.tuma_kadi(self.m)
        self.client.post(reverse("whatsapp"), {"kitendo": "sitisha"})
        self.assertTrue(WhatsAppHali.pata().imesitishwa)
        self.client.post(reverse("whatsapp"), {"kitendo": "futa_foleni"})
        self.assertEqual(Ujumbe.objects.get(mgeni=self.m).hali, "imeghairiwa")
        self.client.post(reverse("whatsapp"), {"kitendo": "endelea"})
        self.assertFalse(WhatsAppHali.pata().imesitishwa)
        r = self.client.get(reverse("dashibodi"))
        self.assertEqual(r.status_code, 200)


def timezone_now():
    from django.utils import timezone

    return timezone.now()


class MipangilioTests(Msingi):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_user("p", password="nenosiri-zuri-123", is_staff=True))

    def test_sehemu_zote_zinafunguka(self):
        for s in ("harusi", "kadi", "ujumbe"):
            r = self.client.get(reverse("mipangilio"), {"sehemu": s})
            self.assertEqual(r.status_code, 200, s)
        self.assertContains(self.client.get(reverse("mipangilio"), {"sehemu": "kadi"}), 'name="jina_fonti"')
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)

    def test_kubadili_muonekano_wa_kadi(self):
        m = self.mgeni("Asha Said", "0711000002", tumwa=False)
        from .kadi import tengeneza_kadi

        tengeneza_kadi(m)
        u = Ujumbe.objects.create(mgeni=m, aina="kadi", hali="kwenye_foleni")
        r = self.client.post(reverse("mipangilio"), {
            "sehemu": "kadi", "jina_fonti": "Cinzel-Bold.ttf", "jina_ukubwa": 36, "jina_rangi": "#7A5A12",
            "jina_x": "0.5", "jina_y": "0.46", "jina_upana_max": "0.7", "tengeneza_upya": "on",
        })
        self.assertEqual(r.status_code, 302)
        self.h.refresh_from_db()
        m.refresh_from_db()
        u.refresh_from_db()
        self.assertEqual((self.h.jina_fonti, self.h.jina_ukubwa, self.h.jina_rangi), ("Cinzel-Bold.ttf", 36, "#7a5a12"))
        self.assertFalse(m.kadi)  # itatengenezwa upya ikitumwa
        self.assertEqual(u.hali, "imeghairiwa")
        # kadi mpya inatengenezwa kwa fonti mpya bila kosa
        tengeneza_kadi(m)
        self.assertTrue(m.kadi)

    def test_thamani_mbaya_inakataliwa(self):
        r = self.client.post(reverse("mipangilio"), {
            "sehemu": "kadi", "jina_fonti": "Cinzel-Bold.ttf", "jina_ukubwa": 36, "jina_rangi": "nyekundu",
            "jina_x": "2", "jina_y": "0.46", "jina_upana_max": "0.7",
        })
        self.assertEqual(r.status_code, 200)
        self.h.refresh_from_db()
        self.assertNotEqual(self.h.jina_fonti, "Cinzel-Bold.ttf")

    def test_harusi_na_ujumbe(self):
        r = self.client.post(reverse("mipangilio"), {
            "sehemu": "harusi", "jina": "Harusi Mpya", "mwenye_harusi": "Richard", "familia": "",
            "tarehe_mwisho": "2026-12-05", "maelekezo_malipo": "M-Pesa 0711 000 000",
        })
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("mipangilio"), {"sehemu": "ujumbe", "vikumbusho_kwa_siku": 0, "vikumbusho_jumla_max": 2})
        self.h.refresh_from_db()
        self.assertEqual((self.h.jina, self.h.vikumbusho_kwa_siku, self.h.vikumbusho_vimewashwa), ("Harusi Mpya", 0, False))

    def test_fomu_ya_mchango_ina_orodha_ya_kutafuta(self):
        self.mgeni("Asha Said", "0711000002")
        r = self.client.get(reverse("mchango_mpya"))
        self.assertContains(r, 'id="orodha"')
        self.assertContains(r, "Asha Said")

    def test_chagua_wote_wa_kichujio(self):
        for i in range(3):
            self.mgeni(f"M{i}", f"071100001{i}", tumwa=False)
        r = self.client.post(reverse("wageni_kitendo"), {"kitendo": "alama_imetumwa", "wote_wa_kichujio": "1", "hali": "hawajatumiwa"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.h.wageni.filter(kadi_imetumwa__isnull=True).count(), 0)
