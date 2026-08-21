"""Mutasyon karnesinin kendi testleri.

Ölçüm aracı da bir yazılımdır ve yanlış ölçebilir. Buradaki testler mutasyon
üreticilerinin gerçekten BOZDUĞUNU doğrular — bozmayan bir mutasyon, kontrolü
haksız yere başarılı gösterir.
"""
import pytest

from eval.guven_olcum import (
    _mutant_bos_kume,
    _mutant_filtre_degeri,
    _mutant_limit_dus,
    _mutant_toplama,
    _mutant_where_dus,
)


def test_filtre_degeri_yazimi_degistirir():
    m = _mutant_filtre_degeri("SELECT * FROM t WHERE durum = 'Iptal'")
    assert m is not None and "'Iptal'" not in m


def test_filtre_degeri_metin_yoksa_none():
    assert _mutant_filtre_degeri("SELECT COUNT(*) FROM t") is None


def test_where_dus_kosulu_kaldirir_siralamayi_korur():
    m = _mutant_where_dus("SELECT a FROM t WHERE x = 1 ORDER BY a LIMIT 5")
    assert "WHERE" not in m.upper()
    assert "ORDER BY" in m.upper() and "LIMIT 5" in m.upper()


def test_where_dus_kosul_yoksa_none():
    assert _mutant_where_dus("SELECT a FROM t") is None


@pytest.mark.parametrize("sql,beklenen", [
    ("SELECT COUNT(*) FROM t", "SUM("),
    ("SELECT SUM(x) FROM t", "AVG("),
    ("SELECT AVG(x) FROM t", "SUM("),
])
def test_toplama_takasi(sql, beklenen):
    assert beklenen in _mutant_toplama(sql)


def test_toplama_yoksa_none():
    assert _mutant_toplama("SELECT a FROM t") is None


def test_limit_dus():
    assert _mutant_limit_dus("SELECT a FROM t ORDER BY a LIMIT 5").upper().endswith("BY A")


def test_limit_yoksa_none():
    assert _mutant_limit_dus("SELECT a FROM t") is None


def test_bos_kume_where_varken_ve_yokken_calisir():
    a = _mutant_bos_kume("SELECT a FROM t WHERE x = 1")
    b = _mutant_bos_kume("SELECT a FROM t")
    c = _mutant_bos_kume("SELECT a FROM t GROUP BY a")
    assert all("olmayan_deger" in m for m in (a, b, c))
    assert c.upper().index("WHERE") < c.upper().index("GROUP BY")


def test_uretilen_mutantlar_ayristirilabilir():
    """Ayrıştırılamayan mutant, güven kontrolünü sınamaz — ölçümü çürütür."""
    import sqlglot
    gold = "SELECT COUNT(*) FROM randevu WHERE durum = 'IPTAL' ORDER BY 1 LIMIT 5"
    for fn in (_mutant_filtre_degeri, _mutant_where_dus, _mutant_toplama,
               _mutant_limit_dus, _mutant_bos_kume):
        m = fn(gold)
        if m:
            assert sqlglot.parse_one(m, read="sqlite") is not None, fn.__name__


def test_karne_ozet_satiri_makine_okunur(capsys, monkeypatch):
    """kontrol.bat bu satırı okuyor; biçimi bir sözleşmedir.

    Hizalanmış insan çıktısını ayrıştırmak kırılgandı: bir boşluk değişince
    betik sessizce 'beklenenden farkli' der ve kimse sebebini anlamaz.
    """
    import sys

    from eval import guven_olcum
    monkeypatch.setattr(sys, "argv", ["guven_olcum.py", "--limit", "3"])
    guven_olcum.main()
    satirlar = [s for s in capsys.readouterr().out.splitlines()
                if s.startswith("KARNE_OZET")]
    assert len(satirlar) == 1
    alanlar = dict(p.split("=", 1) for p in satirlar[0].split()[1:])
    assert set(alanlar) == {"gun", "gold", "alarm", "mutant", "yakalanan", "zbos"}
    from eval.tarih_sabitle import olcum_gunu
    assert alanlar["gun"] == olcum_gunu()
    assert all(v.isdigit() for k, v in alanlar.items() if k != "gun")
