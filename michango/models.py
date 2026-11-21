import re

from django.conf import settings
from django.db import models
from django.db.models import OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


def safisha_simu(simu: str) -> str:
    """Badilisha namba kuwa muundo wa kimataifa bila '+', mfano 0754123456 -> 255754123456."""
    if not simu:
        return ""
    s = simu.strip()
    plus = s.startswith("+") or s.startswith("00")
    digits = re.sub(r"\D", "", s)
    if s.startswith("00"):
        digits = digits[2:]
    if not plus:
        if digits.startswith("0") and len(digits) == 10:  # 07xx / 06xx ya Tanzania
            digits = "255" + digits[1:]
        elif len(digits) == 9 and digits[0] in "67":  # 754123456
            digits = "255" + digits
    return digits


class Harusi(models.Model):
    FONTI = [
        ("GreatVibes-Regular.ttf", "Mwandiko (Great Vibes)"),
        ("Montserrat-Bold.ttf", "Montserrat nzito"),
    ]

    jina = models.CharField("Jina la shughuli", max_length=200, help_text="Mfano: Harusi ya Richard Ngelula")
    mwenye_harusi = models.CharField("Bwana/Bibi harusi", max_length=120, help_text="Mfano: Richard Ngelula")
    familia = models.CharField(max_length=200, blank=True, help_text="Mfano: Familia ya Bw. & Bi. Michael Mchome")
    tarehe_mwisho = models.DateField("Mwisho wa kuchangia")
    maelekezo_malipo = models.CharField(
        "Maelekezo ya malipo",
        max_length=300,
        help_text="Yanaingia kwenye ujumbe. Mfano: M-Pesa 0754 000 000 (Michael Mchome)",
    )

    kadi_template = models.ImageField("Picha ya kadi (bila jina)", upload_to="templates/")
    jina_x = models.FloatField("Jina: nafasi ya mlalo (0-1)", default=0.499)
    jina_y = models.FloatField("Jina: mstari wa chini wa herufi (0-1)", default=0.4538)
    jina_ukubwa = models.PositiveSmallIntegerField("Jina: ukubwa (kwa upana wa 1024px)", default=50)
    jina_upana_max = models.FloatField("Jina: upana mkubwa zaidi (0-1)", default=0.72)
    jina_rangi = models.CharField("Jina: rangi", max_length=7, default="#0d1b4d")
    jina_fonti = models.CharField("Jina: aina ya herufi", max_length=60, choices=FONTI, default=FONTI[0][0])

    vikumbusho_vimewashwa = models.BooleanField("Tuma vikumbusho", default=True)
    vikumbusho_kwa_siku = models.PositiveSmallIntegerField(
        "Vikumbusho kwa siku", default=2, help_text="Mgeni mmoja hapokei zaidi ya idadi hii kwa siku."
    )
    shukrani_zimewashwa = models.BooleanField("Tuma shukrani mchango ukipokelewa", default=True)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Harusi"
        verbose_name_plural = "Harusi"

    def __str__(self):
        return self.jina

    @classmethod
    def ya_sasa(cls):
        return cls.objects.order_by("-created").first()


class MgeniQuerySet(models.QuerySet):
    def na_jumla(self):
        # Subquery (si join) ili jumla isizidishwe ikichanganywa na annotate nyingine
        sub = (
            Mchango.objects.filter(mgeni=OuterRef("pk"))
            .values("mgeni")
            .annotate(s=Sum("kiasi"))
            .values("s")
        )
        return self.annotate(jumla_iliyotolewa=Coalesce(Subquery(sub), 0))

    def wametumiwa(self):
        return self.filter(kadi_imetumwa__isnull=False)

    def wamechangia(self):
        return self.filter(michango__isnull=False).distinct()

    def hawajachangia(self):
        return self.filter(michango__isnull=True)

    def wanaostahili_kikumbusho(self):
        """Wametumiwa kadi, wana simu, hawajajitoa, na bado hawajamaliza.

        "Hawajamaliza" = hawajatoa chochote, au wameahidi kiasi na bado wana salio.
        """
        qs = self.na_jumla().filter(kadi_imetumwa__isnull=False, amejitoa=False).exclude(simu="")
        return qs.filter(Q(jumla_iliyotolewa=0) | Q(ahadi__gt=models.F("jumla_iliyotolewa")))


