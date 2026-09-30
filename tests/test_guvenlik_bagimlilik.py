"""Bağımlılık güvenliği kabullerinin bekçileri (ADR-10, CI `guvenlik` işi).

CI'daki her `--ignore-vuln` bir varsayıma dayanır. Varsayım bir gün bozulursa
kabul sessizce geçerli kalmamalı — bu testler o günü yakalar.
"""
import pathlib
import re

KOK = pathlib.Path(__file__).resolve().parent.parent


def _kaynak():
    for yol in list((KOK / "app").rglob("*.py")) + list((KOK / "ui").rglob("*.py")):
        yield yol, yol.read_text(encoding="utf-8")


def test_chroma_gomulu_kosar_sunucu_acmaz():
    """chromadb PYSEC-2026-311/3813/3814/3815 kabulü: açıkların hepsi Chroma'nın
    HTTP sunucusuna ait. SorBI sunucu istemcisi ya da sunucu kullanırsa kabul düşer."""
    yasak = re.compile(r"\b(HttpClient|AsyncHttpClient|chromadb\.server|chroma run|FastAPI\(.*chroma)")
    suclu = [str(y.relative_to(KOK)) for y, s in _kaynak() if yasak.search(s)]
    assert not suclu, ("Chroma sunucu modu kullanılıyor: " + ", ".join(suclu)
                       + " — CI'daki chromadb istisnaları artık geçersiz, yeniden değerlendirin.")


def test_uzaktan_kod_guvenilmez():
    """PYSEC-2026-311/3814'ün tetikleyicisi `trust_remote_code=True`. Bizde hiç olmamalı."""
    suclu = [str(y.relative_to(KOK)) for y, s in _kaynak()
             if re.search(r"trust_remote_code\s*=\s*True", s)]
    assert not suclu, suclu


def test_ci_istisnalari_gerekceli():
    """CI'daki her istisna, gerekçesiyle aynı dosyada durmalı."""
    ci = (KOK / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for kimlik in re.findall(r"--ignore-vuln (\S+)", ci):
        assert ci.count(kimlik) >= 2, f"{kimlik} için gerekçe yok"
