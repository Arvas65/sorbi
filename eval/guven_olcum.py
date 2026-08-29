"""Güven kontrolünün (B-7) kendi karnesi — LLM'SİZ, mutasyon tabanlı.

Sorun: "sessiz yanlışı yakalıyor mu" sorusunu ancak yanlış cevaplar üzerinde
ölçebiliriz, yanlış cevapları da model üretir. Model çalıştırmak her turda
40 dakika ve bir GPU demektir; kontrolün kendisini geliştirirken bu döngü
çok yavaş.

Çözüm: yanlışı biz üretiriz. 101 sorunun gold SQL'i doğru cevaptır. Gold'u
bozarsak — filtre değerini değiştir, WHERE'i düşür, COUNT'u SUM yap, LIMIT'i
kaldır — elimizde **doğruluğu kesin olarak bilinen** bir yanlış cevap olur.

    gold        → kontrol SUSMALI   (bayrak = yanlış alarm)
    mutant      → kontrol KONUŞMALI (bayrak yoksa = kaçırma)

Önemli kural: sonucu gold ile AYNI kalan mutant sayılmaz. `WHERE 1=1` düşmek
sorguyu bozmaz; o mutant yanlış cevap değildir ve kaçırıldı diye kontrolü
suçlayamayız. Her mutant çalıştırılır ve sonucu gold'dan farklıysa sayılır.

Bu ölçüm gerçek model hatalarının YERİNE geçmez — mutasyonlar bizim
hayal ettiğimiz hatalardır, modelinkiler değil. Gerçek sayı `evaluate.py`
koşumundaki "güven kontrolü karnesi" bölümündedir. Buradaki hızlı geri
bildirim döngüsüdür: kontrolü değiştir, 3 saniyede etkisini gör.

Kullanım:  python eval/guven_olcum.py [--limit N]
"""
import argparse
import inspect
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from app import config, executor, guven  # noqa: E402
from app.schema_rag import ContextIndex  # noqa: E402
from eval.tarih_sabitle import olcum_gunu, sabitle, sayac  # noqa: E402

TEST_SET = os.path.join(KOK, "eval", "test_set_tr.jsonl")

# Tam setin soru sayısı. Bunun altındaki koşumlar geçmişe yazılmaz.
TAM_SET = 101


# ------------------------------------------------------------------ mutasyonlar

def _mutant_filtre_degeri(sql: str) -> str | None:
    """Metin filtresini şemada olmayan bir yazıma çevirir (Türkçe İ/I tuzağı)."""
    m = re.search(r"'([^']{2,})'", sql)
    if not m:
        return None
    eski = m.group(1)
    yeni = eski.upper() if eski != eski.upper() else eski.replace("I", "İ")
    if yeni == eski:
        yeni = eski + "_X"
    return sql[:m.start(1)] + yeni + sql[m.end(1):]


def _mutant_where_dus(sql: str) -> str | None:
    """WHERE'i düşürür — filtresi olan her sorguyu yanlış yapar."""
    m = re.search(r"\bWHERE\b", sql, re.IGNORECASE)
    if not m:
        return None
    son = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING)\b", sql[m.start():], re.IGNORECASE)
    return sql[:m.start()] + (sql[m.start() + son.start():] if son else "")


def _mutant_toplama(sql: str) -> str | None:
    """COUNT↔SUM↔AVG takası — anlam hatasının en saf hâli."""
    for eski, yeni in (("COUNT", "SUM"), ("SUM", "AVG"), ("AVG", "SUM")):
        if re.search(rf"\b{eski}\s*\(", sql, re.IGNORECASE):
            return re.sub(rf"\b{eski}\s*\(", f"{yeni}(", sql, count=1, flags=re.IGNORECASE)
    return None


def _mutant_limit_dus(sql: str) -> str | None:
    """LIMIT'i düşürür — 'ilk 5' sorusuna 40 satır döndürür."""
    m = re.search(r"\s+LIMIT\s+\d+\s*;?\s*$", sql, re.IGNORECASE)
    return sql[:m.start()] if m else None


