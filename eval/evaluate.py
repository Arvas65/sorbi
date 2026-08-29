"""SorBI değerlendirme koşucusu (G-11: execution accuracy · G-12: gecikme).

Her test sorusu tam pipeline'dan geçirilir (ön işleme + RAG + üretim + doğrulama),
üretilen SQL ile gold SQL aynı veritabanında çalıştırılır ve SONUÇ KÜMELERİ
karşılaştırılır (Zhong et al. 2020 yaklaşımı — SQL metni değil, sonuç eşitliği).

A-1 (v3 SPEC): üretici (generator) artık modül düzeyinde bir global değil, dışarıdan
verilen bir nesnedir. Böylece koşucu sahte bir üreticiyle, hiçbir LLM servisi olmadan
test edilebilir — `tests/test_eval_runner.py`.

Kullanım:
    python eval/evaluate.py --doctor                     # önce bunu koş: ortam hazır mı?
    python eval/evaluate.py --db demo/hospital.db        # tam ölçüm
    python eval/evaluate.py --db demo/hospital.db --limit 5    # hızlı deneme
    python eval/evaluate.py --db demo/hospital.db --gold-only  # LLM'siz bütünlük kontrolü
"""
import argparse
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import date

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)


def _bagimlilik_hatasi(e: ModuleNotFoundError) -> None:
    """Eksik bağımlılıkta ham yığın izi yerine ne yapılacağını söyler.

    Ürünün kendi ilkesi (Nielsen 9: ne oldu + ne yapmalı) doğrulama katmanında
    uygulanıyordu ama giriş noktalarında uygulanmıyordu; en sık karşılaşılan hata
    olan 'sanal ortam etkin değil' durumu ham traceback olarak çıkıyordu.
    """
    win = platform.system() == "Windows"
    venv_dizin = os.path.join(KOK, ".venv")
    venv_var = os.path.isdir(venv_dizin)
    venv_etkin = sys.prefix != sys.base_prefix

    print(f"HATA: '{e.name}' paketi kurulu değil.\n", file=sys.stderr)
    print(f"Kullanılan Python : {sys.executable}", file=sys.stderr)
    print(f"Sanal ortam etkin : {'evet' if venv_etkin else 'HAYIR'}", file=sys.stderr)

    if venv_var and not venv_etkin:
        print("\nSebep büyük olasılıkla bu: depoda bir .venv var ama etkin değil.", file=sys.stderr)
        print("Şu komutları sırayla çalıştırın:\n", file=sys.stderr)
        if win:
            print("  .venv\\Scripts\\activate", file=sys.stderr)
        else:
            print("  source .venv/bin/activate", file=sys.stderr)
        print(f"  python {os.path.relpath(os.path.abspath(__file__), KOK)} --doctor", file=sys.stderr)
        print("\nKomut isteminin başında (.venv) görmelisiniz.", file=sys.stderr)
        print("Aktivasyondan sonra da aynı hatayı alırsanız ortam boştur:", file=sys.stderr)
    elif not venv_var:
        print("\nDepoda sanal ortam yok. Önce oluşturun:\n", file=sys.stderr)
        print("  python -m venv .venv", file=sys.stderr)
        print("  .venv\\Scripts\\activate" if win else "  source .venv/bin/activate", file=sys.stderr)
        print("\nSonra bağımlılıkları kurun:", file=sys.stderr)
    else:
        print("\nSanal ortam etkin ama paket yok. Kurun:", file=sys.stderr)

    ayrac = "\\" if win else "/"
    hafif = f"pip install -r requirements{ayrac}core.txt"
    tam = "pip install -r requirements.txt"
    genislik = max(len(hafif), len(tam))
    print(f"\n  {hafif:<{genislik}}   # ölçüm için yeterli (hafif, torch indirmez)", file=sys.stderr)
    print(f"  {tam:<{genislik}}   # tam kurulum (RAG + arayüz dahil)", file=sys.stderr)
    sys.exit(2)


try:
    from app import config, executor, guven  # noqa: E402
    from app.preprocess import resolve_dates  # noqa: E402
    from app.validator import validate_and_transpile  # noqa: E402
    from eval.tarih_sabitle import olcum_gunu, sabitle  # noqa: E402
except ModuleNotFoundError as _e:  # pragma: no cover - kurulum hatası yolu
    _bagimlilik_hatasi(_e)

HEDEF_ACCURACY = 0.80          # G-11
HEDEF_GECIKME_P95_S = 10.0     # G-12


# --------------------------------------------------------------------- yardımcılar

def _normalize(rows: list) -> set:
    """Sonuç kümesini kıyaslanabilir hale getir: satır sırası önemsiz,
    ondalıklar 2 haneye yuvarlı, None -> ''."""
    out = set()
    for r in rows:
        norm = tuple("" if v is None else (round(v, 2) if isinstance(v, float) else v) for v in r)
        out.add(norm)
    return out


