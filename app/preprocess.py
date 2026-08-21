"""Ön işleme (G-07, G-09).

G-07: Göreli zaman ifadeleri MODEL TAHMİNİNE BIRAKILMAZ — takvim kuralıyla mutlak
tarihe çevrilir ve soruya [TARIH ARALIĞI: ...] açıklaması eklenir.
G-09: Hafif kök indirgeme — RAG eşleşmesi için ek temizliği (tam morfoloji değil;
istenirse zeyrek/zemberek takılabilir, arayüz aynı kalır).
"""
import re
from datetime import date, timedelta

from app import config

# ---------------- G-07: Tarih çözümleme ----------------

def _month_range(y: int, m: int) -> tuple[date, date]:
    start = date(y, m, 1)
    end = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return start, end


def _quarter_range(y: int, q: int) -> tuple[date, date]:
    start = date(y, 3 * q - 2, 1)
    _, end = _month_range(y, 3 * q)
    return start, end


def resolve_dates(question: str, today: date | None = None) -> tuple[str, list[dict]]:
    """Soru içindeki göreli zaman ifadelerini bulur, mutlak aralığa çevirir.
    Dönen: (aralık açıklaması eklenmiş soru, çözülen aralıkların listesi)
    """
    # Varsayılan "bugün" config'ten gelir: üretimde gerçek tarih, ölçümde
    # SORBI_BUGUN ile sabitlenebilir (İP-23). Çağıran açıkça verirse o kazanır.
    today = today or config.bugun()
    q = question
    found: list[dict] = []

    def add(label: str, start: date, end: date) -> None:
        found.append({"ifade": label, "baslangic": start.isoformat(), "bitis": end.isoformat()})

    low = q.lower()

    # "son N gün/hafta/ay/yıl"
    for m in re.finditer(r"son\s+(\d+)\s+(gün|hafta|ay|yıl)", low):
        n = int(m.group(1))
        unit = m.group(2)
        days = {"gün": 1, "hafta": 7, "ay": 30, "yıl": 365}[unit] * n
        add(m.group(0), today - timedelta(days=days), today)

    rules: list[tuple[str, tuple[date, date]]] = []
    y, mth = today.year, today.month

    rules.append(("bugün", (today, today)))
    rules.append(("dün", (today - timedelta(days=1), today - timedelta(days=1))))
    rules.append(("bu hafta", (today - timedelta(days=today.weekday()), today)))
    rules.append(("geçen hafta", (today - timedelta(days=today.weekday() + 7),
                                  today - timedelta(days=today.weekday() + 1))))
    rules.append(("bu ay", _month_range(y, mth)))
    prev_y, prev_m = (y - 1, 12) if mth == 1 else (y, mth - 1)
    rules.append(("geçen ay", _month_range(prev_y, prev_m)))
    rules.append(("bu yıl", (date(y, 1, 1), today)))
    rules.append(("yılbaşından beri", (date(y, 1, 1), today)))
    rules.append(("geçen yıl", (date(y - 1, 1, 1), date(y - 1, 12, 31))))

    cur_q = (mth - 1) // 3 + 1
    rules.append(("bu çeyrek", _quarter_range(y, cur_q)))
    prev_q_y, prev_q = (y - 1, 4) if cur_q == 1 else (y, cur_q - 1)
    rules.append(("son çeyrek", _quarter_range(prev_q_y, prev_q)))
    rules.append(("geçen çeyrek", _quarter_range(prev_q_y, prev_q)))

    for label, (s, e) in rules:
        if label in low:
            add(label, s, e)

    if found:
        notes = "; ".join(f"'{f['ifade']}' = {f['baslangic']} .. {f['bitis']}" for f in found)
        q = f"{q}\n[TARIH ARALIĞI: {notes} — sorguda bu mutlak tarihleri kullan]"
    return q, found


# ---------------- G-09: Hafif kök indirgeme ----------------

_SUFFIXES = [
    "lerimizin", "larımızın", "lerimiz", "larımız", "lerinin", "larının",
    "lerine", "larına", "lerden", "lardan", "lerde", "larda", "leri", "ları",
    "ler", "lar", "nin", "nın", "nun", "nün", "in", "ın", "un", "ün",
    "de", "da", "den", "dan", "te", "ta", "ten", "tan", "e", "a", "i", "ı", "u", "ü",
    "ye", "ya", "yi", "yı", "yu", "yü", "si", "sı", "su", "sü",
]


def light_stem(word: str) -> str:
    """Uzun ekten kısaya doğru tek geçişli soyma. Kök ≥3 harf kalmalı.
    Amaç tam morfoloji değil; 'müşterilerimizin' ≈ 'müşteri' eşleşmesini sağlamak."""
    w = word.lower()
    changed = True
    while changed and len(w) > 3:
        changed = False
        for s in _SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 3:
                w = w[: -len(s)]
                changed = True
                break
    return w


_TOKEN = re.compile(r"[a-zçğıöşü]+", re.IGNORECASE)

# 'İ'.lower() Python'da 'i̇' verir: 'i' + U+0307 (birleştirici nokta). Bu ikinci
# kod noktası _TOKEN sınıfında olmadığı için 'İşlemlerin' → ['i', 'şlemlerin']
# diye ikiye bölünüyordu; 'i' kısa diye atılınca geriye BAŞ HARFİ EKSİK bir kök
# kalıyordu ('şlem'). Türkçe bir üründe İ ile başlayan her kelime bundan
# etkileniyordu. (Bulgu: İP-03c, güven kontrolünün yanlış alarmları üzerinden.)
_BIRLESTIRICI = re.compile(r"[\u0300-\u036f]")


def keywords(question: str) -> list[str]:
    """RAG araması için köke indirgenmiş, tekrarsız anahtar kelimeler."""
    stems = []
    for tok in _TOKEN.findall(_BIRLESTIRICI.sub("", question.lower())):
        if len(tok) < 3:
            continue
        s = light_stem(tok)
        if s not in stems:
            stems.append(s)
    return stems