def _mutant_bos_kume(sql: str) -> str | None:
    """Var olmayan bir değerle filtreler — sessiz yanlışın en sık biçimi: 0 satır."""
    if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
        return re.sub(r"\bWHERE\b", "WHERE 'yok' = 'olmayan_deger' AND", sql,
                      count=1, flags=re.IGNORECASE)
    m = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b", sql, re.IGNORECASE)
    ek = " WHERE 'yok' = 'olmayan_deger'"
    return (sql[:m.start()] + ek + " " + sql[m.start():]) if m else sql.rstrip(" ;") + ek


# ---------------------------------------------------- gerçekçi hata aileleri
#
# B7R-08 / BULGU-04 (2026-08-23). Yukarıdaki beş aile ortak bir kusuru
# paylaşıyor: ürettikleri yanlış cevap BİÇİMİNDEN belli oluyor — boş küme,
# sıfır toplam, şemada olmayan bir değer. B-7'nin sekiz kontrolü de tam olarak
# o biçimler için yazıldı, dolayısıyla karne kendi kendini sınıyordu:
# mutasyonda %83, gerçek model hatalarında %20 (GA'lar kesişmiyor).
#
# Gerçek hata şöyle görünüyor: **dolu, makul, doğru biçimli bir tablo ve
# yanlış bir sayı.** Aşağıdaki aileler onu taklit ediyor. Karneyi DÜŞÜRMELERİ
# beklenir — düşürmeleri iyidir; abartılı bir sayının yerine dürüst bir sayı
# koyar. Karne bir regresyon nöbetçisidir; onu saha tahmincisine yaklaştıran
# tek şey havuzun gerçek dağılıma benzemesidir.

def _mutant_deger_takasi(sql: str, idx=None) -> str | None:
    """Filtre değerini AYNI kolonun BAŞKA bir geçerli değeriyle değiştirir.

    En zor aile ve gerçek hataya en yakın olanı: sorgu çalışır, satır döner,
    tablo makul görünür, sayı yanlıştır. `bilinmeyen_deger` susar (değer
    geçerli), `bos_sonuc` susar (satır var), `sifir_toplama` susar.
    """
    bilinen = getattr(idx, "bilinen_degerler", None) or {}
    if not bilinen:
        return None
    for m in re.finditer(r"'([^']{2,})'", sql):
        eski = m.group(1)
        for anahtar, degerler in bilinen.items():
            if "." in anahtar or eski not in degerler:
                continue
            baska = sorted(d for d in degerler if d != eski)
            if baska:
                return sql[:m.start(1)] + baska[0] + sql[m.end(1):]
    return None


def _mutant_karsilastirma_cevirme(sql: str) -> str | None:
    """`>` ↔ `<` çevirir. 'En az 3 randevusu olan' → 'en fazla 3 olan'."""
    for eski, yeni in ((">=", "<="), ("<=", ">="), (">", "<"), ("<", ">")):
        m = re.search(rf"(?<![<>=]){re.escape(eski)}(?![<>=])", sql)
        if m:
            return sql[:m.start()] + yeni + sql[m.end():]
    return None


def _mutant_distinct_dus(sql: str) -> str | None:
    """DISTINCT'i düşürür — 'kaç FARKLI hasta' sorusunu tekrarlarla sayar.

    Model hatalarının en sık görülen sessiz biçimlerinden: sayı büyür, tablo
    doğru görünür, hiçbir biçim kontrolü uyanmaz.
    """
    m = re.search(r"\bDISTINCT\b\s*", sql, re.IGNORECASE)
    return sql[:m.start()] + sql[m.end():] if m else None


def _mutant_join_ici_disi(sql: str) -> str | None:
    """LEFT JOIN ↔ INNER JOIN. Eşleşmesi olmayan satırlar sessizce düşer/eklenir."""
    if re.search(r"\bLEFT\s+(OUTER\s+)?JOIN\b", sql, re.IGNORECASE):
        return re.sub(r"\bLEFT\s+(OUTER\s+)?JOIN\b", "JOIN", sql, count=1,
                      flags=re.IGNORECASE)
    if re.search(r"(?<!LEFT )\bJOIN\b", sql, re.IGNORECASE):
        return re.sub(r"\bJOIN\b", "LEFT JOIN", sql, count=1, flags=re.IGNORECASE)
    return None


