"""Anonimleştirici (ADR-10 § 3.3) — izin listesi + geri dönüşlü, istek başına takma ad.

    "Ahmet Yılmaz'ın geçen ay kardiyolojideki randevuları"
      → "[KISI_1]'ın geçen ay [DEGER_1]deki randevuları"      (dışarı giden)
    model: {"filtreler": [{"boyut": "bolum", "degerler": ["[DEGER_1]"]}]}
      → geri: "Kardiyoloji"                                   (yerelde)

Üç ilke:

1. **İzin listesi, reddetme listesi değil.** Büyük harfle başlayan bir özel ad,
   GÜVENLİ OLDUĞU KANITLANMADIKÇA jetonlanır. Güvenli olanlar: sözlüğün ADLARI ve
   GÖSTERİMLERİ (yapı metaverisi, S1), il adları, ay ve gün adları, cümle başındaki
   sıradan sözcük. Sözlüğün DEĞERLERİ güvenli DEĞİLDİR — gerçek kolon
   değerleridir (S2/S3) ve her zaman jetonlanır.
2. **Kasa yalnız bellekte ve yalnız bir istek boyunca yaşar.** `Kasa` diske,
   denetim izine, log'a yazılmaz; `__repr__` içeriği göstermez.
3. **Geri çevirme sözlüğe karşıdır.** `DEGER` jetonu, sözlükteki kanonik değere
   döner; kullanıcı ne yazmış olursa olsun.

Takma adlandırma anonimleştirme DEĞİLDİR (KVKK): kasa bizde oldukça bu veri bizim
için kişisel veridir. Bu modül bir veri EN AZA İNDİRME tedbiridir, aktarım izni
değil. Aktarım izni `cikis_kapisi` ve ADR-10 § 3.2'nin işidir.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.guvenlik.kisisel_veri import HITAP, IL_LISTESI, TAKVIM, bul, tr_kucuk

JETON = re.compile(r"\[(?P<tur>[A-Z]+)_(?P<no>\d+)\]")
_OZEL_AD = re.compile(r"(?<![\w\[])[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü]+(?:'[a-zçğıöşü]+)?")

# Soru kalıplarında (çoğu cümle başında) büyük harfle gelebilen sıradan sözcükler.
# Bir kişi adı bu listede olamaz; listede olmayan her büyük harfli sözcük,
# cümle başında da olsa, jetonlanır — güvenli olduğu kanıtlanamıyor.
_SIRADAN = frozenset("""
geçen bu son ilk en toplam kaç hangi ne neler nedir kim kimler göster listele getir
bana bize tüm bütün her ortalama sayı sayısı oran oranı aylık haftalık günlük yıllık
çeyreklik bugün dün yarın yıl ay hafta gün göre bazında ile ve veya ama için
tckn vkn iban tc kimlik telefon adres e-posta sql
""".split()) | HITAP


@dataclass
class Kasa:
    """Tek bir isteğin jeton ↔ gerçek değer tablosu. Kalıcı DEĞİL."""

    _ileri: dict[str, str] = field(default_factory=dict)   # jeton -> gerçek
    _geri: dict[tuple[str, str], str] = field(default_factory=dict)
    _sayac: dict[str, int] = field(default_factory=dict)

    def jeton(self, tur: str, gercek: str) -> str:
        anahtar = (tur, tr_kucuk(gercek))
        if anahtar in self._geri:                     # aynı değer → aynı jeton
            return self._geri[anahtar]
        self._sayac[tur] = self._sayac.get(tur, 0) + 1
        j = f"[{tur}_{self._sayac[tur]}]"
        self._ileri[j] = gercek
        self._geri[anahtar] = j
        return j

    def gercegi(self, jeton: str) -> str | None:
        return self._ileri.get(jeton)

    def geri_cevir(self, metin: str) -> str:
        """Metindeki bütün jetonları gerçeğine döndürür; tanınmayan jeton kalır."""
        if not isinstance(metin, str):
            return metin
        return JETON.sub(lambda m: self._ileri.get(m.group(0), m.group(0)), metin)

    def sayim(self) -> dict[str, int]:
        """Denetim izine giden TEK şey: tür başına kaç jeton. Değer yok."""
        return dict(self._sayac)

    def __repr__(self) -> str:                       # içerik log'a sızmasın
        return f"Kasa({self.sayim()})"

    __str__ = __repr__


def _izin_listesi(sozluk: dict) -> frozenset[str]:
    """Güvenli sözcükler: sözlüğün ad ve gösterimlerinin sözcükleri (S1)."""
    sozcukler: set[str] = set()
    for grup in ("olculer", "boyutlar"):
        for g in sozluk.get(grup, []) or []:
            for alan in ("ad", "gosterim"):
                for s in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", str(g.get(alan) or "")):
                    sozcukler.add(tr_kucuk(s))
    return frozenset(sozcukler)


def _degerler(sozluk: dict) -> list[str]:
    """Sözlükteki gerçek değerler, uzun olan önce (çok sözcüklü değer bölünmesin)."""
    d = {str(v) for b in sozluk.get("boyutlar", []) or [] for v in (b.get("degerler") or []) if str(v).strip()}
    return sorted(d, key=len, reverse=True)


def anonimlestir(metin: str, sozluk: dict | None = None,
                 kasa: Kasa | None = None) -> tuple[str, Kasa]:
    """Metni jetonlar. İSTİSNA FIRLATMAZ; bozuk girdi boş metin döner."""
    kasa = kasa if kasa is not None else Kasa()
    if not isinstance(metin, str) or not metin:
        return "", kasa
    sozluk = sozluk or {}
    parcalar: list[tuple[int, int, str]] = []          # (bas, son, jeton)

    def dolu(a: int, b: int) -> bool:
        return any(not (b <= x or a >= y) for x, y, _ in parcalar)

    # 1) Sözlük değerleri (S2/S3). Başta sözcük sınırı aranır, sonda ARANMAZ:
    #    Türkçe eklemelidir, "Kardiyoloji" değeri "kardiyolojideki" içinde de
    #    geçer ve orada da jetonlanmalı. Üç harften kısa değerler yalnız tam
    #    sözcük olarak eşleşir ("K" her 'K' ile başlayan sözcüğü yutmasın).
    kucuk_metin = tr_kucuk(metin)
    for deger in _degerler(sozluk):
        kucuk_deger = tr_kucuk(deger)
        bas = 0
        while (i := kucuk_metin.find(kucuk_deger, bas)) >= 0:
            j = i + len(kucuk_deger)
            bas = j
            if i > 0 and kucuk_metin[i - 1].isalnum():
                continue
            if len(kucuk_deger) < 3 and j < len(kucuk_metin) and kucuk_metin[j].isalnum():
                continue
            if not dolu(i, j):
                parcalar.append((i, j, kasa.jeton("DEGER", deger)))

    # 2) Algılayıcılar (TCKN, IBAN, kişi adı, ...).
    for b in bul(metin):
        if not dolu(b.bas, b.son):
            parcalar.append((b.bas, b.son, kasa.jeton(b.tur, b.metin)))

    # 3) İzin listesinde olmayan özel adlar. Eklemeli dil: "Bölümlere" izinli
    #    "bölüm"ün ek almış hâlidir. Dört harften uzun izinli sözcüklerde önek
    #    eşleşmesi yeterli; kısalarda tam eşleşme aranır.
    izin = _izin_listesi(sozluk) | IL_LISTESI | TAKVIM | _SIRADAN
    for m in _OZEL_AD.finditer(metin):
        a = m.start()
        govde = m.group(0).split("'", 1)[0]
        b = a + len(govde)
        if dolu(a, b) or _izinli(tr_kucuk(govde), izin):
            continue
        parcalar.append((a, b, kasa.jeton("OZEL", govde)))

    cikti = metin
    for a, b, j in sorted(parcalar, key=lambda p: p[0], reverse=True):
        cikti = cikti[:a] + j + cikti[b:]
    return cikti, kasa


def _izinli(k: str, izin: frozenset[str]) -> bool:
    # Büyük harfli kısaltma ("IBAN") Türkçe kuralla "ıban" olur; ikisi de denenir.
    for aday in {k, k.replace("ı", "i")}:
        if aday in izin or any(len(w) >= 4 and aday.startswith(w) for w in izin):
            return True
    return False


def jetonlari_ayikla(metin: str) -> list[str]:
    return [m.group(0) for m in JETON.finditer(metin or "")]
