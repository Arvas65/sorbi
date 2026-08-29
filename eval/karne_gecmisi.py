"""Güven karnesi — sabite değil, KENDİ geçmişine karşı denetlenir.

Neden (BULGU-19, 2026-08-29): `kontrol.bat` karneyi
`BEKLENEN_GUN/ALARM/MUTANT/YAKALAMA` sabitleriyle karşılaştırıyordu. Bu dört
değişken **hiçbir yerde atanmıyor**; kurulan beklenen satır şuydu:

    KARNE_OZET gun= gold=101 alarm= mutant= yakalanan=

Gerçek satırla eşleşmesi iki bağımsız sebeple imkânsız: değişkenler boş, ve
şablonda `zbos=` alanı hiç yok. Sonuç: kontrol HER koşumda "DIKKAT" bastı.
Her koşumda ateşleyen bir alarm, alarm değildir — okuyanı ona bakmamaya
alıştırır. 2026-08-24'te bu kontrol "ölü koddan gerçek kontrole çevrildi"
diye kaydedilmişti; çevrildi ama beklenen değerler hiç doldurulmadı.

Çare `eval/kosum_gecmisi.py`'de zaten yazılıydı ve kendi docstring'i karne
sabitlerini de aynı kalıbın parçası olarak sayıyordu — ama yalnız test
sayısına uygulanmıştı. Bu modül aynı çareyi karneye uygular.

Anlamlı olan yön tek: yakalamanın **düşmesi**. Artış normal ilerlemedir.
Mutant havuzu büyüdüğünde iki koşum kıyaslanamaz; bu bir uyarı değil, bir
kıyas kaybıdır ve öyle raporlanır.

Kullanım:
    python eval/karne_gecmisi.py            # geçmişin son iki kaydını denetler
    python eval/karne_gecmisi.py <log>      # verilen KARNE-GECMIS.log üzerinde
"""
from __future__ import annotations

import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GECMIS = os.path.join(KOK, "docs", "kanit", "KARNE-GECMIS.log")

SAYISAL = ("gold", "alarm", "mutant", "yakalanan", "zbos")


def ayristir(satir: str) -> dict | None:
    """`KARNE_OZET gun=... gold=... ...` satırını sözlüğe çevirir."""
    if not satir.startswith("KARNE_OZET"):
        return None
    kayit: dict = {}
    for parca in satir.split()[1:]:
        if "=" not in parca:
            continue
        anahtar, deger = parca.split("=", 1)
        if anahtar in SAYISAL:
            try:
                kayit[anahtar] = int(deger)
            except ValueError:
                return None
        else:
            kayit[anahtar] = deger
    return kayit or None


def kayitlar(yol: str = GECMIS) -> list[dict]:
    try:
        with open(yol, encoding="utf-8") as f:
            satirlar = f.readlines()
    except OSError:
        return []
    return [k for k in (ayristir(s.strip()) for s in satirlar) if k]


def son_iki(kayit_listesi: list[dict]) -> tuple[dict | None, dict | None]:
    """Son koşum ve onunla KIYASLANABİLİR bir önceki koşum.

    Kıyaslanabilir = aynı `gold` büyüklüğü. Geçmişte 3 soruluk duman koşumları
    ile 101 soruluk tam koşumlar iç içe duruyor; 101'i 3 ile karşılaştırmak
    anlamsız bir düşüş üretirdi.
    """
    if not kayit_listesi:
        return None, None
    son = kayit_listesi[-1]
    for onceki in reversed(kayit_listesi[:-1]):
        if onceki.get("gold") == son.get("gold"):
            return son, onceki
    return son, None


def durum(son: dict | None, onceki: dict | None) -> tuple[str, str]:
    """(kod, açıklama) döner. Kod: ilk | ayni | arti | DUSUS | kiyas_yok | okunamadi"""
    if son is None:
        return "okunamadi", "karne geçmişi okunamadı ya da boş."
    if onceki is None:
        return "ilk", f"bu büyüklükte (gold={son.get('gold')}) ilk koşum; kıyas yok."

    if son.get("mutant") != onceki.get("mutant"):
        return ("kiyas_yok",
                f"mutant havuzu {onceki.get('mutant')} -> {son.get('mutant')} değişti; "
                "yakalama oranları doğrudan kıyaslanamaz.")

    y_son, y_onceki = son.get("yakalanan", 0), onceki.get("yakalanan", 0)
    if y_son < y_onceki:
        return "DUSUS", f"yakalanan {y_onceki} -> {y_son} DÜŞTÜ."
    if y_son > y_onceki:
        return "arti", f"yakalanan {y_onceki} -> {y_son}."
    return "ayni", f"yakalanan {y_son}, değişmedi."


def main() -> int:
    yol = sys.argv[1] if len(sys.argv) > 1 else GECMIS
    son, onceki = son_iki(kayitlar(yol))
    kod, aciklama = durum(son, onceki)
    if son:
        oran = ""
        if son.get("mutant"):
            oran = f" ({100 * son.get('yakalanan', 0) / son['mutant']:.1f}%)"
        print(f"KARNE_GECMIS durum={kod} gold={son.get('gold')} "
              f"mutant={son.get('mutant')} yakalanan={son.get('yakalanan')}{oran}")
    print(f"      {aciklama}")
    # Yalnız gerçek gerileme kırmızıdır. "kiyas_yok" ve "ilk" bilgi notudur.
    return 1 if kod in ("DUSUS", "okunamadi") else 0


if __name__ == "__main__":
    sys.exit(main())
