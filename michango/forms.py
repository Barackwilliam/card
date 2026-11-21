from django import forms

from .models import Mchango, Mgeni, safisha_simu


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
