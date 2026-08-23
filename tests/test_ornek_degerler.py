"""Kategorik değer örnekleme (İP-03b, saha kaydı 2026-08-16 3. ölçüm).

0 JOIN'li soruların yarısı yanlıştı ve sebep şemayı değil DEĞERLERİ bilmemekti:
model `unvan = 'Profesör'` yazıyordu, kolonda `Prof. Dr.` vardı; `durum = 'İPTAL'`
yazıyordu, kolonda `IPTAL` vardı. İkincisi Türkçeye özgü: noktalı İ ile noktasız I
farklı harflerdir ve sorgu hata vermeden 0 satır döndürür.

Bu testler hem faydayı hem GİZLİLİK sınırını koruyor.
"""
import os
import sys

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config  # noqa: E402
from app.schema_rag import ContextIndex, ornek_degerler  # noqa: E402

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "demo", "hospital.db")
DB_URL = f"sqlite:///{DB}"


@pytest.fixture
def bellek_motoru():
    """Bellek-içi motor — ve KAPATILIR.

    Bu iki test motoru açıp hiç kapatmıyordu; her koşumda iki
    ResourceWarning bunlardan geliyordu. Uyarı, çöp toplayıcı ne zaman
    çalışırsa o an koşan teste yazılıyordu; bu yüzden her koşumda BAŞKA
    bir testin üstünde görünüyor ve kaynağı gizleniyordu.
    """
    eng = create_engine("sqlite:///:memory:")
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture(scope="module")
def idx():
    if not os.path.exists(DB):
        pytest.skip("demo/hospital.db yok")
    config.DB_URL = DB_URL
    return ContextIndex(DB_URL)


def _degerler(idx, tablo):
    for d in idx.schema:
        if d["table"] == tablo:
            if "aynen kullan):" not in d["text"]:
                return {}
            blok = d["text"].split("aynen kullan):\n")[1]
            return {s.split(" = ")[0].strip(): s.split(" = ")[1].split(" | ")
                    for s in blok.splitlines() if " = " in s}
    return {}


# ------------------------------------------------------------------ fayda

def test_kategorik_degerler_baglama_giriyor(idx):
    assert _degerler(idx, "doktor")["unvan"] == ["Doç. Dr.", "Dr.", "Prof. Dr.", "Uzm. Dr."]
    assert "IPTAL" in _degerler(idx, "randevu")["durum"]
    assert "GECIKTI" in _degerler(idx, "fatura")["odeme_durumu"]


def test_noktasiz_i_degeri_aynen_veriliyor(idx):
    """'IPTAL' — noktasız I. Model 'İPTAL' yazarsa sorgu sessizce 0 satır döner."""
    durum = _degerler(idx, "randevu")["durum"]
    assert "IPTAL" in durum
    assert "İPTAL" not in durum


# ------------------------------------------------------------ gizlilik sınırı

def test_maskeli_kolonlar_asla_orneklenmez(idx):
    """G-16: masked_columns listesindeki kolonların değerleri isteme kopyalanamaz."""
    hasta = _degerler(idx, "hasta")
    for yasak in ("ad", "soyad", "tckn", "dogum_tarihi"):
        assert yasak not in hasta, f"maskeli kolon örneklendi: hasta.{yasak}"


def test_kisi_tablosunda_ad_soyad_orneklenmez(idx):
    """`doktor` maskeli listede değil ama ad+soyad birlikte bulunduğu için kişi
    tablosudur — gerçek doktor adları isteme girmemeli."""
    doktor = _degerler(idx, "doktor")
    assert "ad" not in doktor and "soyad" not in doktor
    assert "unvan" in doktor          # kategorik olan kalmalı


def test_tek_ad_kolonu_olan_tablolar_orneklenir(idx):
    """`bolum.ad` ve `islem.ad` kişisel veri değil, soruların ihtiyaç duyduğu değerler."""
    assert "Kardiyoloji" in _degerler(idx, "bolum")["ad"]
    assert "MR" in _degerler(idx, "islem")["ad"]


def test_kisisel_desenli_kolonlar_elenir(bellek_motoru):
    eng = bellek_motoru
    with eng.connect() as c:
        c.exec_driver_sql("CREATE TABLE m (tckn TEXT, telefon TEXT, eposta TEXT, tur TEXT)")
        c.exec_driver_sql("INSERT INTO m VALUES ('123','555','a@b.c','A')")
        c.commit()
    bulunan = ornek_degerler(eng, "m", ["tckn", "telefon", "eposta", "tur"], set())
    assert set(bulunan) == {"tur"}


def test_yuksek_kardinalite_ve_uzun_metin_elenir(bellek_motoru):
    eng = bellek_motoru
    with eng.connect() as c:
        c.exec_driver_sql("CREATE TABLE t (kod TEXT, serbest TEXT)")
        for i in range(40):
            c.exec_driver_sql("INSERT INTO t VALUES (?, ?)", (f"k{i}", "x" * 80))
        c.commit()
    bulunan = ornek_degerler(eng, "t", ["kod", "serbest"], set())
    assert bulunan == {}          # 40 farklı değer + 80 karakterlik serbest metin


def test_kapatilabilir(monkeypatch):
    """API modunda bu adım kapatılmalı — değerler gerçek veridir ve dışarı gider."""
    monkeypatch.setattr(config, "ORNEK_DEGERLER", False)
    from app.schema_rag import discover_schema
    docs, _, _, _ = discover_schema(DB_URL, set())
    assert all("DEĞERLER" not in d["text"] for d in docs)


def test_ornek_deger_kapaliyken_istem_temiz_ama_kontrol_gorur(monkeypatch):
    """İP-19: kısıt İSTEME yazmayı kapatır, OKUMAYI değil.

    API modunda değerler dış servise gitmemeli — ama güven kontrolü tamamen
    yerelde koşuyor ve aynı bilgi olmadan kör kalıyor.
    """
    from app import config as cfg
    from app.schema_rag import discover_schema

    monkeypatch.setattr(cfg, "ORNEK_DEGERLER", False)
    docs, _cols, _edges, degerler = discover_schema(DB_URL, set())

    assert not any("DEĞERLER" in d["text"] for d in docs), "istemde değer olmamalı"
    assert degerler, "güven kontrolü için değer haritası yine de dolmalı"
    assert "unvan" in degerler


def test_maskeli_kolon_hicbir_kosulda_orneklenmez(monkeypatch):
    """G-16 değişmedi: maskeleme okumayı da engeller."""
    from app import config as cfg
    from app.schema_rag import discover_schema

    monkeypatch.setattr(cfg, "ORNEK_DEGERLER", True)
    _docs, _cols, _edges, degerler = discover_schema(DB_URL, {"unvan"})
    assert "unvan" not in degerler
