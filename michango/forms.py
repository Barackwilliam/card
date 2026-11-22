import re

from django import forms

from .models import Harusi, Mchango, Mgeni, safisha_simu


class MgeniForm(forms.ModelForm):
    class Meta:
        model = Mgeni
        fields = ["jina", "simu", "ahadi", "maelezo", "amejitoa"]
        widgets = {"simu": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "0754 123 456"})}

    def __init__(self, *args, harusi=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.harusi = harusi or getattr(self.instance, "harusi", None)

    def clean_simu(self):
        simu = safisha_simu(self.cleaned_data.get("simu", ""))
        if simu and len(simu) < 10:
            raise forms.ValidationError("Namba ya simu si kamili.")
        if simu and self.harusi:
            qs = Mgeni.objects.filter(harusi=self.harusi, simu=simu).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"Namba hii tayari ni ya {qs.first().jina}.")
        return simu


class MchangoForm(forms.ModelForm):
    tuma_shukrani = forms.BooleanField(
        label="Mtumie ujumbe wa shukrani WhatsApp", required=False, initial=True
    )

    class Meta:
        model = Mchango
        fields = ["mgeni", "kiasi", "tarehe", "njia", "kumbukumbu", "maelezo"]
        widgets = {
            "tarehe": forms.DateInput(attrs={"type": "date"}),
            "kiasi": forms.NumberInput(attrs={"inputmode": "numeric", "min": 1, "step": 1000, "placeholder": "50000"}),
        }

    def __init__(self, *args, harusi=None, mgeni=None, **kwargs):
        super().__init__(*args, **kwargs)
        if harusi:
            self.fields["mgeni"].queryset = harusi.wageni.order_by("jina")
        if mgeni:
            self.fields["mgeni"].initial = mgeni
            self.fields["mgeni"].widget = forms.HiddenInput()


class IngizaForm(forms.Form):
    faili = forms.FileField(
        label="Faili la CSV",
        help_text="Safu: jina, simu, ahadi, ametoa, maelezo (ni jina tu la lazima). Unaweza kuhifadhi kutoka Excel kama CSV.",
    )


class AnzishaForm(forms.Form):
    jina = forms.CharField(label="Jina la shughuli", initial="Harusi ya Richard Ngelula", max_length=200)
    mwenye_harusi = forms.CharField(label="Bwana harusi", initial="Richard Ngelula", max_length=120)
    familia = forms.CharField(label="Familia", initial="Familia ya Bw. & Bi. Michael Mchome wa Korogwe", max_length=200, required=False)
    tarehe_mwisho = forms.DateField(label="Mwisho wa kuchangia", initial="2026-11-30", widget=forms.DateInput(attrs={"type": "date"}))
    malipo = forms.CharField(
        label="Maelekezo ya malipo", max_length=300, help_text="Yanaingia kwenye ujumbe wa WhatsApp. Mfano: M-Pesa 0754 xxx xxx (Michael Mchome)"
    )


class HarusiForm(forms.ModelForm):
    class Meta:
        model = Harusi
        fields = ["jina", "mwenye_harusi", "familia", "tarehe_mwisho", "maelekezo_malipo"]
        labels = {
            "jina": "Jina la shughuli",
            "mwenye_harusi": "Bwana harusi",
            "familia": "Familia",
            "tarehe_mwisho": "Mwisho wa kuchangia",
            "maelekezo_malipo": "Namba ya kupokea michango",
        }
        help_texts = {
            "jina": "Linaonekana juu ya mfumo.",
            "mwenye_harusi": "Linaingia kwenye ujumbe wa WhatsApp.",
            "maelekezo_malipo": "Inaingia mahali pa {malipo} kwenye ujumbe. Unaweza kuandika mistari kadhaa (namba, jina, mtandao).",
        }
        widgets = {
            "tarehe_mwisho": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "maelekezo_malipo": forms.Textarea(attrs={"rows": 6, "placeholder": "📱 M-PESA\nNamba: 07xx xxx xxx\nJina: ..."}),
        }

    def clean_maelekezo_malipo(self):
        return _mistari_safi(self.cleaned_data["maelekezo_malipo"])


