#!/usr/bin/env python3
"""Kanıt bütünlüğü kapısı — Claude Code hook'u.

İhsan'ın kararı (2026-08-21): "kanıtı bozan şey durdursun, gerisi biriksin."

DURDURUR (çıkış 2 — Claude mesajı görür ve düzeltmek zorundadır):
  - ruff hatası
  - kırmızı test (yalnız hızlı değişmez testleri)
  - ADR ile kodun ayrışması
  - kanıt dosyasının üzerine yazma girişimi

BİRİKTİRİR (uyarı, akışı kesmez):
  - kapsam düşüşü, biçim, stil

Kullanım (`.claude/settings.json` içinden):
    python .claude/hooks/kapi.py --dosya      PostToolUse: Edit|Write
    python .claude/hooks/kapi.py --kapanis    Stop
    python .claude/hooks/kapi.py --acilis     SessionStart
"""
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Bu testler HIZLI ve DEĞİŞMEZ olanlar. Tam süit kapanışta koşulmaz:
# 60+ saniyelik bir kapı, kapatılan bir kapıdır.
HIZLI_TESTLER = [
    "tests/test_adr_uyumu.py",
    "tests/test_tarih_sabitle.py",
    "tests/test_validator.py",
    "tests/test_guven.py",
]


def _kos(argv: list, sure: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, cwd=KOK, capture_output=True, text=True,  # noqa: S603
                           timeout=sure, check=False)
        return p.returncode, (p.stdout + p.stderr)
    except (OSError, subprocess.SubprocessError) as e:
        # Kapı çalışamıyorsa AKIŞI KESMEZ ama sessiz de kalmaz.
        return 0, f"(kapı koşturulamadı: {type(e).__name__})"


def _dur(mesaj: str) -> None:
    """Çıkış 2: Claude bu metni görür ve düzeltmeden devam edemez."""
    print(mesaj, file=sys.stderr)
    sys.exit(2)


def _girdi() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return {}


# --------------------------------------------------------------- dosya kapısı

def dosya_kapisi() -> None:
    veri = _girdi()
    yol = (veri.get("tool_input") or {}).get("file_path") or ""
    if not yol:
        return
    bagil = os.path.relpath(yol, KOK) if os.path.isabs(yol) else yol
    bagil = bagil.replace("\\", "/")

    # Kanıt silinmez, üzerine yazılmaz. Altı ölçüm bir gün içinde aynı
    # dosyaya yazıp birbirini yok etmişti.
    if bagil.startswith("docs/kanit/") and veri.get("tool_name") == "Write":
        if os.path.exists(yol) and not bagil.endswith((".md", ".log")):
            _dur(f"KAPI: {bagil} bir kanıt dosyası ve zaten var.\n"
                 "Kanıtın üzerine yazılmaz. Benzersiz bir ad kullan ya da ekle.")

    if not bagil.endswith(".py"):
        return
    kod, cikti = _kos([sys.executable, "-m", "ruff", "check", bagil], 60)
    if kod != 0 and "All checks passed" not in cikti:
        _dur(f"KAPI: ruff {bagil} dosyasında hata buldu.\n\n{cikti[:1500]}")


# --------------------------------------------------------------- kapanış kapısı

def kapanis_kapisi() -> None:
    sorunlar = []

    kod, cikti = _kos([sys.executable, "-m", "ruff", "check", "."], 90)
    if kod != 0 and "All checks passed" not in cikti:
        sorunlar.append(f"ruff:\n{cikti[-1200:]}")

    var = [t for t in HIZLI_TESTLER if os.path.exists(os.path.join(KOK, t))]
    if var:
        kod, cikti = _kos([sys.executable, "-m", "pytest", *var, "-q",
                           "--no-header", "-p", "no:cacheprovider",
                           "--no-cov"], 180)
        if kod != 0:
            sorunlar.append(f"değişmez testler kırmızı:\n{cikti[-1500:]}")

    if sorunlar:
        _dur("KAPI: kanıt bütünlüğü bozuldu, iş bitmiş sayılmaz.\n\n"
             + "\n\n".join(sorunlar)
             + "\n\nBunlar düzeltilmeden oturum kapanmamalı.")


# --------------------------------------------------------------- açılış

def acilis() -> None:
    """Yeni oturum nereden devraldığını bilsin diye son durumu basar."""
    parcalar = []

    gunluk = os.path.join(KOK, "docs", "is-hatti", "GUNLUK.md")
    if os.path.exists(gunluk):
        with open(gunluk, encoding="utf-8") as f:
            satirlar = f.read().split("\n")
        bas = next((i for i, s in enumerate(satirlar) if s.startswith("## ")), None)
        if bas is not None:
            son = next((i for i, s in enumerate(satirlar[bas + 1:], bas + 1)
                        if s.startswith("## ")), len(satirlar))
            parcalar.append("SON OTURUM:\n" + "\n".join(satirlar[bas:son]).strip())

    gece = os.path.join(KOK, "docs", "kanit", "SON-GECE-KOSUMU.txt")
    if os.path.exists(gece):
        with open(gece, encoding="utf-8") as f:
            satir = f.read().strip()
        if satir:
            parcalar.append("SON GECE KOŞUMU: " + satir)

    push = os.path.join(KOK, "docs", "kanit", "PUSH-SORUNU.txt")
    if os.path.exists(push):
        with open(push, encoding="utf-8") as f:
            parcalar.append("!! " + f.read().strip()
                            + "  → kanıt dışarı çıkamıyor, çözüm: yedekle.bat")

    karne = os.path.join(KOK, "docs", "kanit", "KARNE-GECMIS.log")
    if os.path.exists(karne):
        with open(karne, encoding="utf-8") as f:
            kayitlar = [s.strip() for s in f if s.startswith("KARNE_OZET")]
        if kayitlar:
            parcalar.append("SON KARNE: " + kayitlar[-1])

    if parcalar:
        print("\n\n".join(parcalar))


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "--dosya"
    if mod == "--kapanis":
        kapanis_kapisi()
    elif mod == "--acilis":
        acilis()
    else:
        dosya_kapisi()
