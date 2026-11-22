"""Maandishi ya jumbe za WhatsApp kwa Baileys.

Kila ujumbe una mitindo kadhaa inayochaguliwa kwa bahati nasibu. WhatsApp huona
ujumbe uleule kabisa ukitumwa kwa watu wengi kama dalili ya spam; jumbe
zinazotofautiana (pamoja na jina la mtu) zinapunguza hatari hiyo.

Vigezo (params) viko kwa mpangilio uleule wa templates za WhatsApp Cloud API
ili huduma.py itumie njia moja kwa mifumo yote miwili.
"""
import random
import re

SALAMU = ["Habari {jina}", "Habari yako {jina}", "Salaam {jina}", "Habari za leo {jina}"]
SHUKRANI_MWISHO = ["Asante sana.", "Asante na Mungu akubariki.", "Tunashukuru sana.", "Mungu akubariki."]
ACHA = "(Jibu ACHA kama hutaki kupokea vikumbusho.)"


def _chagua(rng, items):
    return rng.choice(items)


def kadi(params, rng=random):
    jina, mwenye, tarehe, malipo = params
    salamu = _chagua(rng, SALAMU).format(jina=jina)
    mwili = _chagua(rng, [
        f"familia inapenda kukujulisha kuhusu harusi ya mpendwa wetu {mwenye}. Tafadhali pokea kadi yako ya mchango.",
        f"tunayo furaha kukujulisha kuhusu harusi ya kijana wetu {mwenye}. Hii ni kadi yako ya mchango.",
        f"familia inakukaribisha kuchangia harusi ya mpendwa wetu {mwenye}. Kadi yako iko hapa.",
    ])
    ombi = _chagua(rng, [
        f"Tunaomba mchango wako kabla ya tarehe {tarehe}.",
        f"Mchango wako unakaribishwa kabla ya {tarehe}.",
        f"Tafadhali tufikishie mchango wako kabla ya {tarehe}.",
    ])
    return f"{salamu}, {mwili}\n\n{ombi}\nMalipo: {malipo}\n\n{_chagua(rng, SHUKRANI_MWISHO)}"


def kikumbusho(params, rng=random):
    jina, mwenye, tarehe, malipo = params
    salamu = _chagua(rng, SALAMU).format(jina=jina)
    mwili = _chagua(rng, [
        f"tunakukumbusha kwa upendo kuhusu mchango wa harusi ya {mwenye}.",
        f"ni kikumbusho kidogo tu kuhusu mchango wa harusi ya {mwenye}.",
        f"tunakukumbusha kwa heshima mchango wa harusi ya mpendwa wetu {mwenye}.",
    ])
    mwisho = _chagua(rng, [f"Mwisho wa kuchangia ni {tarehe}.", f"Tarehe ya mwisho ni {tarehe}.", f"Michango inapokelewa mpaka {tarehe}."])
    puuza = _chagua(rng, [
        "Kama umeshachangia, tafadhali puuza ujumbe huu.",
        "Kama tayari umechangia, asante sana na puuza ujumbe huu.",
    ])
    return f"{salamu}, {mwili} {mwisho}\nMalipo: {malipo}\n\n{puuza} {_chagua(rng, SHUKRANI_MWISHO)}\n{ACHA}"


def kikumbusho_salio(params, rng=random):
    jina, jumla, mwenye, salio, tarehe, malipo = params
    salamu = _chagua(rng, SALAMU).format(jina=jina)
    asante = _chagua(rng, [
        f"asante kwa mchango wako wa TSh {jumla} kwa harusi ya {mwenye}.",
        f"tunashukuru kwa TSh {jumla} ulizochangia kwa harusi ya {mwenye}.",
    ])
    salio_txt = _chagua(rng, [
        f"Salio la ahadi yako ni TSh {salio}, kabla ya {tarehe}.",
        f"Bado TSh {salio} kukamilisha ahadi yako. Mwisho ni {tarehe}.",
    ])
    return f"{salamu}, {asante} {salio_txt}\nMalipo: {malipo}\n\n{_chagua(rng, SHUKRANI_MWISHO)}\n{ACHA}"


def shukrani(params, rng=random):
    jina, kiasi, mwenye, jumla = params
    mwanzo = _chagua(rng, [f"Asante sana {jina}!", f"Tunakushukuru {jina}!", f"Asante {jina}!"])
    mwili = f"Tumepokea mchango wako wa TSh {kiasi} kwa harusi ya {mwenye}."
    if jumla != kiasi:
        mwili += f" Jumla uliyochangia ni TSh {jumla}."
    return f"{mwanzo} {mwili} {_chagua(rng, ['Mungu akubariki.', 'Mungu akubariki sana.', 'Tunathamini sana.'])}"


