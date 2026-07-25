"""SorBI değerlendirme koşucusu (G-11: execution accuracy).

Her test sorusu tam pipeline'dan geçirilir (ön işleme + RAG + üretim + doğrulama),
üretilen SQL ile gold SQL aynı veritabanında çalıştırılır ve SONUÇ KÜMELERİ
karşılaştırılır (Zhong et al. 2020 yaklaşımı — SQL metni değil, sonuç eşitliği).

Kullanım:
    python eval/evaluate.py --db demo/hospital.db --testset eval/test_set_tr.jsonl
    python eval/evaluate.py --mode api            # API modunu ölçmek için
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, executor
from app.preprocess import resolve_dates
from app.validator import validate_and_transpile


def _normalize(rows: list) -> set:
    """Sonuç kümesini kıyaslanabilir hale getir: satır sırası önemsiz,
    ondalıklar 2 haneye yuvarlı, None -> ''. """
    out = set()
    for r in rows:
        norm = tuple("" if v is None else (round(v, 2) if isinstance(v, float) else v) for v in r)
        out.add(norm)
    return out


def gold_check(items: list) -> int:
    """LLM'siz bütünlük kontrolü: her gold_sql doğrulanır ve çalıştırılır.
    Test seti bozuksa accuracy ölçümü anlamsız olur (G-11 önkoşulu)."""
    hatali = 0
    for i, item in enumerate(items, 1):
        v = validate_and_transpile(item["gold_sql"])
        if v.ok:
            r = executor.run(v.sql)
            durum = "OK" if r.status == "BASARILI" else f"CALISMA_HATASI: {r.error[:80]}"
        else:
            durum = f"DOGRULAMA_RED: {v.error[:80]}"
        if durum != "OK":
            hatali += 1
        isaret = "+" if durum == "OK" else "-"
        print(f"[{i:02d}/{len(items)}] {isaret} {item['soru'][:60]}  [{durum}]")
    print("\n" + "=" * 60)
    print(f"GOLD SQL SAĞLIĞI: {len(items) - hatali}/{len(items)} çalışıyor")
    return hatali


def run_one(item: dict, idx, mode: str) -> dict:
    t0 = time.time()
    rec = {"id": item["id"], "soru": item["soru"], "zorluk": item["zorluk"],
           "join": item["join"], "dogru": False, "asama": "", "sql": ""}

    annotated, _ = resolve_dates(item["soru"])
    context, _ = idx.retrieve(item["soru"])
    try:
        gen, used = generator.generate(annotated, context, mode)
    except Exception as e:
        rec["asama"] = f"uretim_hatasi: {e}"
        return rec
    rec["sql"] = gen.get("sql", "")
    rec["guven"] = gen.get("guven", 0)

    v = validate_and_transpile(rec["sql"], target_dialect=config.TARGET_DIALECT,
                               known_tables=idx.known_tables,
                               known_columns=idx.known_columns)
    if not v.ok:  # tek öz-onarım denemesi (pipeline ile aynı davranış)
        gen2, _ = generator.repair(annotated, context, rec["sql"], v.error, mode)
        rec["sql"] = gen2.get("sql", "")
        rec["onarim"] = True
        v = validate_and_transpile(rec["sql"], target_dialect=config.TARGET_DIALECT,
                                   known_tables=idx.known_tables,
                                   known_columns=idx.known_columns)
        if not v.ok:
            rec["asama"] = f"dogrulama_reddi: {v.error[:120]}"
            return rec

    pred = executor.run(v.sql)
    if pred.status == "CALISMA_HATASI" and not rec.get("onarim"):
        gen3, _ = generator.repair(annotated, context, v.sql, pred.error, mode)
        rec["onarim"] = True
        v2 = validate_and_transpile(gen3.get("sql", ""), target_dialect=config.TARGET_DIALECT,
                                    known_tables=idx.known_tables,
                                    known_columns=idx.known_columns)
        if v2.ok:
            rec["sql"] = gen3["sql"]
            pred = executor.run(v2.sql)
    if pred.status != "BASARILI":
        rec["asama"] = f"calisma_hatasi: {pred.status}"
        return rec

    gold = executor.run(item["gold_sql"])
    if gold.status != "BASARILI":
        rec["asama"] = f"GOLD_HATASI: {gold.error[:120]}"  # test setinin kendisi bozuksa görün
        return rec

    rec["dogru"] = _normalize(pred.rows) == _normalize(gold.rows)
    rec["asama"] = "esit" if rec["dogru"] else "sonuc_farkli"
    rec["sure_s"] = round(time.time() - t0, 2)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--testset", default=os.path.join(os.path.dirname(__file__), "test_set_tr.jsonl"))
    ap.add_argument("--mode", default=config.MODE, choices=["local", "api"])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results.json"))
    ap.add_argument("--gold-only", action="store_true",
                    help="LLM'siz mod: yalnızca gold_sql'lerin geçerliliğini ve çalıştığını kontrol et")
    args = ap.parse_args()
    if args.db:
        config.DB_URL = f"sqlite:///{os.path.abspath(args.db)}"

    items = [json.loads(l) for l in open(args.testset, encoding="utf-8") if l.strip()]

    if args.gold_only:
        sys.exit(1 if gold_check(items) else 0)

    from app import generator            # LLM gerektiren yol — gecikmeli import
    from app.schema_rag import ContextIndex
    globals()["generator"] = generator
    idx = ContextIndex(config.DB_URL)
    results = []
    for i, item in enumerate(items, 1):
        rec = run_one(item, idx, args.mode)
        results.append(rec)
        isaret = "+" if rec["dogru"] else "-"
        print(f"[{i:02d}/{len(items)}] {isaret} ({rec['zorluk']}, {rec['join']} join) "
              f"{item['soru'][:60]}  [{rec['asama']}]")

    n = len(results)
    dogru = sum(r["dogru"] for r in results)
    print("\n" + "=" * 60)
    print(f"EXECUTION ACCURACY: {dogru}/{n} = %{100 * dogru / n:.1f}   (hedef G-11: >=%80)")
    for grup, anahtar in [("Zorluk", "zorluk"), ("JOIN sayısı", "join")]:
        print(f"\n{grup} kırılımı:")
        for val in sorted({r[anahtar] for r in results}, key=str):
            alt = [r for r in results if r[anahtar] == val]
            d = sum(r["dogru"] for r in alt)
            print(f"  {val}: {d}/{len(alt)} = %{100 * d / len(alt):.0f}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"accuracy": dogru / n, "mode": args.mode, "n": n,
                   "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\nAyrıntılı rapor: {args.out}")


if __name__ == "__main__":
    main()
