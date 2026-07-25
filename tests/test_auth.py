"""Kimlik doğrulama testleri."""
import json

import pytest

from app import auth


@pytest.fixture(autouse=True)
def izole_dosya(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "KULLANICI_DOSYASI", str(tmp_path / "users.json"))


def test_ekle_ve_dogrula():
    auth.kullanici_ekle("ihsan", "cokgizli123", "yonetici")
    assert auth.dogrula("ihsan", "cokgizli123") == "yonetici"
    assert auth.dogrula("ihsan", "yanlis!!!") is None
    assert auth.dogrula("yok", "x") is None


def test_sifre_duz_metin_saklanmaz():
    auth.kullanici_ekle("a", "cokgizli123", "analist")
    icerik = open(auth.KULLANICI_DOSYASI, encoding="utf-8").read()
    assert "cokgizli123" not in icerik
    k = json.loads(icerik)["a"]
    assert set(k) == {"salt", "hash", "rol"} and len(k["hash"]) == 64


def test_ayni_sifre_farkli_hash():
    auth.kullanici_ekle("a", "cokgizli123", "analist")
    auth.kullanici_ekle("b", "cokgizli123", "analist")
    d = auth.kullanicilar()
    assert d["a"]["hash"] != d["b"]["hash"]  # kullanıcı başına salt


def test_kisa_sifre_ve_gecersiz_rol_red():
    with pytest.raises(ValueError):
        auth.kullanici_ekle("a", "kisa", "analist")
    with pytest.raises(ValueError):
        auth.kullanici_ekle("a", "cokgizli123", "superadmin")
    with pytest.raises(ValueError):
        auth.kullanici_ekle("  ", "cokgizli123", "analist")


def test_sifre_degistir():
    auth.kullanici_ekle("a", "eskisifre1", "analist")
    auth.sifre_degistir("a", "yenisifre1")
    assert auth.dogrula("a", "eskisifre1") is None
    assert auth.dogrula("a", "yenisifre1") == "analist"


def test_son_yonetici_silinemez():
    auth.kullanici_ekle("admin", "cokgizli123", "yonetici")
    auth.kullanici_ekle("analist1", "cokgizli123", "analist")
    auth.kullanici_sil("analist1")
    with pytest.raises(ValueError):
        auth.kullanici_sil("admin")
