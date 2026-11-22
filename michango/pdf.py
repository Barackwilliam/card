"""Ripoti za PDF zilizopambwa: orodha ya wageni kwa kila kichujio (waliochangia, wasiochangia, ...).

Rangi zinatoka kwenye kadi ya harusi: bluu ya usiku na dhahabu.
"""
import io
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

FONTS = Path(__file__).resolve().parent / "fonts"
NAVY = colors.HexColor("#14205a")
NAVY_2 = colors.HexColor("#1f2f7a")
GOLD = colors.HexColor("#c69a3c")
GOLD_SOFT = colors.HexColor("#f7efdc")
CREAM = colors.HexColor("#faf8f3")
INK = colors.HexColor("#141a33")
MUTED = colors.HexColor("#646b88")
LINE = colors.HexColor("#e6e2d6")
OK = colors.HexColor("#17804c")
WARN = colors.HexColor("#9a6200")

_fonti_zimesajiliwa = False


def _sajili_fonti():
    global _fonti_zimesajiliwa
    if _fonti_zimesajiliwa:
        return
    pdfmetrics.registerFont(TTFont("Poppins", str(FONTS / "Poppins-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Poppins-SemiBold", str(FONTS / "Poppins-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("Poppins-Bold", str(FONTS / "Poppins-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Playfair", str(FONTS / "PlayfairDisplay-BoldItalic.ttf")))
    _fonti_zimesajiliwa = True


VICHWA = {
    "wamechangia": ("Orodha ya Waliochangia", "Asanteni kwa upendo na mchango wenu"),
    "hawajachangia": ("Orodha ya Wasiochangia Bado", "Wageni wanaosubiriwa kuchangia"),
    "wana_salio": ("Wenye Salio la Ahadi", "Waliotoa sehemu ya ahadi zao"),
    "hawajatumiwa": ("Wasiotumiwa Kadi", "Wageni ambao bado hawajapokea kadi"),
    "wametumiwa": ("Waliotumiwa Kadi", "Wageni waliokwisha pokea kadi"),
    "bila_simu": ("Wageni Bila Namba ya Simu", "Tunaomba namba zao"),
    "wote": ("Orodha ya Wageni Wote", "Wageni wote wa harusi"),
}


def tsh(n):
    return f"{int(n or 0):,}"


def simu_nzuri(s):
    if not s:
        return "–"
    if s.startswith("255") and len(s) == 12:
        return f"0{s[3:6]} {s[6:9]} {s[9:]}"
    return f"+{s}"


class _KurasaZote(rl_canvas.Canvas):
    """Canvas inayojua idadi ya kurasa zote ili kuandika 'Ukurasa X kati ya Y'."""

    def __init__(self, *args, **kwargs):
        self._maelezo = kwargs.pop("maelezo", "")
        super().__init__(*args, **kwargs)
        self._kurasa = []

    def showPage(self):
        self._kurasa.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        jumla = len(self._kurasa)
        for hali in self._kurasa:
            self.__dict__.update(hali)
            self._chini(jumla)
            super().showPage()
        super().save()

    def _chini(self, jumla):
        w, _ = A4
        self.setStrokeColor(GOLD)
        self.setLineWidth(0.8)
        self.line(16 * mm, 14 * mm, w - 16 * mm, 14 * mm)
        self.setFont("Poppins", 8)
        self.setFillColor(MUTED)
        self.drawString(16 * mm, 9.5 * mm, self._maelezo)
        self.drawRightString(w - 16 * mm, 9.5 * mm, f"Ukurasa {self._pageNumber} kati ya {jumla}")


def _pete(c, x, y, r):
    """Pete mbili za dhahabu zilizoshikana (mapambo ya harusi)."""
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.2)
    c.circle(x - r * 0.45, y, r, stroke=1, fill=0)
    c.circle(x + r * 0.45, y, r, stroke=1, fill=0)
    c.setFillColor(GOLD)
    c.circle(x + r * 0.45, y + r, 1.6, stroke=0, fill=1)


def tengeneza_pdf(harusi, kichujio, wageni, takwimu) -> bytes:
    """wageni: queryset yenye `jumla_iliyotolewa` (na_jumla())."""
    _sajili_fonti()
    kichwa, kichwa_kidogo = VICHWA.get(kichujio, VICHWA["wote"])
    sasa = timezone.localtime()
    w, h = A4
    buf = io.BytesIO()

    def ukurasa_wa_kwanza(c, doc):
        c.saveState()
        bendi = 52 * mm
        c.setFillColor(NAVY)
        c.rect(0, h - bendi, w, bendi, stroke=0, fill=1)
        c.setFillColor(NAVY_2)
        c.circle(w - 30 * mm, h - 6 * mm, 46 * mm, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.circle(w - 30 * mm, h - 6 * mm, 38 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, h - bendi - 1.6 * mm, w, 1.6 * mm, stroke=0, fill=1)
        _pete(c, w - 30 * mm, h - 26 * mm, 7 * mm)
        c.setFillColor(GOLD)
        c.setFont("Poppins-SemiBold", 8.5)
        c.drawString(16 * mm, h - 15 * mm, harusi.jina.upper())
        c.setFillColor(colors.white)
        c.setFont("Playfair", 25)
        c.drawString(16 * mm, h - 28 * mm, kichwa)
        c.setFont("Poppins", 10)
        c.setFillColor(colors.HexColor("#d9def5"))
        c.drawString(16 * mm, h - 36 * mm, kichwa_kidogo)
        c.setFont("Poppins", 8.5)
        c.drawString(16 * mm, h - 44 * mm,
                     f"Mwisho wa michango: {harusi.tarehe_mwisho:%d.%m.%Y}     ·     Imetolewa: {sasa:%d.%m.%Y, %H:%M}")
        c.restoreState()

    def kurasa_nyingine(c, doc):
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, h - 14 * mm, w, 14 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, h - 14.8 * mm, w, 0.8 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Playfair", 12)
        c.drawString(16 * mm, h - 9.2 * mm, kichwa)
        c.setFont("Poppins", 8)
        c.drawRightString(w - 16 * mm, h - 9 * mm, harusi.jina)
        c.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"{kichwa} - {harusi.jina}", author="Michango ya Harusi",
    )
    fremu_ya_kwanza = Frame(16 * mm, 20 * mm, w - 32 * mm, h - 20 * mm - 62 * mm, id="kwanza")
    fremu = Frame(16 * mm, 20 * mm, w - 32 * mm, h - 20 * mm - 22 * mm, id="nyingine")
    doc.addPageTemplates([
        PageTemplate(id="Kwanza", frames=[fremu_ya_kwanza], onPage=ukurasa_wa_kwanza, autoNextPageTemplate="Nyingine"),
        PageTemplate(id="Nyingine", frames=[fremu], onPage=kurasa_nyingine),
    ])

    s_jina = ParagraphStyle("jina", fontName="Poppins-SemiBold", fontSize=9.5, leading=12, textColor=INK, alignment=TA_LEFT)
    s_ndogo = ParagraphStyle("ndogo", fontName="Poppins", fontSize=8, leading=10, textColor=MUTED)
    s_lbl = ParagraphStyle("lbl", fontName="Poppins-SemiBold", fontSize=7.5, leading=9, textColor=MUTED)
    s_val = ParagraphStyle("val", fontName="Poppins-Bold", fontSize=15, leading=19, textColor=NAVY)

    wageni = list(wageni)
    jumla_ametoa = sum(m.jumla_iliyotolewa or 0 for m in wageni)
    jumla_ahadi = sum(m.ahadi or 0 for m in wageni)
    jumla_salio = sum(max((m.ahadi or 0) - (m.jumla_iliyotolewa or 0), 0) for m in wageni if m.ahadi)

    # Visanduku vya muhtasari
    if kichujio in ("wamechangia", "wana_salio"):
        muhtasari = [("WALIOCHANGIA", f"{len(wageni)}"), ("JUMLA ILIYOCHANGWA", f"TSh {tsh(jumla_ametoa)}"),
                     ("SALIO LA AHADI", f"TSh {tsh(jumla_salio)}")]
    elif kichujio == "hawajachangia":
        waliotumiwa = sum(1 for m in wageni if m.kadi_imetumwa)
        muhtasari = [("HAWAJACHANGIA", f"{len(wageni)}"), ("WAMETUMIWA KADI", f"{waliotumiwa}"),
                     ("AHADI ZAO", f"TSh {tsh(jumla_ahadi)}")]
    else:
        muhtasari = [("WAGENI", f"{len(wageni)}"), ("WALIOCHANGIA (WOTE)", f"{takwimu['wamechangia']}"),
                     ("JUMLA YA MICHANGO", f"TSh {tsh(takwimu['jumla_michango'])}")]
    pengo = 5 * mm
    upana = (w - 32 * mm - 2 * pengo) / 3
    seli = [[Paragraph(lbl, s_lbl), Spacer(1, 2), Paragraph(val, s_val)] for lbl, val in muhtasari]
    nje = Table([[seli[0], "", seli[1], "", seli[2]]], colWidths=[upana, pengo, upana, pengo, upana], hAlign="LEFT")
    mtindo_v = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10)]
    for c in (0, 2, 4):
        mtindo_v += [("BACKGROUND", (c, 0), (c, 0), GOLD_SOFT), ("BOX", (c, 0), (c, 0), 0.6, GOLD),
                     ("LINEABOVE", (c, 0), (c, 0), 2.2, GOLD)]
    nje.setStyle(TableStyle(mtindo_v))

    # Jedwali
    if kichujio in ("wamechangia", "wana_salio"):
        vichwa = ["#", "JINA", "SIMU", "AHADI", "AMETOA", "SALIO"]
        upana_safu = [9 * mm, None, 30 * mm, 24 * mm, 26 * mm, 24 * mm]
    elif kichujio == "hawajachangia":
        vichwa = ["#", "JINA", "SIMU", "AHADI", "KADI"]
        upana_safu = [9 * mm, None, 32 * mm, 26 * mm, 28 * mm]
    else:
        vichwa = ["#", "JINA", "SIMU", "AHADI", "AMETOA", "HALI"]
        upana_safu = [9 * mm, None, 30 * mm, 23 * mm, 24 * mm, 25 * mm]
    upana_safu[1] = (w - 32 * mm) - sum(x for x in upana_safu if x)

    data = [vichwa]
    for i, m in enumerate(wageni, 1):
        ametoa = m.jumla_iliyotolewa or 0
        salio = max((m.ahadi or 0) - ametoa, 0) if m.ahadi else 0
        jina = Paragraph(m.jina, s_jina)
        ahadi = tsh(m.ahadi) if m.ahadi else "–"
        if kichujio in ("wamechangia", "wana_salio"):
            data.append([str(i), jina, simu_nzuri(m.simu), ahadi, tsh(ametoa), tsh(salio) if salio else "–"])
        elif kichujio == "hawajachangia":
            data.append([str(i), jina, simu_nzuri(m.simu), ahadi, "Imetumwa" if m.kadi_imetumwa else "Haijatumwa"])
        else:
            hali = "Amechangia" if ametoa and (not m.ahadi or ametoa >= m.ahadi) else ("Sehemu" if ametoa else "Bado")
            data.append([str(i), jina, simu_nzuri(m.simu), ahadi, tsh(ametoa) if ametoa else "–", hali])

    ina_jumla = kichujio in ("wamechangia", "wana_salio") and wageni
    if ina_jumla:
        data.append(["", Paragraph("JUMLA", ParagraphStyle("j", parent=s_jina, fontName="Poppins-Bold", textColor=NAVY)),
                     "", tsh(jumla_ahadi), tsh(jumla_ametoa), tsh(jumla_salio)])

    def mtindo_wa(safu, mwanzo, ina_kichwa, ina_jumla_hapa):
        """Mitindo ya sehemu ya jedwali. `mwanzo` = namba ya mstari wa kwanza (kwa rangi zinazopishana)."""
        m = [
            ("FONTNAME", (0, 0), (-1, -1), "Poppins"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ]
        k = 1 if ina_kichwa else 0
        if ina_kichwa:
            m += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Poppins-SemiBold"), ("FONTSIZE", (0, 0), (-1, 0), 8),
                  ("LINEBELOW", (0, 0), (-1, 0), 1.6, GOLD)]
        mwisho_wa_data = len(safu) - (1 if ina_jumla_hapa else 0)
        for r in range(k, mwisho_wa_data):
            namba = mwanzo + (r - k)
            if namba % 2 == 0:
                m.append(("BACKGROUND", (0, r), (-1, r), CREAM))
            if kichujio in ("wamechangia", "wana_salio"):
                m += [("FONTNAME", (4, r), (4, r), "Poppins-SemiBold"), ("TEXTCOLOR", (4, r), (4, r), OK)]
            if kichujio == "hawajachangia":
                m.append(("TEXTCOLOR", (4, r), (4, r), OK if safu[r][4] == "Imetumwa" else WARN))
        if ina_jumla_hapa:
            m += [("BACKGROUND", (0, -1), (-1, -1), GOLD_SOFT), ("LINEABOVE", (0, -1), (-1, -1), 1.2, GOLD),
                  ("FONTNAME", (0, -1), (-1, -1), "Poppins-Bold"), ("TEXTCOLOR", (0, -1), (-1, -1), NAVY)]
        return m

    vipande = []
    mistari = data[1:]
    if ina_jumla and len(mistari) > 4:
        # Mstari wa JUMLA usibaki peke yake ukurasa mpya: ufunge pamoja na majina 3 ya mwisho.
        kuu, mkia = data[:-4], data[-4:]
        t1 = Table(kuu, colWidths=upana_safu, repeatRows=1, hAlign="LEFT")
        t1.setStyle(TableStyle(mtindo_wa(kuu, 1, True, False)))
        t2 = Table(mkia, colWidths=upana_safu, hAlign="LEFT")
        t2.setStyle(TableStyle(mtindo_wa(mkia, len(kuu), False, True)))
        vipande = [t1, KeepTogether([t2])]
    else:
        t = Table(data, colWidths=upana_safu, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle(mtindo_wa(data, 1, True, bool(ina_jumla))))
        vipande = [t]

    hadithi = [nje, Spacer(1, 9 * mm)]
    if wageni:
        hadithi += vipande
    else:
        hadithi.append(Paragraph("Hakuna mgeni kwenye orodha hii kwa sasa.", s_ndogo))
    hadithi += [Spacer(1, 8 * mm), Paragraph(
        f"Ripoti hii imetolewa na mfumo wa michango wa {harusi.jina}. Mungu awabariki wote wanaotuchangia.", s_ndogo)]

    doc.build(hadithi, canvasmaker=lambda *a, **k: _KurasaZote(*a, maelezo=f"Michango ya Harusi · {harusi.jina}", **k))
    return buf.getvalue()
