"""Çekirdeğin saflığı — MIMARI §6/D'nin zorlayıcısı.

Bağımlılığın tersine çevrilmesi bir üslup tercihi değil, bu projede üç somut
şeyin ön koşuludur:

  1. Cetvel Katman 1'in (SPEC F-1) LLM'siz ve DB'siz, saniyeler içinde
     koşabilmesi,
  2. Sınır 1'in (SPEC E-1) tip düzeyinde uygulanabilmesi — çekirdek `requests`
     tanımıyorsa oradan bir istem çıkamaz,
  3. Derleyicinin taşınabilir olması: aynı seçim, farklı lehçelerde aynı
     kalır çünkü çekirdek hiçbir sürücüyü tanımaz.

Bir kural olarak yazılsaydı unutulurdu. Bu test, kuralı çalıştırılabilir bir
kontrole çevirir (CLAUDE.md §7'nin ortak çaresi).
"""
from __future__ import annotations

import ast
import pathlib
import sys

CEKIRDEK = pathlib.Path(__file__).resolve().parents[2] / "app" / "cekirdek"

# Çekirdeğin import etmesine izin verilenler: stdlib + saf ayrıştırıcı.
# `sqlglot` bilinçli bir istisnadır: IO yapmaz, ağ görmez, saf bir SQL
# ayrıştırıcı/üreticidir. Derleyici (İP-47) onsuz yazılamaz.
IZINLI_DIS = {"sqlglot"}


def _stdlib() -> set[str]:
    adlar = set(getattr(sys, "stdlib_module_names", set()))
    return adlar | {"__future__"}


def _ust_duzey_importlar(yol: pathlib.Path) -> set[str]:
    agac = ast.parse(yol.read_text(encoding="utf-8"), filename=str(yol))
    adlar: set[str] = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Import):
            adlar |= {a.name.split(".")[0] for a in dugum.names}
        elif isinstance(dugum, ast.ImportFrom):
            if dugum.level:                     # göreli içe aktarım — kendi paketi
                continue
            if dugum.module:
                adlar.add(dugum.module.split(".")[0])
    return adlar


def test_cekirdek_dosyalari_var():
    assert CEKIRDEK.is_dir(), f"çekirdek dizini yok: {CEKIRDEK}"
    assert list(CEKIRDEK.glob("*.py")), "çekirdekte hiç modül yok"


def test_cekirdek_disariya_bagimli_degil():
    izinli = _stdlib() | IZINLI_DIS | {"app"}
    ihlaller: list[str] = []
    for yol in sorted(CEKIRDEK.glob("*.py")):
        disari = _ust_duzey_importlar(yol) - izinli
        if disari:
            ihlaller.append(f"{yol.name}: {', '.join(sorted(disari))}")
    assert not ihlaller, (
        "Çekirdek dışarıya bağımlı hâle gelmiş:\n  " + "\n  ".join(ihlaller) +
        "\n\nÇekirdek yalnız stdlib + sqlglot import edebilir. IO gerekiyorsa "
        "app/baglanti/ altında bir port uygulaması yazın (MIMARI §3)."
    )


def test_cekirdek_app_icinde_yalniz_cekirdegi_tanir():
    """Çekirdek, `app.baglanti` ya da `app.akis`'a bakamaz — ok içeri bakar."""
    ihlaller: list[str] = []
    for yol in sorted(CEKIRDEK.glob("*.py")):
        agac = ast.parse(yol.read_text(encoding="utf-8"), filename=str(yol))
        for dugum in ast.walk(agac):
            if isinstance(dugum, ast.ImportFrom) and (dugum.module or "").startswith("app."):
                parcalar = dugum.module.split(".")
                if len(parcalar) > 1 and parcalar[1] != "cekirdek":
                    ihlaller.append(f"{yol.name}: {dugum.module}")
    assert not ihlaller, (
        "Çekirdek dış katmanlara bakıyor:\n  " + "\n  ".join(ihlaller))


def test_cekirdek_yan_etkisiz_ice_aktarilir():
    """İçe aktarma anında dosya açan, ağ deneyen ya da ortam okuyan bir
    çekirdek modülü, testi yavaşlatmakla kalmaz — sırayla bağımlı hâle
    getirir."""
    import importlib
    for yol in sorted(CEKIRDEK.glob("*.py")):
        if yol.stem == "__init__":
            continue
        importlib.import_module(f"app.cekirdek.{yol.stem}")
