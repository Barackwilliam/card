from django import template

register = template.Library()


@register.filter
def herufi(jina):
    """Herufi za mwanzo za jina, mfano 'Neema Mollel' -> 'NM' (vyeo kama Dr./Mzee vinarukwa)."""
    vyeo = {"dr.", "dkt.", "eng.", "mr.", "mrs.", "fr.", "rm", "mzee", "mama", "dada", "bw.", "bi.", "mch."}
    maneno = [w for w in str(jina).split() if w.lower() not in vyeo] or str(jina).split()
    return ("".join(w[0] for w in maneno[:2]) or "?").upper()


@register.filter
def tsh(n):
    try:
        return f"{int(n or 0):,}"
    except (TypeError, ValueError):
        return n


@register.filter
def asilimia(a, b):
    try:
        return max(0, min(100, round(100 * float(a) / float(b))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def pata(d, k):
    """Chukua thamani kutoka dict: {{ dict|pata:key }}"""
    try:
        return d.get(k, "")
    except AttributeError:
        return ""


@register.filter
def siku_zilizobaki(tarehe):
    """Siku zilizobaki hadi tarehe (0 = leo, hasi = imepita)."""
    from django.utils import timezone

    try:
        return (tarehe - timezone.localdate()).days
    except TypeError:
        return None


@register.filter
def make_list_nums(s):
    """'5 10 15' -> [5, 10, 15] (kwa orodha za kuchagua)."""
    return [int(x) for x in str(s).split()]
