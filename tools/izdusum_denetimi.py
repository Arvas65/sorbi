"""Kaç "yanlış" cevap, aslında yalnız FAZLADAN KOLON yüzünden yanlış sayılıyor?

`eval/evaluate.py` satırı bir bütün olarak karşılaştırır:

    rec["dogru"] = _normalize(pred.rows) == _normalize(gold.rows)

Üretilen sorgu gold'un istediği her kolonu doğru döndürse bile yanına bir
kolon daha koyduysa küme eşit çıkmaz ve cevap YANLIŞ sayılır. "En ucuz işlem
hangisi?" sorusuna `(ad, ucret)` dönmek gold'un `(ad)`'ından daha kötü bir
cevap değildir — ama cetvel onu sessiz yanlış yazar ve B-7'nin paydasını
şişirir.

Bu betik ölçer, karar vermez: gold'un satır kümesi, üretilen sonucun bir
KOLON ALT KÜMESİNE (sıra korunarak) eşit mi?

Kullanım:
    python tools/izdusum_denetimi.py <depo_koku> [sonuclar.json]

(BULGU-18, 2026-08-28 · 2026-08-29: ruff temizliği + sonuç dosyası artık
gerçekten argümandan okunuyor — belgede yazıyordu, kodda sabitti.)
"""

import json
import re
import sqlite3
import sys
from collections import Counter
from itertools import combinations

VARSAYILAN_SONUC = "docs/kanit/sonuclar-2026-08-28-gemini-3-7-flash-01.json"
GUN = "2026-07-23"          # damgadaki olcum_gunu

KOK = sys.argv[1]
SONUC_YOLU = sys.argv[2] if len(sys.argv) > 2 else f"{KOK}/{VARSAYILAN_SONUC}"
DB = f"{KOK}/demo/hospital.db"

ETIKETLER = ("izdusum_fazla_kolon", "izdusum_eksik_kolon", "esit_kolon_sirasi",
             "gercek_fark", "bos_sonuc")


def sabitle(s):
    """Ölçüm günü sabitlenir — cetvel çürümesine karşı (İP-23)."""
    return re.sub(r"'now'", f"'{GUN}'", s or "")


def norm(rows):
    out = set()
    for r in rows:
        out.add(tuple(
            "" if v is None else (round(v, 2) if isinstance(v, float) else v)
            for v in r
        ))
    return out


def gold_yukle(kok):
    gold = {}
    with open(f"{kok}/eval/test_set_tr.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                o = json.loads(line)
                gold[o["id"]] = o
    return gold


def alt_kume_esler(p_rows, g_rows, hedef_kume):
    """Üretilen sonucun bir kolon alt kümesi gold'a eşit mi? Eşleşen indisler
    ya da None döner."""
    np_ = len(p_rows[0])
    ng = len(g_rows[0]) if g_rows else 0
    if not ng or np_ < ng:
        return None
    for idx in combinations(range(np_), ng):
        if norm([tuple(r[i] for i in idx) for r in p_rows]) == hedef_kume:
            return idx
    return None


def main():
    gold = gold_yukle(KOK)
    with open(SONUC_YOLU, encoding="utf-8") as f:
        res = json.load(f)["results"]

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    def kos(sql):
        cur = con.cursor()
        cur.execute(sabitle(sql))
        return cur.fetchall()

    sinif = {}
    for x in res:
        if x["dogru"]:
            sinif[x["id"]] = "esit"
            continue
        g = gold.get(x["id"])
        if not g:
            sinif[x["id"]] = "gold_yok"
            continue
        try:
            p_rows = kos(x["sql"])
            g_rows = kos(g["gold_sql"])
        except Exception as e:                      # noqa: BLE001 — ölçüm sürmeli
            sinif[x["id"]] = f"kosulamadi: {type(e).__name__}"
            continue
        if not p_rows:
            sinif[x["id"]] = "bos_sonuc"
            continue

        G = norm(g_rows)
        bulundu = alt_kume_esler(p_rows, g_rows, G)
        if bulundu is not None:
            fazla = len(p_rows[0]) > (len(g_rows[0]) if g_rows else 0)
            sinif[x["id"]] = "izdusum_fazla_kolon" if fazla else "esit_kolon_sirasi"
            continue

        # Ters yön: üretilen, gold'un bir alt kümesi mi (kolon EKSİK)?
        ters = alt_kume_esler(g_rows, p_rows, norm(p_rows)) if g_rows else None
        sinif[x["id"]] = "izdusum_eksik_kolon" if ters is not None else "gercek_fark"

    con.close()

    c = Counter(sinif.values())
    print(f"=== SINIFLANDIRMA ({len(res)} soru) ===")
    print(f"kaynak: {SONUC_YOLU}")
    for k, v in c.most_common():
        print(f"{v:4d}  {k}")

    yanlis = [x for x in res if not x["dogru"]]
    print()
    print(f"Yanlis sayilan          : {len(yanlis)}")
    for etiket in ETIKETLER:
        ids = [x["id"] for x in yanlis if sinif[x["id"]] == etiket]
        if ids:
            print(f"  {etiket:22s}: {len(ids):3d}  -> {ids}")

    bayrakli = [x["id"] for x in yanlis if x["bayraklar"]]
    print()
    print("Bayraklananlar:", bayrakli)
    print("Bunlarin sinifi:", {i: sinif[i] for i in bayrakli})


if __name__ == "__main__":
    main()
