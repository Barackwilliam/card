"""Kuingiza wageni wengi kwa mara moja kutoka faili la CSV (kutoka Excel au Google Sheets)."""
import csv
import io
import re
from dataclasses import dataclass, field

from django.db import transaction

from .models import Mchango, Mgeni, safisha_simu

VICHWA = {
    "jina": {"jina", "name", "majina"},
    "simu": {"simu", "namba", "phone", "number", "namba ya simu"},
    "ahadi": {"ahadi", "pledge", "ameahidi"},
    "ametoa": {"ametoa", "amelipa", "paid", "mchango", "kilicholipwa"},
    "maelezo": {"maelezo", "notes", "maoni"},
}


def _kiasi(val: str) -> int | None:
    digits = re.sub(r"[^\d]", "", val or "")
    return int(digits) if digits else None


@dataclass
class MatokeoUingizaji:
    wapya: int = 0
    wamesasishwa: int = 0
    michango: int = 0
    makosa: list = field(default_factory=list)


@transaction.atomic
def ingiza_csv(harusi, faili_bytes: bytes, aliyeingiza=None) -> MatokeoUingizaji:
    text = faili_bytes.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    res = MatokeoUingizaji()
    if not rows:
        res.makosa.append("Faili ni tupu.")
        return res

    head = [c.strip().lower() for c in rows[0]]
    cols = {}
    for key, names in VICHWA.items():
        for i, h in enumerate(head):
            if h in names:
                cols[key] = i
                break
    if "jina" in cols:
        data = rows[1:]
        start = 2
    else:  # hakuna kichwa: jina, simu, ahadi, ametoa
        cols = {"jina": 0, "simu": 1, "ahadi": 2, "ametoa": 3}
        data = rows
        start = 1

    def get(row, key):
        i = cols.get(key)
        return row[i].strip() if i is not None and i < len(row) else ""

    for n, row in enumerate(data, start=start):
        jina = get(row, "jina")
        if not jina:
            continue
        simu = safisha_simu(get(row, "simu"))
        ahadi = _kiasi(get(row, "ahadi"))
        ametoa = _kiasi(get(row, "ametoa"))
        maelezo = get(row, "maelezo")[:300]
        mgeni = None
        if simu:
            mgeni = harusi.wageni.filter(simu=simu).first()
        if not mgeni:
            mgeni = harusi.wageni.filter(jina__iexact=jina, simu=simu).first()
        if mgeni:
            mgeni.jina = jina
            if ahadi:
                mgeni.ahadi = ahadi
            if maelezo:
                mgeni.maelezo = maelezo
            mgeni.save()
            res.wamesasishwa += 1
        else:
            mgeni = Mgeni.objects.create(harusi=harusi, jina=jina, simu=simu, ahadi=ahadi, maelezo=maelezo)
            res.wapya += 1
        # "ametoa" inaongezwa tu kama mgeni hana mchango wowote bado, ili kuingiza
        # faili lilelile mara mbili kusiongeze pesa mara mbili.
        if ametoa and not mgeni.michango.exists():
            Mchango.objects.create(
                mgeni=mgeni, kiasi=ametoa, njia="nyingine", maelezo="Kutoka orodha ya awali", aliyeingiza=aliyeingiza
            )
            res.michango += 1
    return res