def _calisma_agaci_kirli() -> bool:
    """İşlenmemiş değişiklik var mı?

    Varsa damgadaki commit hash'i KOŞULAN KODU göstermez, son işlemeyi gösterir.
    2026-08-16 ve 2026-08-22 koşumlarının ikisi de `ffe5db3` damgası taşıyor
    ama aralarında altı haftalık iş var — çünkü hiçbiri işlenmemişti. Damga
    sessizce yanlış söylüyordu.
    """
    git = shutil.which("git")
    if not git:
        return False
    try:
        out = subprocess.run([git, "status", "--porcelain"],  # noqa: S603
                             capture_output=True, text=True, timeout=10, check=False,
                             cwd=KOK)
        return bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _commit_hash() -> str:
    """Ölçüm damgası için commit. Git yoksa 'bilinmiyor' döner — ölçüm yine de koşar."""
    git = shutil.which("git")
    if not git:
        return "bilinmiyor"
    try:
        out = subprocess.run([git, "rev-parse", "--short", "HEAD"],  # noqa: S603
                             capture_output=True, text=True, timeout=5, check=False,
                             cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return out.stdout.strip() or "bilinmiyor"
    except (OSError, subprocess.SubprocessError):
        return "bilinmiyor"


def _model_adi(mode: str) -> str:
    return config.API_MODEL if mode == "api" else config.LOCAL_MODEL


def yukle_testset(yol: str) -> list:
    with open(yol, encoding="utf-8") as f:
        return [json.loads(satir) for satir in f if satir.strip()]


# --------------------------------------------------------------------- doctor

def doctor(mode: str) -> int:
    """Ölçümden ÖNCE koşulur: ortam hazır mı, hazır değilse tam olarak ne yapmalı.

    Bu, v3 SPEC § 2'deki 'Ollama/Windows Vulkan' varsayımını doğrulayan adımdır.
    Çıkış kodu 0 ise ölçüm koşulabilir.
    """
    print("SorBI ölçüm ortamı kontrolü")
    print("=" * 60)
    print(f"Python      : {platform.python_version()} ({platform.system()} {platform.machine()})")
    print(f"Mod         : {mode}")
    print(f"Model       : {_model_adi(mode)}")
    sorun = []

    if mode == "api":
        if not config.API_KEY:
            sorun.append("SORBI_API_KEY tanımlı değil — API modu çalışmaz.")
        else:
            print(f"API adresi  : {config.API_BASE}")
        if sorun:
            print("\n".join("  ! " + s for s in sorun))
            return 1
        print(f"API adresi  : {config.API_BASE}")

        # Yerel modda gerçek bir üretim denemesi yapıyoruz; API modunda
        # yapmamak tutarsızdı. Anahtarın geçerli olduğunu, modelin var
        # olduğunu ve kotanın açık olduğunu ancak çağırarak biliriz.
        from app import generator
        print("\n  Tek soruluk deneme koşuluyor...")
        t0 = time.time()
        try:
            sonuc = generator.generate_api(
                "kaç doktor var",
                "TABLO doktor\nKOLONLAR: doktor_id (INTEGER), ad (TEXT)")
        except generator.KotaHatasi as e:
            print(f"  ! KOTA/HIZ SINIRI: {str(e)[:300]}")
            print("\n    Ölçüm ALINMAMALI: kota aşımı doğruluk kaybı gibi görünür.")
            print("    SORBI_API_BEKLEME ile soru başına bekleme koyun (ör. 4).")
            return 1
        except generator.LlmError as e:
            print(f"  ! API hata verdi:\n    {str(e)[:400]}")
            print("\n    Anahtar, adres ve model adını kontrol edin:")
            print(f"      SORBI_API_BASE  = {config.API_BASE}")
            print(f"      SORBI_API_MODEL = {config.API_MODEL}")
            return 1
        gecen = time.time() - t0
        print(f"  + üretim çalıştı ({gecen:.1f} sn), guven={sonuc.get('guven')}")
        print(f"    üretilen SQL: {sonuc.get('sql', '')[:120]}")
        print("  + gizlilik: bağlamdaki DEĞERLER blokları dış servise gitmiyor "
              "(mask_context)")
        print(f"\nDOCTOR_OZET hizlandirma=api model={config.API_MODEL} "
              f"deneme_sn={gecen:.1f} olcum_gunu={olcum_gunu()}")
        if gecen > HEDEF_GECIKME_P95_S:
            print(f"\n  ~ Uyarı: tek soru {gecen:.1f} sn sürdü, "
                  f"G-12 hedefi {HEDEF_GECIKME_P95_S:.0f} sn.")
        print("=" * 60)
        print("ORTAM HAZIR — ölçümü koşabilirsiniz.")
        return 0

    import requests
    print(f"Ollama      : {config.OLLAMA_URL}")

    # 1) Servis ayakta mı
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        r.raise_for_status()
        modeller = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        print(f"\n  ! Ollama'ya ulaşılamadı: {type(e).__name__}: {str(e)[:120]}")
        print("\n  Yapılacak:")
        print("    1. Ollama kurulu değilse: https://ollama.com")
        print("    2. Kuruluysa servisi başlatın:  ollama serve")
        return 1
    print(f"  + servis ayakta, {len(modeller)} model yüklü")

    # 2) Hedef model var mı
    hedef = config.LOCAL_MODEL
    if not any(m == hedef or m.startswith(hedef.split(":")[0] + ":") for m in modeller):
        print(f"\n  ! '{hedef}' yüklü değil. Yüklü olanlar: {', '.join(modeller) or '(yok)'}")
        print(f"\n  Yapılacak:  ollama pull {hedef}")
        return 1
    print(f"  + model bulundu: {hedef}")

    # 3) Gerçek bir üretim denemesi — Vulkan çökmesi burada yakalanır
    from app import generator
    print("\n  Tek soruluk deneme koşuluyor (bu adım Vulkan çökmesini yakalar)...")
    t0 = time.time()
    try:
        sonuc = generator.generate_local(
            "kaç doktor var",
            "TABLO doktor\nKOLONLAR: doktor_id (INTEGER), ad (TEXT)")
    except generator.LlmError as e:
        gecen = time.time() - t0
        print(f"  ! Model {gecen:.1f} sn sonra hata verdi:\n    {str(e)[:400]}")
        print("\n  Bilinen saha sorunu — Windows + Ollama Vulkan arka ucu (0xe06d7363):")
        print("    CPU'ya zorlayıp yeniden deneyin:")
        print("      PowerShell:  $env:OLLAMA_LLM_LIBRARY='cpu_avx2'; ollama serve")
        print("      cmd:         set OLLAMA_LLM_LIBRARY=cpu_avx2 && ollama serve")
        print("    CPU'da da olmuyorsa daha küçük bir model deneyin:")
        print("      ollama pull qwen2.5:1.5b-instruct")
        print("      set SORBI_LOCAL_MODEL=qwen2.5:1.5b-instruct")
        return 1
    gecen = time.time() - t0
    print(f"  + üretim çalıştı ({gecen:.1f} sn), guven={sonuc.get('guven')}")
    print(f"    üretilen SQL: {(sonuc.get('sql') or '(boş)')[:80]}")

    # Model GPU'da mı CPU'da mı? (saha kaydı 2026-08-16: iki saatlik teşhis)
    # Ollama, GPU keşfi başarısız olursa sessizce CPU'ya düşer ve 6-10 kat yavaşlar.
    # Hiçbir hata mesajı vermez; tek belirti sürelerdir. Artık kendimiz bakıyoruz.
    hizlandirma = "bilinmiyor"
    try:
        ps = requests.get(f"{config.OLLAMA_URL}/api/ps", timeout=10).json()
        yuklu = [m for m in ps.get("models", []) if m.get("name", "").startswith(hedef.split(":")[0])]
        if yuklu:
            toplam = yuklu[0].get("size", 0)
            vram = yuklu[0].get("size_vram", 0)
            if toplam and vram == 0:
                hizlandirma = "cpu"
                print("\n  ! Model TAMAMEN CPU'da koşuyor — GPU kullanılmıyor.")
                print("    Beklenen etki: 6-10 kat yavaşlık. G-12 bu haliyle karşılanamaz.")
                print("\n    Teşhis için Ollama'yı önplanda, ayrıntılı günlükle başlatın:")
                print("      taskkill /F /IM \"ollama app.exe\" & taskkill /F /IM ollama.exe")
                print("      set OLLAMA_VULKAN=0")
                print("      set OLLAMA_DEBUG=1")
                print("      ollama serve")
                print("    'discovering available GPUs' satırından sonrasına bakın.")
                print("    Bilinen sebep: Vulkan arka ucu açıkken GPU keşfi tümden")
                print("    başarısız olabiliyor — CUDA'ya sıra gelmiyor (OLLAMA_VULKAN=0).")
            elif vram and toplam:
                hizlandirma = "gpu"
                print(f"\n  + Model GPU'da: {100 * vram / toplam:.0f}% VRAM'de "
                      f"({vram / 1e9:.1f} / {toplam / 1e9:.1f} GB)")
    except Exception as e:
        # Sessizce yutmuyoruz — BULGU-02'nin aynısını yazmak olurdu.
        print(f"\n  ~ GPU/CPU durumu okunamadı ({type(e).__name__}); ölçüm yine de koşabilir.")

    # Makine okunur tek satır — betikler çıktı metnini ayrıştırmasın.
    print(f"\nDOCTOR_OZET hizlandirma={hizlandirma} model={hedef} "
          f"deneme_sn={gecen:.1f} olcum_gunu={olcum_gunu()}")

    if gecen > HEDEF_GECIKME_P95_S:
        print(f"\n  ~ Uyarı: tek soru {gecen:.1f} sn sürdü, G-12 hedefi {HEDEF_GECIKME_P95_S:.0f} sn.")
        print("    Ölçüm koşabilir ama G-12 muhtemelen karşılanmayacak; bu da bir bulgudur.")

    print("\n" + "=" * 60)
    print("ORTAM HAZIR — ölçümü koşabilirsiniz:")
    print("  python eval/evaluate.py --db demo/hospital.db")
    return 0


# --------------------------------------------------------------------- gold-only

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


# --------------------------------------------------------------------- tek soru

def run_one(item: dict, idx, mode: str, gen_mod) -> dict:
    """Tek bir test sorusunu uçtan uca koşar.

    gen_mod: `generate(question, context, mode)` ve
             `repair(question, context, bad_sql, error, mode)` sağlayan herhangi bir nesne.
             Gerçek `app.generator` ya da testlerdeki sahte üretici olabilir (A-1).
    """
    t0 = time.time()
    rec = {"id": item["id"], "soru": item["soru"], "zorluk": item["zorluk"],
           "join": item["join"], "dogru": False, "asama": "", "sql": "",
           "onarim": False, "bayraklar": []}

    def bitir(asama: str) -> dict:
        rec["asama"] = asama
        rec["sure_s"] = round(time.time() - t0, 2)
        return rec

    # İP-23: soruya yazılan mutlak tarih aralığı da ölçüm gününe sabitlenir.
    # SQL'i sabitleyip istemi sabitlememek, modele Eylül'ü gösterip sorguyu
    # Ağustos'ta koşturmak olurdu — kendi ölçümümüzü kendimiz bozardık.
    _gun = olcum_gunu()
    annotated, _ = resolve_dates(item["soru"], date.fromisoformat(_gun))
    context, _ = idx.retrieve(item["soru"])

    try:
        gen, kullanilan_mod = gen_mod.generate(annotated, context, mode)
        # YENİ-C (2026-08-23): `generate` GERÇEKTEN kullanılan modu dönüyor ve
        # bu değer atılıyordu; damga koşulsuz api modelini yazıyordu. Sessiz bir
        # yerele düşüş (kota, ağ) yine "gemini" damgasıyla raporlanırdı — yani
        # ölçüm hangi modeli ölçtüğünü bilmiyordu. Artık soru bazında kayıtlı.
        rec["mod"] = kullanilan_mod
    except Exception as e:
        # Kota aşımı bir MODEL HATASI DEĞİLDİR; ayrı aşama adı alır ki
        # özet onu doğruluk kaybı gibi saymasın.
        if type(e).__name__ == "KotaHatasi":
            return bitir(f"kota_asildi: {str(e)[:100]}")
        return bitir(f"uretim_hatasi: {type(e).__name__}: {str(e)[:100]}")

    rec["sql"] = gen.get("sql", "")
    rec["guven"] = gen.get("guven", 0)

    v = validate_and_transpile(rec["sql"], target_dialect=config.TARGET_DIALECT,
                               known_tables=idx.known_tables,
                               known_columns=idx.known_columns)
    if not v.ok:  # tek öz-onarım denemesi (pipeline ile aynı davranış)
        try:
            gen2, _ = gen_mod.repair(annotated, context, rec["sql"], v.error, mode)
        except Exception as e:
            return bitir(f"onarim_hatasi: {type(e).__name__}: {str(e)[:100]}")
        rec["sql"] = gen2.get("sql", "")
        rec["onarim"] = True
        v = validate_and_transpile(rec["sql"], target_dialect=config.TARGET_DIALECT,
                                   known_tables=idx.known_tables,
                                   known_columns=idx.known_columns)
        if not v.ok:
            return bitir(f"dogrulama_reddi: {v.error[:120]}")

    # İP-23: gold ve tahmin AYNI günü görmeli. Sabitleme yalnız çalıştırma
    # anında yapılır; kullanıcıya/rapora giden SQL modelin yazdığı SQL'dir.
    pred = executor.run(sabitle(v.sql, _gun))
    if pred.status == "CALISMA_HATASI" and not rec["onarim"]:
        try:
            gen3, _ = gen_mod.repair(annotated, context, v.sql, pred.error, mode)
        except Exception as e:
            return bitir(f"onarim_hatasi: {type(e).__name__}: {str(e)[:100]}")
        rec["onarim"] = True
        v2 = validate_and_transpile(gen3.get("sql", ""), target_dialect=config.TARGET_DIALECT,
                                    known_tables=idx.known_tables,
                                    known_columns=idx.known_columns)
        if v2.ok:
            rec["sql"] = gen3["sql"]
            v = v2
            pred = executor.run(sabitle(v2.sql, _gun))
    if pred.status != "BASARILI":
        return bitir(f"calisma_hatasi: {pred.status}")

    gold = executor.run(sabitle(item["gold_sql"], _gun))
    if gold.status != "BASARILI":
        # Test setinin kendisi bozuksa görünsün — accuracy'ye hata olarak yazılmaz
        return bitir(f"GOLD_HATASI: {gold.error[:120]}")

    rec["dogru"] = _normalize(pred.rows) == _normalize(gold.rows)
    # B-7 (İP-03c): güven kontrolü SONUCU değiştirmez, yalnız bayrak koyar.
    # Doğruluğu bilinen 101 soruya karşı koştuğumuz için kontrolün kendi
    # isabet/yanlış alarm oranını burada ölçebiliyoruz.
    g = guven.degerlendir(
        item["soru"], v.sql, pred.rowcount, kolon_sayisi=len(pred.columns or []),
        satirlar=pred.rows,
        bilinen_degerler=getattr(idx, "bilinen_degerler", None),
        kolonlar={k for kolonlar in (getattr(idx, "known_columns", None) or {}).values()
                  for k in kolonlar},
        sozluk=(getattr(idx, "glossary", None) or {}).get("terms", {}))
    rec["bayraklar"] = g.kodlar
    return bitir("esit" if rec["dogru"] else "sonuc_farkli")


# --------------------------------------------------------------------- raporlama

def ozetle(results: list) -> dict:
    n = len(results)
    dogru = sum(r["dogru"] for r in results)
    sureler = sorted(r.get("sure_s", 0.0) for r in results)
    ozet = {
        "n": n,
        "dogru": dogru,
        "accuracy": dogru / n if n else 0.0,
        "onarim_sayisi": sum(1 for r in results if r.get("onarim")),
        "p50_s": statistics.median(sureler) if sureler else 0.0,
        "p95_s": (sureler[min(len(sureler) - 1, int(round(0.95 * (len(sureler) - 1))))]
                  if sureler else 0.0),
        "en_yavas_5": sorted(results, key=lambda r: -r.get("sure_s", 0))[:5],
        "kirilim": {},
    }
    for anahtar in ("zorluk", "join"):
        ozet["kirilim"][anahtar] = {}
        for val in sorted({r[anahtar] for r in results}, key=str):
            alt = [r for r in results if r[anahtar] == val]
            ozet["kirilim"][anahtar][str(val)] = {
                "dogru": sum(r["dogru"] for r in alt), "toplam": len(alt)}
    # Neden yanlış: aşama dağılımı
    ozet["asama_dagilimi"] = {}
    for r in results:
        kok = r["asama"].split(":")[0]
        ozet["asama_dagilimi"][kok] = ozet["asama_dagilimi"].get(kok, 0) + 1

    # B-7: sessiz yanlış — sorgu çalıştı, sonuç döndü, cevap yanlış.
    # Doğruluk yüzdesinden ayrı izlenir çünkü riski farklıdır: yakalanan hata
    # kullanıcıyı uyarır, sessiz yanlış yanlış sayıyı yönetime taşır (B7 riski).
    sessiz = sum(1 for r in results if r["asama"] == "sonuc_farkli")
    # BULGU-06 (2026-08-23): bu sayı raporda "yakalanan" diye geçiyordu, güven
    # karnesindeki "yakalanan" ise B-7 BAYRAĞI demekti. Aynı raporda "yakalanan
    # hata 0/101" ve "sessiz yanlışın 6/30'u yakalandı" yan yana duruyordu;
    # çelişki değil, iki tanım — ama okuyucu bunu bilemez. Bu taraf artık
    # REDDEDİLEN adını taşıyor: hattın cevabı kullanıcıya HİÇ vermediği durum.
    reddedilen = sum(1 for r in results
                     if r["asama"].startswith(("dogrulama_reddi", "calisma_hatasi",
                                               "uretim_hatasi", "onarim_hatasi")))
    yanlis = n - dogru
    ozet["sessiz_yanlis"] = sessiz
    ozet["reddedilen"] = reddedilen
    # Eski ad geriye dönük uyum için duruyor; yeni kod `reddedilen` kullanmalı.
    ozet["yakalanan_hata"] = reddedilen
    # Hangi mod kaç soruyu cevapladı (YENİ-C). Damga tek bir model adı yazar;
    # bu satır o adın koşumun TAMAMI için geçerli olup olmadığını gösterir.
    mod_dagilimi: dict[str, int] = {}
    for r in results:
        if r.get("mod"):
            mod_dagilimi[r["mod"]] = mod_dagilimi.get(r["mod"], 0) + 1
    ozet["mod_dagilimi"] = mod_dagilimi
    ozet["sessiz_yanlis_orani"] = sessiz / n if n else 0.0
    # Yanlışların kaçta kaçı sessiz? Asıl izlenecek sayı bu.
    ozet["yanlislarda_sessiz_pay"] = sessiz / yanlis if yanlis else 0.0
    # Kota aşımı ayrı tutulur. Ücretsiz katmanda 101 sorunun 40'ı 429 alsa
    # doğruluk %20 görünür ve bu tamamen yanlış bir sonuçtur — model değil,
    # kota ölçülmüş olur.
    ozet["kota_asildi"] = sum(1 for r in results if r["asama"].startswith("kota_asildi"))
    ozet["olculebilen"] = n - ozet["kota_asildi"]
    ozet["accuracy_olculebilen"] = (dogru / ozet["olculebilen"]
                                    if ozet["olculebilen"] else 0.0)
    ozet["guven"] = guven_ozeti(results)
    return ozet


def guven_ozeti(results: list) -> dict:
    """Güven kontrolünün KENDİ karnesi (İP-03c).

    Yalnız çalışan sorgular sayılır: reddedilen ya da patlayan sorguda kullanıcı
    zaten uyarılmıştır, bayrak koymanın bir değeri yoktur. Değerlendirme evreni
    "temiz bir tablo dönen" cevaplardır — sessiz yanlışın yaşadığı yer.

    İki sayı önemli ve ikisi ters yönde çekiyor:
    - **yakalama**: sessiz yanlışların kaçı bayraklandı (yükselmesi iyi)
    - **yanlis_alarm**: doğru cevapların kaçı bayraklandı (düşmesi iyi)

    Sürekli bağıran bir uyarı, hiç uyarmayandan kötüdür: kullanıcı bir süre
    sonra bayrağı okumayı bırakır ve sessiz yanlış geri döner. Bu yüzden
    yanlış alarm oranı, yakalama oranıyla aynı raporda durur.
    """
    kapali = set(config.GUVEN_KAPALI)

    def acik(r):
        return [k for k in r.get("bayraklar", []) if k not in kapali]

    calisan = [r for r in results if r["asama"] in ("esit", "sonuc_farkli")]
    dogrular = [r for r in calisan if r["dogru"]]
    yanlislar = [r for r in calisan if not r["dogru"]]
    yakalanan = [r for r in yanlislar if acik(r)]
    alarm = [r for r in dogrular if acik(r)]
    ozet = {
        "evren": len(calisan),
        "sessiz_yanlis": len(yanlislar),
        "yakalanan": len(yakalanan),
        "yakalama_orani": len(yakalanan) / len(yanlislar) if yanlislar else 0.0,
        "dogru_cevap": len(dogrular),
        "yanlis_alarm": len(alarm),
        "yanlis_alarm_orani": len(alarm) / len(dogrular) if dogrular else 0.0,
        "kapali": sorted(kapali),
        "kodlar": {},
    }
    # Bayraklananların içinde gerçekten yanlış olanların payı — kullanıcının
    # uyarıyı ciddiye alıp almayacağını belirleyen sayı budur.
    bayrakli = len(yakalanan) + len(alarm)
    ozet["isabet"] = len(yakalanan) / bayrakli if bayrakli else 0.0
    for kod in guven.TUM_KODLAR:
        d = sum(1 for r in yanlislar if kod in r.get("bayraklar", []))
        y = sum(1 for r in dogrular if kod in r.get("bayraklar", []))
        if d or y:
            ozet["kodlar"][kod] = {"yanlista": d, "dogruda": y,
                                   "kapali": kod in kapali,
                                   "isabet": d / (d + y) if (d + y) else 0.0}
    return ozet


def onceki_olcum(yol: str) -> dict | None:
    """Bir önceki koşumun özetini okur (varsa). Üzerine yazmadan ÖNCE çağrılmalı.

    Amaç: 'bu değişiklik işe yaradı mı' sorusunun cevabı raporun içinde dursun,
    iki dosyayı yan yana açmak gerekmesin.
    """
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    ozet = veri.get("ozet")
    if not ozet or "accuracy" not in ozet:
        return None
    return {"accuracy": ozet["accuracy"], "n": ozet.get("n"),
            "olcum_gunu": (veri.get("damga") or {}).get("olcum_gunu"),
            "p50_s": ozet.get("p50_s"), "p95_s": ozet.get("p95_s"),
            "sessiz_yanlis": ozet.get("sessiz_yanlis"),
            "damga": veri.get("damga", {}),
            # Soru bazlı sonuç: eşli karşılaştırmanın (McNemar) tek girdisi.
            # Toplam yüzde eşli bir karar veremez; hangi SORULARIN yön
            # değiştirdiğini bilmek gerekir (BULGU-09/10).
            "sorular": {str(r.get("id")): bool(r.get("dogru"))
                        for r in (veri.get("results") or []) if r.get("id") is not None}}


def _mcnemar_p(b: int, c: int) -> float:
    """İki yönlü tam (exact) McNemar olasılığı. `scipy` gerektirmez.

    b: önce doğru → şimdi yanlış · c: önce yanlış → şimdi doğru
    Sıfır hipotezi: bir sorunun yön değiştirmesi yazı-tura kadar rastlantısal.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    kuyruk = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * kuyruk)


# Kaç soruluk net fark "ölçülebilir" sayılsın. Eşik değil, ikinci bir emniyet:
# p küçük olsa bile tek soruluk bir fark için CI'ı kırmızıya döndürmek
# gürültüyü olay yerine koymak olurdu.
REGRESYON_ASGARI_FARK = 3
REGRESYON_P_ESIGI = 0.05


def regresyon_karari(onceki: dict | None, results: list) -> dict | None:
    """SPEC A-4'ün regresyon kapısı — ham puan farkı yerine EŞLİ karar.

    Neden değişti (BULGU-10, 2026-08-23). A-4 "doğruluk son ölçümden 3 puandan
    fazla düşerse CI kırmızı" diyordu. Ölçülen api gürültü tabanı: aynı kod,
    aynı ayarlar, iki koşum arasında **7 ayrık soru** (McNemar p = 1,000).
    Saf gürültüde |net| >= 3 soru çıkma olasılığı **yaklaşık %45.** Yani kapı,
    hiçbir şey olmadan neredeyse her iki koşumda bir ateşleyecek biçimde
    kalibreydi — ve ateşlemeye başlayan bir kapı kapatılan bir kapıdır.

    Yeni kural aynı soruların yön değişimine bakar:

        b = önce doğru, şimdi yanlış        c = önce yanlış, şimdi doğru
        REGRESYON  <=>  b - c >= 3  VE  McNemar p < 0,05

    "3 puan" atılmadı; ölçülebilir bir farkın İÇİNE alındı. Gürültü artık
    kapıyı açamaz, gerçek bir gerileme hâlâ açar.
    """
    if not onceki or not onceki.get("sorular"):
        return None
    eski = onceki["sorular"]
    ortak = [(str(r["id"]), bool(r.get("dogru"))) for r in results
             if str(r.get("id")) in eski]
    if not ortak:
        return None
    b = sum(1 for i, yeni in ortak if eski[i] and not yeni)
    c = sum(1 for i, yeni in ortak if not eski[i] and yeni)
    p = _mcnemar_p(b, c)
    if b - c >= REGRESYON_ASGARI_FARK and p < REGRESYON_P_ESIGI:
        karar = "REGRESYON"
    elif c - b >= REGRESYON_ASGARI_FARK and p < REGRESYON_P_ESIGI:
        karar = "IYILESME"
    else:
        karar = "FARK_YOK"
    return {"karar": karar, "eslesen": len(ortak), "bozulan": b, "duzelen": c,
            "net": c - b, "p": p,
            "asgari_fark": REGRESYON_ASGARI_FARK, "p_esigi": REGRESYON_P_ESIGI}


def regresyon_satiri(k: dict) -> str:
    """Kararı tek satırda, hükmü ve dayanağıyla."""
    if k["karar"] == "FARK_YOK":
        bas = "FARK YOK"
        aciklama = ("ölçülebilir bir doğruluk farkı yok"
                    if k["bozulan"] or k["duzelen"] else "hiçbir soru yön değiştirmedi")
    elif k["karar"] == "REGRESYON":
        bas, aciklama = "REGRESYON", "gerileme gürültüyle açıklanamıyor"
    else:
        bas, aciklama = "İYİLEŞME", "iyileşme gürültüyle açıklanamıyor"
    return (f"{bas} — {k['eslesen']} eşleşen soru, {k['bozulan']} bozuldu, "
            f"{k['duzelen']} düzeldi (net {k['net']:+d}), McNemar p = {k['p']:.3f}; "
            f"{aciklama}.")


def karsilastirilamaz(onceki: dict, ozet: dict, damga: dict) -> str | None:
    """İki koşum aynı şeyi ölçmüyorsa sebebini söyler, yoksa None.

    Sessizce karşılaştırmak en pahalı hatadır: cetvel değiştiği hâlde yüzde
    farkı bir "iyileşme" ya da "gerileme" gibi okunur. Referans günü de bu
    listeye 2026-08-20'de eklendi — 13 zamana bağlı soru yüzünden farklı
    günlere sabitlenmiş iki koşum farklı bir seti ölçer.
    """
    if onceki.get("n") != ozet["n"]:
        return (f"Önceki koşum {onceki.get('n')} soruluk, bu koşum {ozet['n']} soruluk "
                "bir setle yapıldı. Test seti değiştiğinde yüzdeler aynı şeyi ölçmez.")
    eski_gun = onceki.get("olcum_gunu")
    yeni_gun = damga.get("olcum_gunu")
    if eski_gun and yeni_gun and eski_gun != yeni_gun:
        return (f"Önceki koşum `{eski_gun}` gününe, bu koşum `{yeni_gun}` gününe "
                "sabitlenmiş. Test setinin 13 sorusu zamana bağlı; farklı referans "
                "günü farklı bir cetvel demektir.")
    if eski_gun is None and yeni_gun:
        return ("Önceki koşumda referans günü kayıtlı değil (İP-23 öncesi). O koşum "
                "gerçek takvimle alınmıştır ve zamana bağlı 13 soruda bu koşumla "
                "aynı şeyi ölçmez.")

    # Üretim ayarları. Bunlar `olcum-al` skill'inde "karşılaştırılabilirlik
    # koşulu" diye yazılıydı ama KOD yalnız n ve referans günü denetliyordu —
    # kuralın belgede olup kodda olmaması, ADR-1'in koda inmemesiyle aynı
    # aile. 2026-08-22 koşumunda num_ctx 4096'dan 8192'ye çıkmıştı ve bu
    # denetlenmiyordu; referans günü de değişmeseydi 6 puanlık fark gerçek
    # bir gerileme gibi raporlanacaktı.
    eski_damga = onceki.get("damga") or {}
    for alan, aciklama in (
        ("model", "farklı model"),
        ("temperature", "farklı sıcaklık"),
        ("seed", "farklı seed"),
        ("num_ctx", "farklı bağlam penceresi"),
        ("ornek_degerler", "farklı değer örnekleme ayarı"),
    ):
        eski, yeni = eski_damga.get(alan), damga.get(alan)
        if eski is not None and yeni is not None and str(eski) != str(yeni):
            return (f"Önceki koşum `{alan}={eski}`, bu koşum `{alan}={yeni}` ile "
                    f"yapıldı ({aciklama}). Üretim ayarı değiştiğinde yüzdeler "
                    "aynı şeyi ölçmez.")
    return None


def g12_kapsam_disi(damga: dict) -> str | None:
    """G-12 yerel çıkarım modunu ölçer. Başka bir modda hüküm verilmez.

    BULGU-03 (2026-08-22, nöbet): api modunda alınan p95 3,76 sn için rapor
    "KARŞILANDI" yazdı. G-12'nin kendi metni ve v3 SPEC A-3 hedefi *yerel
    çıkarım modu* içindir; api modunda ölçülen süre ağ gidiş-dönüşü + başka
    birinin donanımıdır. `karsilastirilamaz()`'ın doğruluk tarafında
    engellediği hatanın gecikme tarafındaki hâli: cetvel değişti, sayı aynı
    kutuya yazıldı. Sayılar yerinde durur, yalnız HÜKÜM düşer.
    """
    mod = damga.get("mod")
    if mod and mod != "local":
        return (f"Bu koşum `mod={mod}` ile alındı. G-12 *yerel çıkarım modu* için "
                "tanımlıdır; api modunda ölçülen süre SorBI'nin çıkarımını değil dış "
                "servisin altyapısını ve ağ gecikmesini ölçer. Sayılar aşağıda durur, "
                "hüküm verilmez.")
    return None


def _fark_satiri(yeni: float, eski: float | None, birim: str = "puan",
                 yukselmesi_iyi: bool = True) -> str:
    if eski is None:
        return "—"
    d = yeni - eski
    # Yuvarlama yalanı: 2,26 -> 2,29 farkı "+0.0 sn (gerileme)" diye yazılıyordu.
    # Basılan hassasiyette sıfıra yuvarlanan bir fark hakkında hüküm verilmez.
    if round(d, 1) == 0:
        return "değişmedi"
    iyi = (d > 0) if yukselmesi_iyi else (d < 0)
    return f"{'+' if d > 0 else ''}{d:.1f} {birim} ({'iyileşme' if iyi else 'gerileme'})"


def _kota_uyarisi(ozet: dict) -> str:
    """Kota aşımı olduysa manşet sayının NEYİ ölçtüğünü söyler."""
    k = ozet.get("kota_asildi") or 0
    if not k:
        return ""
    return (f"\n> **DİKKAT: {k} soru kota/hız sınırına takıldı ve hiç ölçülemedi.**\n"
            f"> Yukarıdaki yüzde bu {k} soruyu YANLIŞ sayıyor; oysa cevaplanmadılar.\n"
            f"> Ölçülebilen {ozet.get('olculebilen')} soru üzerinden doğruluk: "
            f"**%{100 * ozet.get('accuracy_olculebilen', 0):.1f}**.\n"
            "> Bu koşum bir model karşılaştırması için KULLANILAMAZ; kota\n"
            "> aşımı giderilip tekrarlanmalıdır.\n")


def _mod_satiri(ozet: dict, damga: dict) -> str:
    """Damga tek bir model adı yazar; koşumun tamamı o modelle mi koştu?

    YENİ-C: `generate` gerçekten kullanılan modu dönüyor ama atılıyordu.
    Sessiz bir yerele düşüş (kota, ağ kesintisi) yine api damgasıyla
    raporlanırdı. Bu satır iddiayı sayıya bağlar.
    """
    dagilim = ozet.get("mod_dagilimi") or {}
    n = ozet.get("n") or 0
    if not dagilim:
        return "ölçülmedi"
    beklenen = damga.get("mod")
    parcalar = ", ".join(f"`{k}` {v}/{n}" for k, v in sorted(dagilim.items()))
    if beklenen and set(dagilim) == {beklenen}:
        return f"{parcalar} — damgayla tutarlı"
    return f"{parcalar} — **damga `{beklenen}` diyor, koşum bölündü**"


def _guven_bolumu(g: dict) -> str:
    """Güven kontrolünün karnesi — rapora her koşumda girer.

    Kontrolün kendisi ölçülmeden açılmaz: bir uyarı sistemi hem kaçırdığında
    hem gereksiz bağırdığında zarar verir ve ikisi ters yönde çekilir.
    """
    if not g or not g.get("evren"):
        return ""
    satirlar = [
        "\n## Güven kontrolü karnesi (B-7)\n",
        "Aşağıdaki sayılar cevabın doğruluğunu değil, **uyarı sisteminin**",
        "başarısını ölçer. Değerlendirme evreni yalnız temiz bir tablo dönen",
        f"cevaplardır ({g['evren']} soru) — sessiz yanlışın yaşadığı yer.\n",
        "| Ölçü | Değer | Yön |",
        "|------|-------|-----|",
        f"| Sessiz yanlışların **bayraklananı** | **{g['yakalanan']}/{g['sessiz_yanlis']}** "
        f"(%{100 * g['yakalama_orani']:.0f}) | yükselmeli |",
        f"| Doğru cevaba konan gereksiz bayrak | {g['yanlis_alarm']}/{g['dogru_cevap']} "
        f"(%{100 * g['yanlis_alarm_orani']:.0f}) | düşmeli |",
        f"| Bayrak isabeti (bayraklının kaçı gerçekten yanlış) | "
        f"**%{100 * g['isabet']:.0f}** | yükselmeli |\n",
    ]
    if g.get("kodlar"):
        satirlar += [
            "### Kontrol bazında\n",
            "İsabeti düşük bir kontrol, koddan silinmeden `SORBI_GUVEN_KAPALI` ile",
            "kapatılır; böylece sonraki ölçüm aynı çizelgeyle karşılaştırılabilir.\n",
            "| Kontrol | Yanlış cevapta | Doğru cevapta | İsabet |",
            "|---------|----------------|----------------|--------|",
        ]
        for kod, v in sorted(g["kodlar"].items(), key=lambda x: -x[1]["isabet"]):
            ad = f"`{kod}`" + (" _(kapalı)_" if v.get("kapali") else "")
            satirlar.append(f"| {ad} | {v['yanlista']} | {v['dogruda']} | "
                            f"%{100 * v['isabet']:.0f} |")
        satirlar.append("")
    return "\n".join(satirlar) + "\n"


def _belirlenim(mode: str) -> str:
    """Damga, uygulanmamış bir ayarı uygulanmış gösteremez (BULGU-08).

    Metin KODDAN türetilir, elle yazılmaz: `generator.API_BELIRLENIM_ALANLARI`
    isteğin gerçekten taşıdığı alanların listesidir. Biri isteğe eklenir ya da
    çıkarılırsa damga kendiliğinden düzelir — "ADR'yi yazıp koda indirmemek"
    hatasının damga tarafındaki hâli tam olarak buydu.

    Gönderilmiş olmak UYGULANMIŞ olmak değildir: barındırılan modellerin çoğu
    `seed`'i sessizce yok sayar. Bu yüzden api tarafında hüküm verilmiyor,
    yalnız ne gönderildiği yazılıyor. Belirlenimin tek kanıtı tekrardır.
    """
    if mode == "local":
        return f"seed={config.SEED}, num_ctx={config.NUM_CTX} — Ollama isteğine konuyor"
    try:
        from app import generator
        return generator.belirlenim_durumu()
    except Exception:                    # noqa: BLE001 - damga LLM'siz de yazılabilmeli
        return "bilinmiyor (üretici içe aktarılamadı)"


def _damga(mode: str) -> dict:
    return {
        "tarih": date.today().isoformat(),
        # Koşumun GERÇEK günü yukarıda; aşağıdaki ise sorguların gördüğü gün.
        # İkisi ayrı: cetveli sabitlemenin anlamı bu (İP-23).
        "olcum_gunu": olcum_gunu(),
        "commit": _commit_hash() + (" (+islenmemis degisiklikler)"
                                    if _calisma_agaci_kirli() else ""),
        "model": _model_adi(mode),
        "mod": mode,
        "db_url": config.DB_URL,
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        # Karşılaştırmayı geçersiz kılabilecek her ayar damgaya girer.
        "temperature": config.TEMPERATURE,
        "seed": config.SEED,
        "num_ctx": config.NUM_CTX,
        "ornek_degerler": config.ORNEK_DEGERLER,
        # `seed` ve `num_ctx` yalnız Ollama isteğine konur; `generate_api` ikisini
        # de göndermez. Damga onları yine de yazıyordu ve var olmayan bir
        # belirlenim kontrolünü uygulanmış gibi gösteriyordu — ölçülmemiş şeyi
        # iddia etme kuralının ihlali. 2026-08-23'te iki api koşumu aynı
        # temperature/seed ile 7 soruda ayrıştı; sebebi buydu.
        "belirlenim": _belirlenim(mode),
    }


def rapor_yaz(ozet: dict, damga: dict, klasor: str, onceki: dict | None = None,
              govde: dict | None = None) -> tuple[str, str]:
    """docs/kanit/ altına raporları yazar. Dönen: (accuracy yolu, gecikme yolu).

    `govde` verilirse aynı damgayla bir de `sonuclar-<sonek>.json` yazılır
    (BULGU-05): soru bazlı sonuç `eval/results.json` içindeydi, o da
    `.gitignore`'da — rapor hiç itilmeyen bir dosyayı kaynak gösteriyordu ve
    eşli karşılaştırmanın (McNemar) girdisi kanıt klasörüne hiç girmiyordu.
    Üç dosya aynı soneki taşır; hangisinin hangi koşuma ait olduğu gözle görülür.
    """
    os.makedirs(klasor, exist_ok=True)
    t = damga["tarih"]
    # Dosya adı koşuma özgü olmalı. Saha kaydı (2026-08-16): bir günde altı ölçüm
    # yapıldı ve her biri bir öncekinin ÜZERİNE yazdı — kanıt klasöründe yalnız
    # sonuncusu kaldı. Kanıt dosyasının değeri, silinmemesindedir.
    model_slug = "".join(c if c.isalnum() else "-" for c in damga.get("model", "model"))
    ek = 1
    while True:
        sonek = f"{t}-{model_slug}-{ek:02d}"
        acc_yol = os.path.join(klasor, f"accuracy-{sonek}.md")
        gec_yol = os.path.join(klasor, f"gecikme-{sonek}.md")
        if not os.path.exists(acc_yol):
            break
        ek += 1
    if govde is not None:
        with open(os.path.join(klasor, f"sonuclar-{sonek}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(govde, f, ensure_ascii=False, indent=2)
    basari = ozet["accuracy"] >= HEDEF_ACCURACY

    def damga_blogu() -> str:
        return ("| Alan | Değer |\n|------|-------|\n"
                + "\n".join(f"| {k} | `{v}` |" for k, v in damga.items()))

    karsilastirma = ""
    _engel = karsilastirilamaz(onceki, ozet, damga) if onceki else None
    if _engel:
        karsilastirma = (
            "## Önceki ölçümle karşılaştırma\n\n"
            f"> **Karşılaştırma yapılmadı.** {_engel}\n>\n"
            "> Aynı cetveli kullanan iki koşum arasında karşılaştırma otomatik döner.\n\n")
    elif onceki:
        onceki_damga = onceki.get("damga", {})
        karsilastirma = (
            "## Önceki ölçümle karşılaştırma\n\n"
            f"Önceki koşum: `{onceki_damga.get('tarih', '?')}` · model `{onceki_damga.get('model', '?')}` "
            f"· commit `{onceki_damga.get('commit', '?')}`\n\n"
            "| Ölçü | Önceki | Şimdi | Fark |\n|------|--------|-------|------|\n"
            f"| Accuracy | %{100 * onceki['accuracy']:.1f} | **%{100 * ozet['accuracy']:.1f}** | "
            f"{_fark_satiri(100 * ozet['accuracy'], 100 * onceki['accuracy'])} |\n"
            f"| p50 | {onceki['p50_s']:.1f} sn | {ozet['p50_s']:.1f} sn | "
            f"{_fark_satiri(ozet['p50_s'], onceki['p50_s'], 'sn', yukselmesi_iyi=False)} |\n"
            f"| p95 | {onceki['p95_s']:.1f} sn | {ozet['p95_s']:.1f} sn | "
            f"{_fark_satiri(ozet['p95_s'], onceki['p95_s'], 'sn', yukselmesi_iyi=False)} |\n"
            f"| Sessiz yanlış | {onceki['sessiz_yanlis']} | {ozet['sessiz_yanlis']} | "
            f"{_fark_satiri(ozet['sessiz_yanlis'], onceki['sessiz_yanlis'], 'soru', yukselmesi_iyi=False)} |\n\n"
            "> Karşılaştırma yalnız test seti ve ölçüm yöntemi aynıysa anlamlıdır.\n"
            "> Model ya da soru sayısı değiştiyse bu tabloyu tek başına okuma.\n\n")
        # Yukarıdaki tablo FARKI gösterir; hükmü aşağıdaki satır verir.
        # Ham puan farkına bakan bir kapı gürültünün içinde kalıyordu (BULGU-10).
        _reg = regresyon_karari(onceki, govde.get("results") or []) if govde else None
        if _reg:
            karsilastirma += (
                "### Regresyon kapısı (SPEC A-4)\n\n"
                f"**{regresyon_satiri(_reg)}**\n\n"
                f"Kural: `bozulan - düzelen >= {_reg['asgari_fark']}` **ve** "
                f"`McNemar p < {_reg['p_esigi']}`. Ham puan farkı tek başına hüküm "
                "vermez: aynı kod, aynı ayarlarla alınan iki api koşumu arasında "
                "7 soru yön değiştirmişti (p = 1,000) — saf gürültüde 3 soruluk net "
                "fark çıkma olasılığı yaklaşık %45.\n\n")

    with open(acc_yol, "w", encoding="utf-8") as f:
        f.write(f"""# Execution Accuracy Raporu — {t}

**Gereksinim:** G-11 — {ozet['n']} soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **{100 * ozet['accuracy']:.1f}%**  ({ozet['dogru']}/{ozet['n']})
{_kota_uyarisi(ozet)}

**Hedef ({100 * HEDEF_ACCURACY:.0f}%) {'KARŞILANDI' if basari else 'KARŞILANMADI'}.**
{'' if basari else chr(10) + '> ADR-2 koşulu tetiklendi: RAG-only baseline hedefin altında. QLoRA fine-tune ' + chr(10) + '> kararı yeniden açılmalı ve yeni bir iş paketi olarak planlanmalıdır.' + chr(10)}
Öz-onarım denemesi yapılan soru sayısı: {ozet['onarim_sayisi']}/{ozet['n']}

## Sessiz yanlış (B-7)

Yanlış cevabın iki türü vardır ve riskleri aynı değildir. **Yakalanan** hata kullanıcıyı
uyarır. **Sessiz yanlış** hatasız bir tablo döndürür ve yanlış sayı yönetime taşınır —
sistem analizi B7 bunu projenin en büyük riski olarak kaydetmişti.

| Ölçü | Değer |
|------|-------|
| Sessiz yanlış (çalıştı, cevap yanlış) | **{ozet['sessiz_yanlis']}/{ozet['n']}** (%{100 * ozet['sessiz_yanlis_orani']:.1f}) |
| Reddedilen (cevap kullanıcıya hiç ulaşmadı) | {ozet['reddedilen']}/{ozet['n']} |

> "Reddedilen" ile aşağıdaki güven karnesinin "yakalanan"ı **ayrı şeylerdir**:
> burada hat cevabı vermiyor, orada cevap veriliyor ve yanına uyarı konuyor.
> (BULGU-06 — aynı raporda iki tanım aynı adı taşıyordu.)
| **Yanlışların içinde sessiz olanların payı** | **%{100 * ozet['yanlislarda_sessiz_pay']:.1f}** |
| Cevabı gerçekten üreten mod | {_mod_satiri(ozet, damga)} |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

{karsilastirma}
## Ölçüm damgası

{damga_blogu()}

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
""")
        for k, v in ozet["kirilim"]["zorluk"].items():
            f.write(f"| {k} | {v['dogru']}/{v['toplam']} | %{100 * v['dogru'] / v['toplam']:.0f} |\n")
        f.write("\n## JOIN sayısı kırılımı\n\n| JOIN | Doğru / Toplam | Oran |\n|------|----------------|------|\n")
        for k, v in ozet["kirilim"]["join"].items():
            f.write(f"| {k} | {v['dogru']}/{v['toplam']} | %{100 * v['dogru'] / v['toplam']:.0f} |\n")
        f.write("\n## Hangi aşamada kaybediliyor\n\n| Aşama | Soru sayısı |\n|-------|-------------|\n")
        for k, v in sorted(ozet["asama_dagilimi"].items(), key=lambda x: -x[1]):
            f.write(f"| `{k}` | {v} |\n")
        f.write(_guven_bolumu(ozet.get("guven") or {}))
        f.write("\nSoru bazlı ayrıntı: `eval/results.json`\n")

    with open(gec_yol, "w", encoding="utf-8") as f:
        p95_ok = ozet["p95_s"] <= HEDEF_GECIKME_P95_S
        _kapsam = g12_kapsam_disi(damga)
        # "En geç 10 sn" bir en-kötü-durum ifadesidir; p95 onun vekilidir.
        # Hedefi aşan tek tek sorular da yazılır, yoksa vekil aslını gizler.
        _asanlar = [r for r in ozet.get("en_yavas_5") or []
                    if r.get("sure_s", 0) > HEDEF_GECIKME_P95_S]
        if _kapsam:
            _hedef_satiri = f"| Hedef (p95) | {HEDEF_GECIKME_P95_S:.0f} sn — **KAPSAM DIŞI** |"
            _hukum = f"\n> **G-12 hakkında hüküm verilmedi.** {_kapsam}\n"
        else:
            _hedef_satiri = (f"| Hedef (p95) | {HEDEF_GECIKME_P95_S:.0f} sn — "
                             f"{'KARŞILANDI' if p95_ok else 'KARŞILANMADI'} |")
            _hukum = ""
        if _asanlar:
            _hukum += (f"\n> Hedefi aşan soru: en az {len(_asanlar)} tanesi "
                       f"{HEDEF_GECIKME_P95_S:.0f} sn üstünde (en yavaş "
                       f"{max(r['sure_s'] for r in _asanlar):.2f} sn). p95 bir vekildir; "
                       "gereksinimin metni \"en geç\" der.\n")
        f.write(f"""# Gecikme Raporu — {t}

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **{ozet['p50_s']:.2f} sn** |
| p95 | **{ozet['p95_s']:.2f} sn** |
{_hedef_satiri}
{_hukum}

## Ölçüm damgası

{damga_blogu()}

## En yavaş 5 soru

| Süre (sn) | Aşama | Soru |
|-----------|-------|------|
""")
        for r in ozet["en_yavas_5"]:
            f.write(f"| {r.get('sure_s', 0):.2f} | `{r['asama'].split(':')[0]}` | {r['soru'][:70]} |\n")
        f.write("\n> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +\n"
                "> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar\n"
                "> yukarı çeker; üretim kullanımında o adım yoktur.\n")

    _gunluge_ekle(klasor, ozet, damga, os.path.basename(acc_yol))
    return acc_yol, gec_yol


def _gunluge_ekle(klasor: str, ozet: dict, damga: dict, rapor_adi: str) -> None:
    """Her koşum `OLCUMLER.md` dosyasına tek satır olarak eklenir — üzerine yazılmaz.

    Bu dosya projenin ölçüm hafızasıdır: hangi yapılandırma hangi sayıyı verdi,
    tarih sırasıyla. Tek tek raporlar ayrıntı, bu dosya seyir çizgisidir.
    """
    yol = os.path.join(klasor, "OLCUMLER.md")
    yeni = not os.path.exists(yol)
    with open(yol, "a", encoding="utf-8") as f:
        if yeni:
            f.write("# Ölçüm Günlüğü\n\n"
                    "Her koşum bir satır. Bu dosyaya asla üzerine yazılmaz.\n"
                    "Karşılaştırma yalnız aynı test seti ve aynı model için anlamlıdır.\n\n"
                    "| Tarih | Model | Acc | Sessiz yanlış | p50 | p95 | temp | seed | num_ctx | değer örn. | commit | Rapor |\n"
                    "|-------|-------|-----|---------------|-----|-----|------|------|---------|-----------|--------|-------|\n")
        f.write(
            f"| {damga.get('tarih')} | `{damga.get('model')}` "
            f"| **%{100 * ozet['accuracy']:.0f}** ({ozet['dogru']}/{ozet['n']}) "
            f"| {ozet['sessiz_yanlis']} (%{100 * ozet['yanlislarda_sessiz_pay']:.0f}) "
            f"| {ozet['p50_s']:.1f} | {ozet['p95_s']:.1f} "
            f"| {damga.get('temperature')} | {damga.get('seed')} | {damga.get('num_ctx')} "
            f"| {'açık' if damga.get('ornek_degerler') else 'kapalı'} "
            f"| `{damga.get('commit')}` | {rapor_adi} |\n")


# --------------------------------------------------------------------- ana akış

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SorBI execution accuracy ve gecikme ölçümü")
    ap.add_argument("--db", default=None)
    ap.add_argument("--testset", default=os.path.join(os.path.dirname(__file__), "test_set_tr.jsonl"))
    ap.add_argument("--mode", default=config.MODE, choices=["local", "api"])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results.json"))
    ap.add_argument("--kanit-dir", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "kanit"))
    ap.add_argument("--limit", type=int, default=None, help="ilk N soruyla hızlı deneme")
    ap.add_argument("--gold-only", action="store_true",
                    help="LLM'siz mod: yalnızca gold_sql'lerin geçerliliğini ve çalıştığını kontrol et")
    ap.add_argument("--doctor", action="store_true",
                    help="Ölçüm ortamı hazır mı? Hazır değilse ne yapılacağını yazar.")
    args = ap.parse_args(argv)

    if args.db:
        config.DB_URL = f"sqlite:///{os.path.abspath(args.db)}"

    if args.doctor:
        return doctor(args.mode)

    # Üzerine yazmadan ÖNCE oku — yoksa karşılaştıracak bir şey kalmaz
    onceki = onceki_olcum(args.out)

    items = yukle_testset(args.testset)
    if args.limit:
        items = items[: args.limit]

    if args.gold_only:
        return 1 if gold_check(items) else 0

    # LLM gerektiren yol — gecikmeli içe aktarım (gold-only ve doctor bunu istemez)
    from app import generator as gen_mod
    from app.schema_rag import ContextIndex
    idx = ContextIndex(config.DB_URL)

    results = []
    for i, item in enumerate(items, 1):
        # Tek bir sorunun beklenmeyen hatası 50 soruluk koşumu düşürmemeli.
        # Saha kaydı (2026-08-16): 30. soruda çöken koşum 29 sorunun sonucunu götürdü.
        try:
            rec = run_one(item, idx, args.mode, gen_mod)
        except Exception as e:  # noqa: BLE001
            rec = {"id": item["id"], "soru": item["soru"], "zorluk": item["zorluk"],
                   "join": item["join"], "dogru": False, "sql": "", "onarim": False,
                   "sure_s": 0.0, "asama": f"kosucu_hatasi: {type(e).__name__}: {str(e)[:100]}"}
        results.append(rec)
        isaret = "+" if rec["dogru"] else "-"
        print(f"[{i:02d}/{len(items)}] {isaret} ({rec['zorluk']}, {rec['join']} join, "
              f"{rec.get('sure_s', 0):.1f} sn) {item['soru'][:55]}  [{rec['asama']}]")

    ozet = ozetle(results)
    damga = _damga(args.mode)

    print("\n" + "=" * 60)
    print(f"EXECUTION ACCURACY: {ozet['dogru']}/{ozet['n']} = "
          f"%{100 * ozet['accuracy']:.1f}   (hedef G-11: >=%{100 * HEDEF_ACCURACY:.0f})")
    print(f"GECİKME: p50 {ozet['p50_s']:.2f} sn · p95 {ozet['p95_s']:.2f} sn   "
          f"(hedef G-12: p95 <= {HEDEF_GECIKME_P95_S:.0f} sn)")
    if ozet.get("kota_asildi"):
        print(f"!! KOTA AŞIMI: {ozet['kota_asildi']}/{ozet['n']} soru hiç ölçülemedi. "
              f"Ölçülebilen {ozet['olculebilen']} soruda doğruluk "
              f"%{100 * ozet['accuracy_olculebilen']:.1f}. Bu koşum karşılaştırma "
              "için kullanılamaz.")
    print(f"SESSİZ YANLIŞ: {ozet['sessiz_yanlis']}/{ozet['n']} "
          f"(yanlışların %{100 * ozet['yanlislarda_sessiz_pay']:.0f}'i sessiz)  [B-7]")
    g = ozet.get("guven") or {}
    if g.get("evren"):
        print(f"GÜVEN KONTROLÜ: sessiz yanlışın {g['yakalanan']}/{g['sessiz_yanlis']} "
              f"(%{100 * g['yakalama_orani']:.0f}) bayraklandı; "
              f"doğru cevapta {g['yanlis_alarm']}/{g['dogru_cevap']} gereksiz bayrak "
              f"(%{100 * g['yanlis_alarm_orani']:.0f}); isabet %{100 * g['isabet']:.0f}")
    _engel = karsilastirilamaz(onceki, ozet, damga) if onceki else None
    _regresyon = None
    if _engel:
        print(f"ÖNCEKİ ÖLÇÜM: karşılaştırma yapılmadı — {_engel}")
    elif onceki:
        fark = 100 * (ozet["accuracy"] - onceki["accuracy"])
        print(f"ÖNCEKİ ÖLÇÜM: %{100 * onceki['accuracy']:.1f} "
              f"({onceki.get('damga', {}).get('tarih', '?')}) -> "
              f"{'+' if fark >= 0 else ''}{fark:.1f} puan")
        # Ham puan farkı bir HÜKÜM değildir; hükmü eşli karar verir (BULGU-09/10).
        _regresyon = regresyon_karari(onceki, results)
        if _regresyon:
            print(f"REGRESYON KAPISI: {regresyon_satiri(_regresyon)}")
    for grup, anahtar in [("Zorluk", "zorluk"), ("JOIN sayısı", "join")]:
        print(f"\n{grup} kırılımı:")
        for val, v in ozet["kirilim"][anahtar].items():
            print(f"  {val}: {v['dogru']}/{v['toplam']} = %{100 * v['dogru'] / v['toplam']:.0f}")

    _govde = {"damga": damga,
              "ozet": {k: v for k, v in ozet.items() if k != "en_yavas_5"},
              "regresyon": _regresyon,
              "results": results}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(_govde, f, ensure_ascii=False, indent=2)

    # BULGU-05: damgalı soru bazlı kopya da kanıt klasörüne yazılır.
    acc_yol, gec_yol = rapor_yaz(ozet, damga, args.kanit_dir, onceki, govde=_govde)
    sonuc_yol = acc_yol.replace("accuracy-", "sonuclar-").replace(".md", ".json")
    print(f"\nAyrıntılı rapor : {args.out}")
    print(f"Kanıt raporları : {acc_yol}\n                  {gec_yol}\n                  {sonuc_yol}")
    print("\nBu dosyaları commit'leyin — v3 SPEC A-2/A-3'ün kabul kriteri budur.")
    # CI için: regresyon kapısı kırmızıya döndürebilmeli (SPEC A-4).
    if _regresyon and _regresyon["karar"] == "REGRESYON":
        print("\n!! REGRESYON KAPISI KIRMIZI — çıkış kodu 3.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
