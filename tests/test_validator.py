"""Doğrulama katmanı testleri (G-10 lehçe çevirisi, G-18 SELECT-only)."""
from app.validator import validate_and_transpile

TABLES = {"doktor", "hasta", "randevu"}
COLUMNS = {
    "doktor": {"doktor_id", "ad", "soyad", "bolum_id"},
    "hasta": {"hasta_id", "ad", "soyad", "sehir"},
    "randevu": {"randevu_id", "hasta_id", "doktor_id", "tarih", "durum"},
}


def test_gecerli_select():
    r = validate_and_transpile("SELECT ad FROM doktor LIMIT 3")
    assert r.ok and "SELECT" in r.sql and r.tables == ("doktor",)


def test_cte_ve_union_kabul():
    assert validate_and_transpile(
        "WITH x AS (SELECT ad FROM doktor) SELECT * FROM x").ok
    assert validate_and_transpile(
        "SELECT ad FROM doktor UNION SELECT ad FROM hasta").ok


def test_yazma_sorgulari_red():
    for sql in ["DELETE FROM hasta", "INSERT INTO hasta (ad) VALUES ('x')",
                "UPDATE hasta SET ad='x'", "DROP TABLE hasta",
                "CREATE TABLE t (a INT)"]:
        r = validate_and_transpile(sql)
        assert not r.ok, sql


def test_coklu_ifade_red():
    r = validate_and_transpile("SELECT 1; SELECT 2")
    assert not r.ok


def test_noktali_virgul_enjeksiyonu_red():
    r = validate_and_transpile("SELECT ad FROM hasta; DROP TABLE hasta")
    assert not r.ok


def test_bilinmeyen_tablo_red():
    r = validate_and_transpile("SELECT * FROM personel", known_tables=TABLES)
    assert not r.ok and "personel" in r.error


def test_bilinmeyen_kolon_red():
    r = validate_and_transpile("SELECT maas FROM doktor",
                               known_tables=TABLES, known_columns=COLUMNS)
    assert not r.ok and "maas" in r.error.lower()


def test_takma_adli_kolon_cozumu():
    r = validate_and_transpile(
        "SELECT d.ad FROM doktor d JOIN randevu r ON r.doktor_id = d.doktor_id",
        known_tables=TABLES, known_columns=COLUMNS)
    assert r.ok


def test_bozuk_sozdizimi_red():
    r = validate_and_transpile("SELECT FROM WHERE")
    assert not r.ok and "çözümlenemedi" in r.error


def test_lehce_cevirisi_postgres():
    r = validate_and_transpile("SELECT ad FROM doktor LIMIT 3",
                               target_dialect="postgres")
    assert r.ok