MUTASYONLAR = [
    # biçimden belli olan aileler
    ("filtre_degeri", _mutant_filtre_degeri),
    ("where_dus", _mutant_where_dus),
    ("toplama_takasi", _mutant_toplama),
    ("limit_dus", _mutant_limit_dus),
    ("bos_kume", _mutant_bos_kume),
    # gerçek model hatasına benzeyen aileler (B7R-08)
    ("deger_takasi", _mutant_deger_takasi),
    ("karsilastirma", _mutant_karsilastirma_cevirme),
    ("distinct_dus", _mutant_distinct_dus),
    ("join_ici_disi", _mutant_join_ici_disi),
]


# ------------------------------------------------------------------ ölçüm

def _sonuc(sql: str):
    """SQL'i ÖLÇÜM GÜNÜNE sabitleyerek çalıştırır (İP-23).

    Sabitleme yalnız çalıştırmada; güven kontrolüne sorgunun özgün hâli
    verilir, çünkü kullanıcıya giden de odur.
    """
    r = executor.run(sabitle(sql, olcum_gunu()))
    return r if r.status == "BASARILI" else None


def _tum_kolonlar(idx) -> set:
    return {k for kolonlar in (getattr(idx, "known_columns", None) or {}).values()
            for k in kolonlar}


def _bayrakla(idx, soru: str, sql: str, sonuc, kapali=None) -> list[str]:
    g = guven.degerlendir(soru, sql, sonuc.rowcount,
                          kapali=kapali,
                          kolon_sayisi=len(sonuc.columns or []),
                          satirlar=sonuc.rows,
                          bilinen_degerler=getattr(idx, "bilinen_degerler", None),
                          kolonlar=_tum_kolonlar(idx),
                          sozluk=(getattr(idx, "glossary", None) or {}).get("terms", {}))
    return g.kodlar


def _bos_cevap(sonuc) -> bool:
    """Sonuç 'hiç yok' anlamına mı geliyor: sıfır satır ya da tek hücrede 0/None."""
    if sonuc.rowcount == 0:
        return True
    if sonuc.rowcount == 1 and len(sonuc.columns or []) == 1:
        try:
            deger = list(sonuc.rows[0])[0]
        except (TypeError, IndexError):
            return False
        return deger in (0, None) and not isinstance(deger, bool)
    return False


