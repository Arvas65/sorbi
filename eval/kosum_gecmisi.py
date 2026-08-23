"""Koşum geçmişi — test sayısını sabite değil, KENDİ geçmişine karşı denetler.

Neden (2026-08-22): `kontrol.bat` içinde `BEKLENEN_TEST=320` diye bir sabit
vardı. Aynı gün 6 test eklendi, sayı 326 oldu ve betik "beklenenden farklı"
diye uyardı — oysa artış iyi bir şeydi. Sabit, yazıldığı ana aittir.

Bu, bu hafta dördüncü kez aynı kalıp: sabit referans günü, sabit karne
sayıları, ADR'nin koda inmemesi ve şimdi bu. Çare her seferinde aynı:
sabiti sil, ölçülen değeri KENDİ geçmişiyle karşılaştır.

Anlamlı olan yön tek: test sayısının **düşmesi**. Artış normal ilerlemedir.

Kullanım:
    python eval/kosum_gecmisi.py docs/kanit/kontrol-20260822-0018.log
"""
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GECMIS = os.path.join(KOK, "docs", "kanit", "TEST-GECMIS.log")

_GECEN = re.compile(r"(\d+) passed")


def gecen_sayisi(metin: str) -> int | None:
    """pytest çıktısındaki 'N passed' sayısı. Birden çoksa sonuncusu."""
    bulunan = _GECEN.findall(metin or "")
    return int(bulunan[-1]) if bulunan else None


def onceki_sayi(yol: str = GECMIS) -> int | None:
    try:
        with open(yol, encoding="utf-8") as f:
            kayitlar = [s for s in f if s.startswith("TEST_OZET")]
    except OSError:
        return None
    if not kayitlar:
        return None
    for parca in kayitlar[-1].split():
        if parca.startswith("gecen="):
            try:
                return int(parca.split("=", 1)[1])
            except ValueError:
                return None
    return None


def yaz(gecen: int, yol: str = GECMIS) -> None:
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "a", encoding="utf-8") as f:
            f.write(f"TEST_OZET gecen={gecen}\n")
    except OSError:
        pass          # geçmiş yazılamazsa denetim yine de yapılmıştır


def durum(gecen: int | None, onceki: int | None) -> str:
    if gecen is None:
        return "okunamadi"
    if onceki is None:
        return "ilk"
    if gecen < onceki:
        return "azaldi"
    return "arti" if gecen > onceki else "ayni"


def main() -> int:
    if len(sys.argv) < 2:
        print("TEST_GECMIS durum=okunamadi sebep=log_verilmedi")
        return 0
    try:
        with open(sys.argv[1], encoding="utf-8", errors="ignore") as f:
            metin = f.read()
    except OSError:
        print("TEST_GECMIS durum=okunamadi sebep=log_acilamadi")
        return 0

    gecen = gecen_sayisi(metin)
    onceki = onceki_sayi()
    d = durum(gecen, onceki)
    print(f"TEST_GECMIS gecen={gecen} onceki={onceki} durum={d}")
    if gecen is not None:
        yaz(gecen)
    # Yalnız DÜŞÜŞ bir sorundur; artış ilerlemedir.
    return 1 if d == "azaldi" else 0


if __name__ == "__main__":
    sys.exit(main())
