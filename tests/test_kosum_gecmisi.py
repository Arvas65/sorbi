"""Koşum geçmişi denetimi — sabit yerine kendi geçmişi.

`BEKLENEN_TEST=320` sabiti aynı gün 6 test eklenince yanlış alarm üretti.
Bu testler, yerine geçen mekanizmanın doğru yönde çalıştığını sabitler:
düşüş uyarır, artış uyarmaz.
"""
from eval.kosum_gecmisi import durum, gecen_sayisi, onceki_sayi, yaz


def test_pytest_ciktisindan_sayi_okunur():
    assert gecen_sayisi("326 passed in 2.36s") == 326


def test_birden_cok_varsa_sonuncu_alinir():
    assert gecen_sayisi("5 passed\n... \n326 passed in 2.36s") == 326


def test_sayi_yoksa_none():
    assert gecen_sayisi("hicbir sey") is None
    assert gecen_sayisi("") is None


def test_dusus_sorundur():
    assert durum(320, 326) == "azaldi"


def test_artis_ilerlemedir():
    assert durum(326, 320) == "arti"


def test_ayni_kalmak_normaldir():
    assert durum(326, 326) == "ayni"


def test_ilk_kosum_kiyaslanmaz():
    assert durum(326, None) == "ilk"


def test_okunamayan_cikti_sorun_sayilmaz():
    """Log bozuksa uyarı üretmek, gerçek bir gerilemeyi gölgeler."""
    assert durum(None, 326) == "okunamadi"


def test_gecmis_ekle_only_ve_son_kayit_okunur(tmp_path):
    yol = str(tmp_path / "TEST-GECMIS.log")
    yaz(320, yol)
    yaz(326, yol)
    assert onceki_sayi(yol) == 326
    with open(yol, encoding="utf-8") as f:
        assert len(f.readlines()) == 2      # eski kayıt silinmedi


def test_gecmis_yoksa_none(tmp_path):
    assert onceki_sayi(str(tmp_path / "yok.log")) is None
