from django.contrib import admin

from .models import Harusi, Mchango, Mgeni, Ujumbe


@admin.register(Harusi)
class HarusiAdmin(admin.ModelAdmin):
    list_display = ["jina", "mwenye_harusi", "tarehe_mwisho", "vikumbusho_vimewashwa", "vikumbusho_kwa_siku"]
    fieldsets = [
        (None, {"fields": ["jina", "mwenye_harusi", "familia", "tarehe_mwisho", "maelekezo_malipo"]}),
        ("Kadi", {"fields": ["kadi_template", "jina_x", "jina_y", "jina_ukubwa", "jina_upana_max", "jina_rangi", "jina_fonti"]}),
        ("Ujumbe wa WhatsApp", {"fields": ["vikumbusho_vimewashwa", "vikumbusho_kwa_siku", "shukrani_zimewashwa"]}),
    ]


class MchangoInline(admin.TabularInline):
    model = Mchango
    extra = 0
    fields = ["kiasi", "tarehe", "njia", "kumbukumbu", "maelezo"]


@admin.register(Mgeni)
class MgeniAdmin(admin.ModelAdmin):
    list_display = ["jina", "simu", "ahadi", "kadi_imetumwa", "amejitoa"]
    list_filter = ["harusi", "amejitoa", ("kadi_imetumwa", admin.EmptyFieldListFilter)]
    search_fields = ["jina", "simu"]
    inlines = [MchangoInline]


@admin.register(Mchango)
class MchangoAdmin(admin.ModelAdmin):
    list_display = ["mgeni", "kiasi", "tarehe", "njia", "kumbukumbu"]
    list_filter = ["njia", "tarehe"]
    search_fields = ["mgeni__jina", "kumbukumbu"]
    autocomplete_fields = ["mgeni"]


@admin.register(Ujumbe)
class UjumbeAdmin(admin.ModelAdmin):
    list_display = ["mgeni", "aina", "hali", "created", "kosa"]
    list_filter = ["aina", "hali"]
    search_fields = ["mgeni__jina", "wa_id"]
    readonly_fields = [f.name for f in Ujumbe._meta.fields]
