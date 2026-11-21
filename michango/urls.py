from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashibodi, name="dashibodi"),
    path("wageni/", views.wageni, name="wageni"),
    path("wageni/kitendo/", views.wageni_kitendo, name="wageni_kitendo"),
    path("wageni/mpya/", views.mgeni_fomu, name="mgeni_mpya"),
    path("wageni/ingiza/", views.ingiza, name="ingiza"),
    path("wageni/<int:pk>/", views.mgeni, name="mgeni"),
    path("wageni/<int:pk>/hariri/", views.mgeni_fomu, name="mgeni_hariri"),
    path("wageni/<int:pk>/kitendo/", views.mgeni_kitendo, name="mgeni_kitendo"),
    path("michango/", views.michango, name="michango"),
    path("michango/mpya/", views.mchango_mpya, name="mchango_mpya"),
    path("michango/<int:pk>/futa/", views.mchango_futa, name="mchango_futa"),
    path("vikumbusho/tuma/", views.tuma_vikumbusho_sasa, name="tuma_vikumbusho"),
    path("whatsapp/", views.whatsapp_hali, name="whatsapp"),
    path("mipangilio/", views.mipangilio, name="mipangilio"),
    path("cron/vikumbusho/", views.cron_vikumbusho, name="cron_vikumbusho"),
    path("afya/", views.afya, name="afya"),
    path("webhook/whatsapp/", views.webhook_whatsapp, name="webhook_whatsapp"),
]