def olc(limit: int | None = None, kapali=None) -> dict:
    """kapali=None ise üretimdeki ayar (config.GUVEN_KAPALI) ölçülür."""
    kapali = config.GUVEN_KAPALI if kapali is None else kapali
    idx = ContextIndex()
    with open(TEST_SET, encoding="utf-8") as f:
        sorular = [json.loads(s) for s in f if s.strip()]
    if limit:
        sorular = sorular[:limit]

    yanlis_alarm, temiz = [], 0
    yakalanan, kacirilan, gecersiz = [], [], 0
    kod_sayaci: dict[str, dict] = {}
    # Referans gün veri setine uymazsa zamana bağlı sorular boşa düşer ve
    # ÖLÇMEZ hale gelir. Bunu saymazsak sessizce körleşiriz — nitekim
    # 2026-08-21'de İhsan'ın kopyasında tam olarak bu oldu.
    zamana_bagli, zamana_bagli_bos = 0, []

    for item in sorular:
        gold = _sonuc(item["gold_sql"])
        if gold is None:
            continue
        if sayac(item["gold_sql"]):
            zamana_bagli += 1
            if _bos_cevap(gold):
                zamana_bagli_bos.append(item["id"])
        kodlar = _bayrakla(idx, item["soru"], item["gold_sql"], gold, kapali)
        if kodlar:
            yanlis_alarm.append({"id": item["id"], "soru": item["soru"], "kodlar": kodlar})
            for k in kodlar:
                kod_sayaci.setdefault(k, {"dogruda": 0, "yanlista": 0})["dogruda"] += 1
        else:
            temiz += 1

        for ad, fn in MUTASYONLAR:
            try:
                # Bazı aileler şemanın gerçek değerlerine ihtiyaç duyar
                # (`deger_takasi`); imzasına bakıp öyle çağırıyoruz.
                mutant = (fn(item["gold_sql"], idx)
                          if "idx" in inspect.signature(fn).parameters
                          else fn(item["gold_sql"]))
            except Exception:      # noqa: BLE001 - mutasyon üretimi ölçümü durdurmaz
                mutant = None
            if not mutant or mutant.strip() == item["gold_sql"].strip():
                continue
            m_sonuc = _sonuc(mutant)
            if m_sonuc is None:
                continue           # mutant çalışmıyor: bu sorgu kullanıcıya hiç ulaşmaz
            if _ayni(m_sonuc, gold):
                gecersiz += 1      # sonuç değişmedi: yanlış cevap DEĞİL, sayılmaz
                continue
            kodlar = _bayrakla(idx, item["soru"], mutant, m_sonuc, kapali)
            kayit = {"id": item["id"], "soru": item["soru"], "mutasyon": ad,
                     "sql": mutant, "kodlar": kodlar}
            if kodlar:
                yakalanan.append(kayit)
                for k in kodlar:
                    kod_sayaci.setdefault(k, {"dogruda": 0, "yanlista": 0})["yanlista"] += 1
            else:
                kacirilan.append(kayit)

    mutant_sayisi = len(yakalanan) + len(kacirilan)
    gold_sayisi = temiz + len(yanlis_alarm)
    for v in kod_sayaci.values():
        v["isabet"] = v["yanlista"] / (v["yanlista"] + v["dogruda"])
    return {
        "olcum_gunu": olcum_gunu(),
        "zamana_bagli": zamana_bagli,
        "zamana_bagli_bos": zamana_bagli_bos,
        "kapali": sorted(kapali or []),
        "gold_sayisi": gold_sayisi,
        "yanlis_alarm": len(yanlis_alarm),
        "yanlis_alarm_orani": len(yanlis_alarm) / gold_sayisi if gold_sayisi else 0.0,
        "mutant_sayisi": mutant_sayisi,
        "yakalanan": len(yakalanan),
        "yakalama_orani": len(yakalanan) / mutant_sayisi if mutant_sayisi else 0.0,
        "gecersiz_mutant": gecersiz,
        "kodlar": kod_sayaci,
        "yanlis_alarm_ornekleri": yanlis_alarm[:12],
        "kacirilan_ornekleri": kacirilan[:12],
        "mutasyon_kirilimi": _mutasyon_kirilimi(yakalanan, kacirilan),
    }


def _ayni(a, b) -> bool:
    return sorted(map(str, a.rows)) == sorted(map(str, b.rows))


def _mutasyon_kirilimi(yakalanan: list, kacirilan: list) -> dict:
    kirilim: dict[str, dict] = {}
    for kayit in yakalanan:
        kirilim.setdefault(kayit["mutasyon"], {"yakalanan": 0, "kacirilan": 0})["yakalanan"] += 1
    for kayit in kacirilan:
        kirilim.setdefault(kayit["mutasyon"], {"yakalanan": 0, "kacirilan": 0})["kacirilan"] += 1
    for v in kirilim.values():
        t = v["yakalanan"] + v["kacirilan"]
        v["oran"] = v["yakalanan"] / t if t else 0.0
    return kirilim


GECMIS = os.path.join(KOK, "docs", "kanit", "KARNE-GECMIS.log")


def _ozet_satiri(r: dict) -> str:
    return (f"KARNE_OZET gun={r['olcum_gunu']} gold={r['gold_sayisi']} "
            f"alarm={r['yanlis_alarm']} mutant={r['mutant_sayisi']} "
            f"yakalanan={r['yakalanan']} zbos={len(r['zamana_bagli_bos'])}")


