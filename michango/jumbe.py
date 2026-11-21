"""Maandishi ya jumbe za WhatsApp kwa Baileys.

Kila ujumbe una mitindo kadhaa inayochaguliwa kwa bahati nasibu. WhatsApp huona
ujumbe uleule kabisa ukitumwa kwa watu wengi kama dalili ya spam; jumbe
zinazotofautiana (pamoja na jina la mtu) zinapunguza hatari hiyo.

Vigezo (params) viko kwa mpangilio uleule wa templates za WhatsApp Cloud API
ili huduma.py itumie njia moja kwa mifumo yote miwili.
"""
import random

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


def tunga(template: str, params) -> str:
    return WATUNGAJI[template](list(params))