def _kagua_maandishi(maandishi, template):
    from . import jumbe

    maandishi = (maandishi or "").replace("\r\n", "\n").replace("\r", "\n")

    mbaya = jumbe.vishika_visivyojulikana(maandishi, template)
    if mbaya:
        ruhusiwa = ", ".join("{" + v + "}" for v in jumbe.vishika_vya(template))
        raise forms.ValidationError(
            f"Hivi havijulikani: {', '.join('{' + m + '}' for m in mbaya)}. Unaweza kutumia: {ruhusiwa}."
        )
    kikomo = 950 if template == "kadi" else 3000  # WhatsApp: maelezo ya picha yasizidi herufi 1024
    for t in jumbe.matoleo(maandishi):
        if len(t) > kikomo:
            raise forms.ValidationError(f"Ujumbe ni mrefu sana (herufi {len(t)}). Usizidi herufi {kikomo}.")
    return maandishi.strip()


def _mistari_safi(t):
    return (t or "").replace("\r\n", "\n").replace("\r", "\n").strip()


class UjumbeForm(forms.ModelForm):
    class Meta:
        model = Harusi
        fields = [
            "vikumbusho_vimewashwa", "vikumbusho_kwa_siku", "vikumbusho_jumla_max", "shukrani_zimewashwa",
            "ujumbe_kadi", "ujumbe_kikumbusho", "ujumbe_salio", "ujumbe_shukrani",
        ]
        labels = {
            "vikumbusho_vimewashwa": "Tuma vikumbusho kwa ambao hawajachangia",
            "vikumbusho_kwa_siku": "Mara ngapi kwa siku",
            "vikumbusho_jumla_max": "Vikumbusho visizidi (kwa mtu mmoja)",
            "shukrani_zimewashwa": "Tuma ujumbe wa shukrani mtu akichangia",
        }
        help_texts = {
            "vikumbusho_kwa_siku": "Tunashauri 1. Kumtumia mtu mara nyingi kunaweza kufanya namba ifungiwe.",
            "vikumbusho_jumla_max": "Baada ya hapo mtu hakumbushwi tena.",
        }
        widgets = {
            "vikumbusho_kwa_siku": forms.Select(choices=[(0, "Hapana"), (1, "Mara 1 (inashauriwa)"), (2, "Mara 2")]),
            "vikumbusho_jumla_max": forms.Select(choices=[(n, f"Mara {n}") for n in (1, 2, 3, 4, 5, 6)]),
        }

    def clean_ujumbe_kadi(self):
        return _kagua_maandishi(self.cleaned_data["ujumbe_kadi"], "kadi")

    def clean_ujumbe_kikumbusho(self):
        return _kagua_maandishi(self.cleaned_data["ujumbe_kikumbusho"], "kikumbusho")

    def clean_ujumbe_salio(self):
        return _kagua_maandishi(self.cleaned_data["ujumbe_salio"], "kikumbusho_salio")

    def clean_ujumbe_shukrani(self):
        return _kagua_maandishi(self.cleaned_data["ujumbe_shukrani"], "shukrani")


class KumbushaForm(forms.Form):
    KUNDI = [("hawajachangia", "Hawajachangia"), ("wana_salio", "Wenye salio la ahadi")]
    kundi = forms.ChoiceField(choices=KUNDI, initial="hawajachangia", widget=forms.RadioSelect)
    maandishi = forms.CharField(widget=forms.Textarea, required=True)
    hifadhi = forms.BooleanField(required=False, initial=True)

    def clean(self):
        d = super().clean()
        if d.get("maandishi") and d.get("kundi"):
            template = "kikumbusho_salio" if d["kundi"] == "wana_salio" else "kikumbusho"
            try:
                d["maandishi"] = _kagua_maandishi(d["maandishi"], template)
            except forms.ValidationError as e:
                self.add_error("maandishi", e)
        return d


class KadiForm(forms.ModelForm):
    tengeneza_upya = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = Harusi
        fields = ["jina_fonti", "jina_ukubwa", "jina_rangi", "jina_x", "jina_y", "jina_upana_max"]

    def clean_jina_rangi(self):
        v = self.cleaned_data["jina_rangi"]
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v or ""):
            raise forms.ValidationError("Rangi si sahihi.")
        return v.lower()

    def clean(self):
        d = super().clean()
        for f, lo, hi in (("jina_x", 0, 1), ("jina_y", 0, 1), ("jina_upana_max", 0.1, 1)):
            if f in d and d[f] is not None and not (lo <= d[f] <= hi):
                self.add_error(f, "Thamani iko nje ya kadi.")
        if d.get("jina_ukubwa") and not (12 <= d["jina_ukubwa"] <= 140):
            self.add_error("jina_ukubwa", "Ukubwa uwe kati ya 12 na 140.")
        return d


class PichaYaKadiForm(forms.Form):
    picha = forms.ImageField(label="Picha mpya ya kadi (bila jina)")
