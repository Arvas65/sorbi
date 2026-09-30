"""ADR-5 B / SPEC E-6: API modu müşteri bağlantısında açılamaz (İP-45).

Kabul metni: "demo dışı bağlantıda API modunun açılamadığını gösteren test."
"""
import os

import pytest

from app import config
from app.akis.mod import API, YEREL, cikarim_modu, demo_mu

DEMO_DB = f"sqlite:///{os.path.join(config.DEMO_DIZINI, 'hospital.db')}"


def test_demo_veritabaninda_api_acilir():
    k = cikarim_modu(DEMO_DB, "api")
    assert k.mod == API and not k.kilitlendi and k.not_ == ""


@pytest.mark.parametrize("url", [
    "postgresql+psycopg2://u:p@hastane-replika:5432/hbys",
    "mysql+pymysql://u:p@db:3306/musteri",
    "mssql+pyodbc://u:p@db:1433/musteri?driver=ODBC+Driver+17+for+SQL+Server",
    "sqlite:////var/musteri/veri.db",
])
def test_musteri_baglantisinda_api_acilamaz(url):
    """Kabulün kendisi: istenen API, çıkan yerel — ve SESSİZ değil."""
    k = cikarim_modu(url, "api")
    assert k.mod == YEREL
    assert k.kilitlendi
    assert "ADR-5" in k.not_ and "yerelde" in k.not_


def test_kardes_dizin_demo_sayilmaz(tmp_path, monkeypatch):
    """`demo-musteri/` adı `demo` ile başlıyor diye demo değildir."""
    demo = tmp_path / "demo"
    kardes = tmp_path / "demo-musteri"
    demo.mkdir()
    kardes.mkdir()
    monkeypatch.setattr(config, "DEMO_DIZINI", str(demo))
    assert demo_mu(f"sqlite:///{demo / 'x.db'}")
    assert not demo_mu(f"sqlite:///{kardes / 'x.db'}")


def test_nokta_nokta_ile_kacilamaz(tmp_path, monkeypatch):
    demo = tmp_path / "demo"
    demo.mkdir()
    monkeypatch.setattr(config, "DEMO_DIZINI", str(demo))
    assert not demo_mu(f"sqlite:///{demo}/../musteri.db")


def test_sembolik_bag_demo_yapmaz(tmp_path, monkeypatch):
    """Demo dizinine konmuş bir bağ, dışarıdaki müşteri dosyasını demo yapmaz.

    Bağ dosya sisteminde KURULMAZ (Windows'ta yetki ister ve koşula bağlı
    atlama bu süitte yasak — test_suit_dururlugu). Onun yerine `realpath`
    bağın hedefini döndürecek şekilde taklit edilir: sınanan şey, kararın
    ad üzerinden değil ÇÖZÜLMÜŞ yol üzerinden verilmesidir.
    """
    import app.akis.mod as mod
    demo = tmp_path / "demo"
    demo.mkdir()
    bag, hedef = str(demo / "bag.db"), str(tmp_path / "musteri.db")
    gercek = os.path.realpath
    monkeypatch.setattr(mod.os.path, "realpath", lambda y: hedef if y == bag else gercek(y))
    monkeypatch.setattr(config, "DEMO_DIZINI", str(demo))
    assert not demo_mu(f"sqlite:///{bag}")
    assert demo_mu(f"sqlite:///{demo / 'gercek.db'}")


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite:///", "", None, 42])
def test_tuhaf_girdi_demo_degil_ve_patlamaz(url):
    assert demo_mu(url) is False
    assert cikarim_modu(url, "api").mod == YEREL


def test_yerel_istek_hic_not_uretmez():
    k = cikarim_modu("postgresql://u:p@h/db", "local")
    assert k.mod == YEREL and not k.kilitlendi and k.not_ == ""


def test_taninmayan_mod_yerele_duser_ve_soyler():
    k = cikarim_modu(DEMO_DB, "bulut")
    assert k.mod == YEREL and "Tanınmayan" in k.not_


def test_varsayilan_istek_configten_gelir(monkeypatch):
    monkeypatch.setattr(config, "MODE", "api")
    assert cikarim_modu("postgresql://u:p@h/db").mod == YEREL
    assert cikarim_modu(DEMO_DB).mod == API


def test_anlam_katmani_varsayilan_kapali():
    """v4 yolu ürüne bağlanana kadar kapalı; geri alma yolu da bu (SPEC B-4).

    Kaynaktan okunur: testi koşan makinede ortam değişkeni tanımlı olabilir.
    """
    import re
    kaynak = open(os.path.join(config.HERE, "app", "config.py"), encoding="utf-8").read()
    m = re.search(r'os\.getenv\("SORBI_ANLAM_KATMANI",\s*"([^"]*)"\)', kaynak)
    assert m and m.group(1) == "0"
