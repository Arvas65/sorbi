"""Doğrulama katmanı testleri (G-10 lehçe çevirisi, G-18 SELECT-only)."""
import pytest

from app.validator import ValidationResult, validate_and_transpile

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


# --------------------------------------------- kapı asla fırlatmaz (saha kaydı)

def test_kapanmamis_tirnak_cokme_yerine_red_doner():
    """2026-08-16: model, terim sözlüğünün bir parçasını SQL alanına kopyaladı.
    sqlglot TokenError fırlattı; yalnız ParseError yakalandığı için 50 soruluk
    ölçüm 30. soruda çöktü ve 29 sorunun sonucu kayboldu."""
    kotu = ("SUM(fatura.tutar) — fatura tablosundaki tutar toplamı\n"
            "TERIM 'tabu")
    r = validate_and_transpile(kotu)
    assert r.ok is False
    assert r.error                      # sessiz değil, açıklamalı


@pytest.mark.parametrize("girdi", [
    "",
    "   ",
    None,
    "SELECT 'kapanmamis",
    "'''",
    "SELECT * FROM t WHERE x = '",
    "```sql\nSELECT 1",
    "TABLO hasta\nKOLONLAR: ad, soyad",          # istemin kendisi
    "{\"sql\": \"SELECT 1\"}",                    # JSON, SQL değil
    "\x00\x01\x02",
    "SELECT " + "(" * 200,
    "-- yalnızca yorum",
])
def test_hicbir_girdi_istisna_firlatmaz(girdi):
    """Doğrulama katmanının sözleşmesi: her girdi için ValidationResult döner."""
    r = validate_and_transpile(girdi)
    assert isinstance(r, ValidationResult)
    if not r.ok:
        assert r.error, f"sessiz red: {girdi!r}"


def test_bos_sorgu_anlasilir_mesaj_verir():
    r = validate_and_transpile("")
    assert r.ok is False
    assert "boş" in r.error.lower()


# ------------------- takma ad yanlış pozitifi (saha kaydı 2026-08-16, 2. ölçüm)

ALIAS_TABLES = {"doktor", "hasta", "randevu", "fatura", "muayene", "bolum"}
ALIAS_COLUMNS = {
    "doktor": {"doktor_id", "ad", "soyad", "unvan", "bolum_id"},
    "hasta": {"hasta_id", "ad", "soyad", "sehir"},
    "randevu": {"randevu_id", "hasta_id", "doktor_id", "tarih", "durum"},
    "fatura": {"fatura_id", "muayene_id", "tutar", "odeme_durumu"},
    "muayene": {"muayene_id", "randevu_id", "tani"},
    "bolum": {"bolum_id", "ad"},
}


@pytest.mark.parametrize(("ad", "sql"), [
    ("ORDER BY takma ad",
     "SELECT h.ad, COUNT(*) AS randevu_sayisi FROM hasta h "
     "JOIN randevu r ON r.hasta_id = h.hasta_id GROUP BY h.hasta_id "
     "ORDER BY randevu_sayisi DESC LIMIT 5"),
    ("SUM takma adı",
     "SELECT b.ad, SUM(f.tutar) AS ciro FROM bolum b "
     "JOIN doktor d ON d.bolum_id = b.bolum_id "
     "JOIN randevu r ON r.doktor_id = d.doktor_id "
     "JOIN muayene m ON m.randevu_id = r.randevu_id "
     "JOIN fatura f ON f.muayene_id = m.muayene_id GROUP BY b.bolum_id ORDER BY ciro DESC"),
    ("HAVING takma ad",
     "SELECT doktor_id, COUNT(*) AS adet FROM randevu GROUP BY doktor_id HAVING adet > 5"),
    ("CTE adı ve kolonu",
     "WITH sayim AS (SELECT doktor_id, COUNT(*) AS n FROM randevu GROUP BY doktor_id) "
     "SELECT d.ad, sayim.n FROM doktor d JOIN sayim ON sayim.doktor_id = d.doktor_id"),
    ("türetilmiş tablo",
     "SELECT x.toplam FROM (SELECT SUM(tutar) AS toplam FROM fatura) x"),
])
def test_takma_adlar_halusinasyon_sayilmaz(ad, sql):
    """Reddedilen 10 sorgunun 9'u buydu: geçerli SQL, yanlış pozitif red.

    `ORDER BY ciro` içindeki `ciro` bir tablo kolonu değil, sorgunun kendi
    tanımladığı addır. Bunu halüsinasyon saymak, accuracy'yi kendi elimizle
    bastırmak demekti — üstelik istem modele 'hesapla ve adlandır' dedikçe
    yanlış pozitif daha da sık tetikleniyordu.
    """
    r = validate_and_transpile(sql, known_tables=ALIAS_TABLES, known_columns=ALIAS_COLUMNS)
    assert r.ok is True, f"{ad}: yanlış pozitif red — {r.error}"


@pytest.mark.parametrize(("ad", "sql"), [
    ("olmayan kolon nitelenmiş", "SELECT h.gender FROM hasta h"),
    ("olmayan kolon niteliksiz", "SELECT sex FROM hasta"),
    ("yanlış tablodan kolon", "SELECT muayene_id FROM doktor"),
    ("olmayan tablo", "SELECT * FROM uydurma_tablo"),
    ("takma ad başka kolonu meşrulaştırmaz",
     "SELECT COUNT(*) AS adet, gender FROM hasta"),
])
def test_halusinasyon_korumasi_bozulmadi(ad, sql):
    """Takma ad muafiyeti, gerçek halüsinasyonu geçirmemeli."""
    r = validate_and_transpile(sql, known_tables=ALIAS_TABLES, known_columns=ALIAS_COLUMNS)
    assert r.ok is False, f"{ad}: halüsinasyon sızdı"