WATUNGAJI = {"kadi": kadi, "kikumbusho": kikumbusho, "kikumbusho_salio": kikumbusho_salio, "shukrani": shukrani}


# ---------- Ujumbe ulioandikwa na mtumiaji ----------

# Vishika-nafasi vinavyoruhusiwa kwa kila ujumbe, kwa mpangilio wa params
VISHIKA = {
    "kadi": ["jina", "bwana_harusi", "tarehe", "malipo"],
    "kikumbusho": ["jina", "bwana_harusi", "tarehe", "malipo"],
    "kikumbusho_salio": ["jina", "ametoa", "bwana_harusi", "salio", "tarehe", "malipo"],
    "shukrani": ["jina", "kiasi", "bwana_harusi", "jumla"],
}

# {JINA} = jina kwa herufi kubwa (linatokana na "jina"), linaruhusiwa kwenye ujumbe wote
ZIADA = ["JINA"]

MAELEZO_YA_VISHIKA = {
    "jina": "Jina la mgeni",
    "JINA": "JINA (herufi kubwa)",
    "bwana_harusi": "Bwana harusi",
    "tarehe": "Tarehe ya mwisho",
    "malipo": "Namba ya malipo",
    "salio": "Salio la ahadi",
    "ametoa": "Alichokwisha toa",
    "kiasi": "Kiasi alichotoa sasa",
    "jumla": "Jumla aliyotoa",
}

# Mfano unaoonyeshwa mtumiaji akianza kuandika (si lazima atumie)
MFANO = {
    "kadi": "Habari {jina}, familia inapenda kukujulisha kuhusu harusi ya mpendwa wetu {bwana_harusi}. Tafadhali pokea kadi yako ya mchango.\n\nTunaomba mchango wako kabla ya tarehe {tarehe}.\nMalipo: {malipo}\n\nAsante na Mungu akubariki.",
    "kikumbusho": "Habari {jina}, tunakukumbusha kwa upendo kuhusu mchango wa harusi ya {bwana_harusi}. Mwisho wa kuchangia ni {tarehe}.\nMalipo: {malipo}\n\nKama umeshachangia, tafadhali puuza ujumbe huu. Asante sana.",
    "kikumbusho_salio": "Habari {jina}, asante kwa mchango wako wa TSh {ametoa} kwa harusi ya {bwana_harusi}. Salio la ahadi yako ni TSh {salio}, kabla ya {tarehe}.\nMalipo: {malipo}\n\nMungu akubariki.",
    "shukrani": "Asante sana {jina}! Tumepokea mchango wako wa TSh {kiasi} kwa harusi ya {bwana_harusi}. Jumla uliyochangia ni TSh {jumla}. Mungu akubariki.",
}

_KITENGANISHI = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)
_KISHIKA = re.compile(r"\{(\w+)\}")


def matoleo(maandishi: str) -> list[str]:
    """Gawa maandishi kuwa matoleo (yaliyotenganishwa na mstari wa ---)."""
    return [t.strip() for t in _KITENGANISHI.split(maandishi or "") if t.strip()]


def vishika_vya(template: str) -> list[str]:
    v = VISHIKA[template]
    return v[:1] + ZIADA + v[1:]


def vishika_visivyojulikana(maandishi: str, template: str) -> list[str]:
    ruhusiwa = set(vishika_vya(template))
    return sorted({k for k in _KISHIKA.findall(maandishi or "") if k not in ruhusiwa})


def jaza(maandishi: str, template: str, params) -> str:
    thamani = dict(zip(VISHIKA[template], [str(p) for p in params]))
    thamani["JINA"] = thamani.get("jina", "").upper()
    return _KISHIKA.sub(lambda m: thamani.get(m.group(1), m.group(0)), maandishi)


def tunga(template: str, params, maalum: str = "", rng=random) -> str:
    """Tunga ujumbe: wa mtumiaji (kama upo, toleo moja kwa bahati nasibu) au wa kawaida."""
    params = list(params)
    chaguo = matoleo(maalum)
    if not chaguo:
        return WATUNGAJI[template](params, rng)
    maandishi = jaza(rng.choice(chaguo), template, params)
    # Kinga: vikumbusho lazima vimwonyeshe mtu jinsi ya kusitisha
    if template.startswith("kikumbusho") and "acha" not in maandishi.lower():
        maandishi += "\n" + ACHA
    return maandishi