class Mgeni(models.Model):
    harusi = models.ForeignKey(Harusi, on_delete=models.CASCADE, related_name="wageni")
    jina = models.CharField(max_length=150)
    simu = models.CharField(max_length=20, blank=True, help_text="Namba ya WhatsApp. Mfano 0754123456")
    ahadi = models.PositiveIntegerField("Ahadi (TSh)", null=True, blank=True)
    kadi = models.ImageField(upload_to="kadi/", blank=True)
    kadi_imetumwa = models.DateTimeField("Kadi ilitumwa", null=True, blank=True)
    amejitoa = models.BooleanField("Hataki ujumbe", default=False, help_text="Ameomba asitumiwe ujumbe tena.")
    maelezo = models.CharField(max_length=300, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = MgeniQuerySet.as_manager()

    class Meta:
        verbose_name = "Mgeni"
        verbose_name_plural = "Wageni"
        ordering = ["jina"]
        constraints = [
            models.UniqueConstraint(
                fields=["harusi", "simu"], condition=~Q(simu=""), name="simu_moja_kwa_harusi"
            )
        ]

    def __str__(self):
        return self.jina

    def save(self, *args, **kwargs):
        self.simu = safisha_simu(self.simu)
        super().save(*args, **kwargs)

    @property
    def jumla(self):
        val = getattr(self, "jumla_iliyotolewa", None)
        if val is None:
            val = self.michango.aggregate(s=Sum("kiasi"))["s"] or 0
        return val

    @property
    def salio(self):
        if not self.ahadi:
            return 0
        return max(self.ahadi - self.jumla, 0)

    @property
    def hali(self):
        if self.jumla and (not self.ahadi or self.jumla >= self.ahadi):
            return "amemaliza"
        if self.jumla:
            return "sehemu"
        if self.kadi_imetumwa:
            return "anasubiriwa"
        return "hajatumiwa"


class Mchango(models.Model):
    NJIA = [
        ("mpesa", "M-Pesa"),
        ("mixx", "Mixx by Yas (Tigo Pesa)"),
        ("airtel", "Airtel Money"),
        ("halopesa", "HaloPesa"),
        ("benki", "Benki"),
        ("taslimu", "Taslimu"),
        ("nyingine", "Nyingine"),
    ]

    mgeni = models.ForeignKey(Mgeni, on_delete=models.CASCADE, related_name="michango")
    kiasi = models.PositiveIntegerField("Kiasi (TSh)")
    tarehe = models.DateField(default=timezone.localdate)
    njia = models.CharField(max_length=20, choices=NJIA, default="mpesa")
    kumbukumbu = models.CharField("Namba ya muamala", max_length=60, blank=True)
    maelezo = models.CharField(max_length=300, blank=True)
    aliyeingiza = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mchango"
        verbose_name_plural = "Michango"
        ordering = ["-tarehe", "-created"]

    def __str__(self):
        return f"{self.mgeni} - TSh {self.kiasi:,}"


class Ujumbe(models.Model):
    AINA = [("kadi", "Kadi"), ("kikumbusho", "Kikumbusho"), ("shukrani", "Shukrani")]
    HALI = [
        ("jaribio", "Jaribio (haukutumwa)"),
        ("umetumwa", "Umetumwa"),
        ("umefika", "Umefika"),
        ("umesomwa", "Umesomwa"),
        ("umeshindwa", "Umeshindwa"),
    ]

    mgeni = models.ForeignKey(Mgeni, on_delete=models.CASCADE, related_name="jumbe")
    aina = models.CharField(max_length=20, choices=AINA)
    hali = models.CharField(max_length=20, choices=HALI)
    wa_id = models.CharField("WhatsApp message id", max_length=120, blank=True, db_index=True)
    kosa = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ujumbe"
        verbose_name_plural = "Jumbe"
        ordering = ["-created"]
        indexes = [models.Index(fields=["mgeni", "aina", "created"])]

    def __str__(self):
        return f"{self.get_aina_display()} kwa {self.mgeni} ({self.get_hali_display()})"
