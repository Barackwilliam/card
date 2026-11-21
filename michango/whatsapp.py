"""Mteja mdogo wa WhatsApp Cloud API (Meta).

Ujumbe unaoanzishwa na biashara lazima utumie "message templates" zilizoidhinishwa
na Meta. Maandishi ya templates za mfumo huu yako kwenye README.

Bila WHATSAPP_TOKEN mfumo uko kwenye hali ya majaribio: hakuna kinachotumwa,
lakini kila ujumbe unaandikwa kwenye kumbukumbu kwa hali "jaribio".
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

log = logging.getLogger("michango.whatsapp")


@dataclass
class Matokeo:
    ok: bool
    jaribio: bool = False
    wa_id: str = ""
    kosa: str = ""


def iko_hewani() -> bool:
    cfg = settings.WHATSAPP
    return bool(cfg["TOKEN"] and cfg["PHONE_NUMBER_ID"])


def tuma_template(simu: str, aina: str, params: list[str], picha_url: str | None = None) -> Matokeo:
    cfg = settings.WHATSAPP
    template = cfg["TEMPLATES"][aina]
    components = []
    if picha_url:
        components.append({"type": "header", "parameters": [{"type": "image", "image": {"link": picha_url}}]})
    if params:
        components.append(
            {"type": "body", "parameters": [{"type": "text", "text": str(p)} for p in params]}
        )
    payload = {
        "messaging_product": "whatsapp",
        "to": simu,
        "type": "template",
        "template": {"name": template, "language": {"code": cfg["LANGUAGE"]}, "components": components},
    }

    if not iko_hewani():
        log.info("[JARIBIO] %s -> %s %s", template, simu, params)
        return Matokeo(ok=True, jaribio=True)

    url = f"https://graph.facebook.com/{cfg['API_VERSION']}/{cfg['PHONE_NUMBER_ID']}/messages"
    try:
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {cfg['TOKEN']}"}, timeout=20)
    except requests.RequestException as e:
        return Matokeo(ok=False, kosa=f"Mtandao: {e}")
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.ok and data.get("messages"):
        return Matokeo(ok=True, wa_id=data["messages"][0].get("id", ""))
    err = data.get("error", {})
    return Matokeo(ok=False, kosa=f"{r.status_code}: {err.get('message') or r.text[:300]}")


def sahihi_ni_halali(body: bytes, signature_header: str) -> bool:
    """Hakiki X-Hub-Signature-256 ya webhook (kama WHATSAPP_APP_SECRET imewekwa)."""
    secret = settings.WHATSAPP["APP_SECRET"]
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))
