"""BULGU-24 — kanıt itmesi çalışılan daldan bağımsız olmalı.

Buradaki testler gerçek git depoları kurar (çıplak uzak + iki klon) ve
gerçek `git push` çalıştırır. Taklit yok: kusur tam olarak git'in
hızlı-ileri sarma davranışından doğmuştu; taklit edilen bir git bunu
gösteremezdi.

`skipif` YOK ve olmayacak: git yoksa bu testler atlanmaz, düşer. Atlanan
test koşmamış testtir (`tests/test_suit_dururlugu.py`) — ve zaten git'i
olmayan bir makinede gece koşumunun kanıt itmesi de çalışmaz.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from eval import kanit_it

# --------------------------------------------------------------- yardımcılar

def _g(depo: Path, *arg: str) -> str:
    ortam = dict(os.environ)
    ortam.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
    )
    p = subprocess.run(["git", *arg], cwd=str(depo), env=ortam,  # noqa: S603, S607
                       capture_output=True, text=True)
    assert p.returncode == 0, f"git {' '.join(arg)}: {p.stderr}"
    return p.stdout.strip()


def _yaz(kok: Path, yol: str, icerik: str) -> None:
    d = kok / yol
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(icerik, encoding="utf-8")


@pytest.fixture
def hat(tmp_path: Path):
    """Çıplak uzak depo + `olcum-otomatik` dalı + bir çalışma kopyası."""
    uzak = tmp_path / "uzak.git"
    _g(tmp_path, "init", "--bare", "-b", "olcum-otomatik", str(uzak))

    is_ = tmp_path / "is"
    _g(tmp_path, "clone", str(uzak), str(is_))
    _yaz(is_, "docs/kanit/.gitkeep", "")
    _yaz(is_, "docs/is-hatti/GUNLUK.md", "# gunluk\n")
    _yaz(is_, "app/config.py", "MOD = 'api'\n")
    _g(is_, "add", "-A")
    _g(is_, "commit", "-m", "taban")
    _g(is_, "push", "origin", "HEAD:refs/heads/olcum-otomatik")
    return is_, uzak


def _uzak_dosyalar(uzak: Path) -> set[str]:
    return set(_g(uzak, "ls-tree", "-r", "--name-only", "olcum-otomatik").splitlines())


# --------------------------------------------------------------- testler

def test_kanit_itilir_ve_uzak_dal_ilerler(hat):
    is_, uzak = hat
    once = _g(uzak, "rev-parse", "olcum-otomatik")
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")

    s = kanit_it.kanit_it(is_, mesaj="olcum: 20260902")

    assert s.durum == "islendi", s.aciklama
    assert _g(uzak, "rev-parse", "olcum-otomatik") != once
    assert "docs/kanit/gece-20260902-0300.log" in _uzak_dosyalar(uzak)


def test_ozellik_dalindaki_kod_uzak_dala_SIZMAZ(hat):
    """BULGU-24'ün ta kendisi: eski kod HEAD'i ittiği için v4 çalışması
    ölçüm dalına taşınıyordu. Yeni kod yalnız kanıtı taşımalı."""
    is_, uzak = hat
    _g(is_, "checkout", "-b", "ip-46-cekirdek")
    _yaz(is_, "app/cekirdek/anlam.py", "# yarim kalmis v4 isi\n")
    _g(is_, "add", "-A")
    _g(is_, "commit", "-m", "IP-46 yarim")
    # Bu dal, uzak olcum-otomatik'in torunu: eski kod burada hızlı-ileri
    # sarma yapar ve push BAŞARILI olurdu.
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")

    s = kanit_it.kanit_it(is_, mesaj="olcum: 20260902")

    assert s.durum == "islendi", s.aciklama
    dosyalar = _uzak_dosyalar(uzak)
    assert "docs/kanit/gece-20260902-0300.log" in dosyalar
    assert "app/cekirdek/anlam.py" not in dosyalar, "ozellik dali kodu sizdi"


def test_calisma_agaci_indeks_ve_HEAD_degismez(hat):
    is_, _ = hat
    _g(is_, "checkout", "-b", "ip-46-cekirdek")
    _yaz(is_, "app/yarim.py", "# hazirlanmis ama islenmemis\n")
    _g(is_, "add", "app/yarim.py")          # İhsan'ın hazırladığı indeks
    head_once = _g(is_, "rev-parse", "HEAD")
    dal_once = _g(is_, "rev-parse", "--abbrev-ref", "HEAD")
    indeks_once = _g(is_, "diff", "--cached", "--name-only")

    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")
    kanit_it.kanit_it(is_)

    assert _g(is_, "rev-parse", "HEAD") == head_once
    assert _g(is_, "rev-parse", "--abbrev-ref", "HEAD") == dal_once
    assert _g(is_, "diff", "--cached", "--name-only") == indeks_once
    assert (is_ / "app" / "yarim.py").exists()


def test_gecici_indeks_dosyasi_geride_birakilmaz(hat):
    is_, _ = hat
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")
    kanit_it.kanit_it(is_)
    assert not (is_ / ".git" / kanit_it.GECICI_INDEKS).exists()


def test_yeni_kanit_yoksa_commit_yaratilmaz(hat):
    is_, uzak = hat
    kanit_it.kanit_it(is_)                       # ilk çağrı: fark yok
    once = _g(uzak, "rev-parse", "olcum-otomatik")
    s = kanit_it.kanit_it(is_)
    assert s.durum == "yeni_kanit_yok"
    assert s.commit is None
    assert _g(uzak, "rev-parse", "olcum-otomatik") == once


def test_yerelde_silinen_kanit_uzaktan_dusurulmez(hat):
    """Kanıt ekle-only. `git add -A` kullanılsaydı bu test düşerdi."""
    is_, uzak = hat
    _yaz(is_, "docs/kanit/gece-20260901-0300.log", "eski\n")
    kanit_it.kanit_it(is_)
    (is_ / "docs" / "kanit" / "gece-20260901-0300.log").unlink()
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "yeni\n")

    kanit_it.kanit_it(is_)

    dosyalar = _uzak_dosyalar(uzak)
    assert "docs/kanit/gece-20260901-0300.log" in dosyalar
    assert "docs/kanit/gece-20260902-0300.log" in dosyalar


def test_push_her_zaman_hizli_ileri_sarmadir(hat):
    """Başka bir makine araya girse bile kanıt kaybolmaz: taban her
    seferinde uzak dalın GÜNCEL tepesinden okunur."""
    is_, uzak = hat
    baska = is_.parent / "baska"
    _g(is_.parent, "clone", str(uzak), str(baska))
    _yaz(baska, "docs/kanit/gece-baska.log", "baska makine\n")
    _g(baska, "add", "-A")
    _g(baska, "commit", "-m", "baska")
    _g(baska, "push", "origin", "HEAD:refs/heads/olcum-otomatik")

    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")
    s = kanit_it.kanit_it(is_)

    assert s.durum == "islendi", s.aciklama
    dosyalar = _uzak_dosyalar(uzak)
    assert "docs/kanit/gece-baska.log" in dosyalar          # ezilmedi
    assert "docs/kanit/gece-20260902-0300.log" in dosyalar


def test_uzak_dal_hic_yoksa_yaratilir(hat, tmp_path):
    is_, _ = hat
    yeni_uzak = tmp_path / "yeni.git"
    _g(tmp_path, "init", "--bare", str(yeni_uzak))
    _g(is_, "remote", "add", "yedek", str(yeni_uzak))
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")

    s = kanit_it.kanit_it(is_, uzak="yedek", dal="olcum-otomatik")

    assert s.durum == "islendi", s.aciklama
    assert "docs/kanit/gece-20260902-0300.log" in _uzak_dosyalar(yeni_uzak)


def test_uzak_tanimli_degilse_sessizce_yutulmaz(tmp_path):
    depo = tmp_path / "yalniz"
    depo.mkdir()
    _g(depo, "init", "-b", "olcum-otomatik")
    _yaz(depo, "docs/kanit/x.log", "x\n")
    _g(depo, "add", "-A")
    _g(depo, "commit", "-m", "t")

    s = kanit_it.kanit_it(depo)

    assert s.durum == "uzak_yok"
    assert not s.basarili
    assert "uzak" in s.aciklama.lower()


def test_git_deposu_degilse_patlamaz(tmp_path):
    s = kanit_it.kanit_it(tmp_path)
    assert s.durum == "git_yok"
    assert not s.basarili


def test_kuru_kosum_itmez(hat):
    is_, uzak = hat
    once = _g(uzak, "rev-parse", "olcum-otomatik")
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")

    s = kanit_it.kanit_it(is_, it=False)

    assert s.durum == "islendi"
    assert s.commit
    assert _g(uzak, "rev-parse", "olcum-otomatik") == once


def test_ozet_satiri_makine_okunur(hat):
    is_, _ = hat
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")
    s = kanit_it.kanit_it(is_)
    assert s.ozet().startswith("KANIT_IT durum=islendi commit=")


def test_cli_cikis_kodu(hat, capsys):
    is_, _ = hat
    _yaz(is_, "docs/kanit/gece-20260902-0300.log", "kosum\n")
    assert kanit_it.main(["--depo", str(is_), "--kuru"]) == 0
    assert "KANIT_IT durum=islendi" in capsys.readouterr().out