def _gecmise_yaz(r: dict) -> None:
    """Karneyi ekle-only bir günlüğe yazar ve bir öncekiyle karşılaştırır.

    Sabit bir beklenen sayı tutmak yanlıştı: o sayı yazıldığı makinenin
    verisine aitti ve başka bir kopyada 'gerileme' gibi göründü. Doğru
    referans, AYNI MAKİNENİN bir önceki koşumudur.

    KISMİ KOŞUM GEÇMİŞE GİRMEZ (bulgu 2026-08-22): `--limit 3` ile alınan
    bir karne 101 soruluk karneyle karşılaştırılamaz — aynı "farklı cetvel"
    kuralı. Test süiti içindeki 3 soruluk bir koşum gerçek günlüğe yazılmış
    ve İhsan'ın makinesinde "ÖNCEKİ KARNE: FARKLI" diye yanlış alarm
    üretmişti. Testin üretim kanıtını kirletmesi başlı başına bir kusurdur.
    """
    if r["gold_sayisi"] < TAM_SET:
        print(f"\nÖNCEKİ KARNE: kısmi koşum ({r['gold_sayisi']}/{TAM_SET} soru), "
              "geçmişe yazılmadı.")
        return
    satir = _ozet_satiri(r)
    onceki = None
    try:
        if os.path.exists(GECMIS):
            with open(GECMIS, encoding="utf-8") as f:
                eskiler = [x.strip() for x in f if x.startswith("KARNE_OZET")]
            onceki = eskiler[-1] if eskiler else None
        os.makedirs(os.path.dirname(GECMIS), exist_ok=True)
        with open(GECMIS, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError as e:
        print(f"\n  ~ Karne geçmişi yazılamadı ({type(e).__name__}); ölçüm geçerli.")

    if onceki is None:
        print("\nÖNCEKİ KARNE: yok — bu koşum taban olacak.")
    elif onceki == satir:
        print("\nÖNCEKİ KARNE: birebir aynı.")
    else:
        print("\nÖNCEKİ KARNE: FARKLI")
        print(f"  önceki: {onceki}")
        print(f"  şimdi : {satir}")
        eski = dict(p.split("=", 1) for p in onceki.split()[1:])
        yeni = dict(p.split("=", 1) for p in satir.split()[1:])
        if eski.get("gun") != yeni.get("gun"):
            print("  ! Referans gün değişmiş — sayılar zaten karşılaştırılamaz.")


def main() -> None:
    ap = argparse.ArgumentParser(description="B-7 güven kontrolünün mutasyon karnesi")
    ap.add_argument("--limit", type=int, help="ilk N soru")
    ap.add_argument("--json", help="sonucu bu dosyaya yaz")
    ap.add_argument("--hepsi-acik", action="store_true",
                    help="kapalı kontrolleri de aç (kapatma kararını gözden geçirmek için)")
    a = ap.parse_args()

    kapali = set() if a.hepsi_acik else None
    r = olc(a.limit, kapali)
    print("=" * 68)
    print("GÜVEN KONTROLÜ MUTASYON KARNESİ (B-7, LLM'siz)")
    print("=" * 68)
    print(f"Ölçüm günü (sabit)      : {olcum_gunu()}")
    _bos = r["zamana_bagli_bos"]
    if _bos:
        print(f"  ! Zamana bağlı {r['zamana_bagli']} sorunun {len(_bos)}'i BOŞ döndü "
              f"(id: {', '.join(str(x) for x in _bos)})")
        print("    Referans gün veri setine uymuyor: o sorular artık bir şey ölçmüyor.")
        print("    Düzeltme: SORBI_BUGUN=<gün> ile elle verin, ya da veri setini "
              "yeniden tohumlayın.")
    else:
        print(f"  + Zamana bağlı {r['zamana_bagli']} sorunun tamamı dolu döndü")
    print(f"Kapalı kontrol          : {', '.join(r['kapali']) or 'yok'}")
    print(f"Doğru sorgu (gold)      : {r['gold_sayisi']}")
    print(f"  gereksiz bayrak       : {r['yanlis_alarm']} "
          f"(%{100 * r['yanlis_alarm_orani']:.1f})   <- DÜŞMELİ")
    print(f"Bilinen yanlış (mutant) : {r['mutant_sayisi']}"
          f"   (sonucu değişmeyen {r['gecersiz_mutant']} mutant sayılmadı)")
    print(f"  yakalanan             : {r['yakalanan']} "
          f"(%{100 * r['yakalama_orani']:.1f})   <- YÜKSELMELİ")
    print("\nMutasyon türüne göre yakalama:")
    for ad, v in sorted(r["mutasyon_kirilimi"].items(), key=lambda x: -x[1]["oran"]):
        print(f"  {ad:16s} {v['yakalanan']:4d}/{v['yakalanan'] + v['kacirilan']:<4d} "
              f"%{100 * v['oran']:.0f}")
    print("\nKontrol bazında (yanlışta kaç kez / doğruda kaç kez / isabet):")
    for kod, v in sorted(r["kodlar"].items(), key=lambda x: -x[1]["isabet"]):
        print(f"  {kod:22s} {v['yanlista']:4d} / {v['dogruda']:4d}  "
              f"%{100 * v['isabet']:.0f}")
    if r["yanlis_alarm_ornekleri"]:
        print("\nGereksiz bayrak örnekleri (doğru cevaba konan uyarı):")
        for x in r["yanlis_alarm_ornekleri"][:8]:
            print(f"  [{x['id']}] {x['soru'][:56]:58s} {','.join(x['kodlar'])}")
    if r["kacirilan_ornekleri"]:
        print("\nKaçırılan örnekler (yanlış cevap, uyarı yok):")
        for x in r["kacirilan_ornekleri"][:8]:
            print(f"  [{x['id']}] {x['mutasyon']:15s} {x['soru'][:50]}")

    # B7R-01 (2026-08-23): kapatma kararı ölçüye bağlıydı ama ölçü her koşumda
    # görünmüyordu — `--hepsi-acik` bayrağını hatırlamak gerekiyordu ve kimse
    # hatırlamıyordu. Karar bir kez verilip donuyor, kontroller değişirken
    # takas sessizce eskiyordu. Artık her tam koşum iki yapılandırmayı YAN YANA
    # basıyor. Kararın kendisi değişmedi; görünürlüğü değişti.
    if not a.hepsi_acik and not a.limit and r["kapali"]:
        acik = olc(None, set())
        r["acik_yakalanan"] = acik["yakalanan"]
        r["acik_yanlis_alarm"] = acik["yanlis_alarm"]
        print(f"\nKapatma kararının BUGÜNKÜ takası ({', '.join(r['kapali'])}):")
        print(f"  {'':16s} {'yakalanan':>16s} {'gereksiz bayrak':>18s}")
        print(f"  {'kapalı (şu an)':16s} {r['yakalanan']:>8d} "
              f"(%{100 * r['yakalama_orani']:4.1f}) {r['yanlis_alarm']:>9d} "
              f"(%{100 * r['yanlis_alarm_orani']:4.1f})")
        print(f"  {'açık':16s} {acik['yakalanan']:>8d} "
              f"(%{100 * acik['yakalama_orani']:4.1f}) {acik['yanlis_alarm']:>9d} "
              f"(%{100 * acik['yanlis_alarm_orani']:4.1f})")
        print(f"  Açmanın bedeli  : {acik['yakalanan'] - r['yakalanan']:+d} yakalama, "
              f"{acik['yanlis_alarm'] - r['yanlis_alarm']:+d} gereksiz bayrak")

    # Makine okunur tek satır: betikler çıktı metnine değil BUNA baksın.
    # (kontrol.bat bu satırı okuyor; hizalama değişirse kırılmasın diye.)
    print(f"\nKARNE_OZET gun={r['olcum_gunu']} gold={r['gold_sayisi']} "
          f"alarm={r['yanlis_alarm']} mutant={r['mutant_sayisi']} "
          f"yakalanan={r['yakalanan']} zbos={len(r['zamana_bagli_bos'])}")
    _gecmise_yaz(r)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print(f"\nJSON: {a.json}")


if __name__ == "__main__":
    main()
