"""Depoya girmemesi gereken şeyler ve dayanaksız belge atıfları.

İki bulgu bu dosyada kilitleniyor:

**BULGU-15 (ağır).** `.sorbi/users.json` — admin `salt` + `hash` — `884f8d9`
commit'inde uzak depoya itilmişti ve `.gitignore`'da değildi. Takipten
çıkarmak geçmişi temizlemez (parola döndürüldü mü, `SHIP.md`'ye yazılır); bu
testlerin işi, aynı dosyanın bir daha SESSİZCE geri gelmemesidir.

**YENİ-A.** `CLAUDE.md` § 6 ADR-3 ve ADR-4'e atıf yapıyordu, dosyaları yoktu.
Dayanaksız atıf Verify sınıfı bir hatadır — README'nin var olmayan bir
`training/` klasörünü anlatmasıyla aynı aile.
"""
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Depoda İZİ bile olmaması gereken yollar (git takibinde olmamalı).
YASAK_YOLLAR = (
    ".sorbi/",          # kimlik deposu: salt + hash
    ".coverage",        # araç çıktısı
    ".venv/",
)

# `CLAUDE.md` içinde anılan her ADR'nin dosyası olmalı.
ADR_DIZIN = os.path.join(KOK, "docs", "kararlar")


def _takip_edilenler() -> list[str] | None:
    """`git ls-files` çıktısı. Git yoksa None — test atlanmaz, geçerli sayılır."""
    try:
        out = subprocess.run(["git", "ls-files"],  # noqa: S603, S607
                             capture_output=True, text=True, timeout=20,
                             check=False, cwd=KOK)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [s for s in out.stdout.splitlines() if s.strip()]


def test_kimlik_deposu_ve_arac_ciktilari_takip_edilmiyor():
    """Bir sır, `.gitignore`'a eklenerek geçmişten silinmez — ama yenisi eklenmez.

    `.sorbi/users.json` uzak depo geçmişinde duruyor. Bu test onu oradan
    kaldıramaz; kaldırabileceği tek şey, aynı hatanın tekrarıdır.
    """
    dosyalar = _takip_edilenler()
    if dosyalar is None:
        return                       # git yok (paket kurulumu): denetlenecek bir şey de yok
    suclu = [d for d in dosyalar
             if any(d == y.rstrip("/") or d.startswith(y) for y in YASAK_YOLLAR)]
    assert not suclu, (
        "Depoya girmemesi gereken dosyalar takip ediliyor:\n  "
        + "\n  ".join(suclu)
        + "\n\n`git rm --cached <yol>` ile takipten çıkarın. Bir sır söz konusuysa "
          "takipten çıkarmak YETMEZ: geçmişte duruyor, kimlik bilgisi döndürülmeli."
    )


def test_gitignore_kimlik_deposunu_kapsiyor():
    """Koruma iki katmanlı olmalı: bu test ve `.gitignore`. Biri unutulursa öteki tutar."""
    yol = os.path.join(KOK, ".gitignore")
    if not os.path.exists(yol):
        return
    metin = open(yol, encoding="utf-8").read()
    assert ".sorbi/" in metin, ".gitignore `.sorbi/` satırını taşımıyor (BULGU-15)."


def test_claude_md_de_anilan_her_adr_dosyasi_var():
    """Belgede adı geçen her ADR gerçekten yazılmış olmalı (YENİ-A)."""
    metin = open(os.path.join(KOK, "CLAUDE.md"), encoding="utf-8").read()
    anilan = {int(n) for n in re.findall(r"\bADR-(\d+)\b", metin)}
    if not anilan:
        return
    mevcut = {int(m.group(1))
              for ad in os.listdir(ADR_DIZIN)
              if (m := re.match(r"ADR-(\d+)-", ad))}
    eksik = sorted(anilan - mevcut)
    assert not eksik, (
        f"CLAUDE.md şu ADR'lere atıf yapıyor ama dosyaları yok: {eksik}. "
        "Ya yazılsın ya atıf düşsün — dayanaksız atıf bir Verify hatasıdır."
    )


def test_adr_dosyalarinin_durumu_yazili():
    """Her ADR'nin başında bir **Durum** satırı olmalı.

    "Taslak mı, kabul mü" sorusunun cevabı dosyanın içinde durmuyorsa, ADR
    bir karar kaydı değil bir not olur. ADR-5 için bu özellikle önemli:
    o bir Ship kapısı ve TASLAK olduğu görünmeli.
    """
    for ad in sorted(os.listdir(ADR_DIZIN)):
        if not ad.startswith("ADR-"):
            continue
        bas = open(os.path.join(ADR_DIZIN, ad), encoding="utf-8").read()[:600]
        assert re.search(r"\*\*Durum:\*\*", bas), f"{ad}: 'Durum:' satırı yok."


def test_adr5_karar_kodla_ayni():
    """ADR-5 kabul edildi (İhsan, 2026-09-30): seçenek B — yerel varsayılan.

    Karar yalnız belgede durursa karar değildir (CLAUDE.md § 7). Bu test iki
    şeyi birbirine kilitler: ADR'nin seçtiği harf ve `config.py`'deki
    varsayılan mod. Biri değişip öteki değişmezse CI kırmızıya döner.

    Varsayılan, ortam değişkeninden bağımsız olarak **kaynaktan** okunur:
    testi koşan makinede `SORBI_MODE=api` tanımlı olabilir (İhsan'ınkinde öyle).
    """
    metin = open(os.path.join(ADR_DIZIN, "ADR-5-api-modu.md"), encoding="utf-8").read()
    assert "KABUL" in metin[:400], "ADR-5 kabul edildiğini söylemiyor."
    assert "Ship kapısıdır" in metin
    secilen = re.search(r"^Seçilen:\s*(.*)$", metin, re.MULTILINE)
    assert secilen, "ADR-5'te 'Seçilen:' satırı yok."
    assert secilen.group(1).strip() == "B", (
        f"ADR-5 '{secilen.group(1).strip()}' diyor; kod B'ye göre yazılı. "
        "Karar değiştiyse config.py ve bu test birlikte güncellenir.")

    kaynak = open(os.path.join(KOK, "app", "config.py"), encoding="utf-8").read()
    varsayilan = re.search(r'os\.getenv\("SORBI_MODE",\s*"([^"]+)"\)', kaynak)
    assert varsayilan, "config.py'de SORBI_MODE varsayılanı bulunamadı."
    assert varsayilan.group(1) == "local", (
        f"ADR-5 B: varsayılan mod 'local' olmalı, config '{varsayilan.group(1)}' diyor.")


def test_yasak_yollar_listesi_gitignore_ile_tutarli():
    """Listeyi kod tarafında tutup `.gitignore`'u unutmak da bir sessiz yanlış."""
    yol = os.path.join(KOK, ".gitignore")
    if not os.path.exists(yol):
        return
    metin = open(yol, encoding="utf-8").read()
    for y in YASAK_YOLLAR:
        anahtar = y.rstrip("/")
        assert anahtar in metin, f"`{y}` yasak listede ama .gitignore'da yok."


if __name__ == "__main__":                        # elle bakmak için
    sys.exit(0)
