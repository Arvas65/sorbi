"""Dinamik bağlantı katmanı testleri (v2 — Bağlantı Yöneticisi)."""
import os

import pytest

from app import connections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SATIS = os.path.join(HERE, "demo", "satis.db")


def test_build_url_sqlite():
    url = connections.build_url("sqlite", dosya="demo/satis.db")
    assert url.startswith("sqlite:///") and url.endswith("satis.db")


def test_build_url_postgres_sifre_kodlanir():
    url = connections.build_url("postgres", host="h", veritabani="db",
                                kullanici="u", sifre="p@ss:1")
    assert url == "postgresql+psycopg2://u:p%40ss%3A1@h:5432/db"


def test_build_url_mssql_odbc_parametresi():
    url = connections.build_url("mssql", host="h", veritabani="db",
                                kullanici="u", sifre="p")
    assert "pyodbc" in url and "driver=ODBC" in url


def test_build_url_bilinmeyen_tip():
    with pytest.raises(ValueError):
        connections.build_url("oracle")


def test_connection_basarili():
    r = connections.test_connection(connections.build_url("sqlite", dosya=SATIS))
    assert r["ok"] and "musteri" in r["tablolar"]


def test_connection_olmayan_sqlite_dosyasi():
    r = connections.test_connection(connections.build_url("sqlite", dosya="boyle_bir_dosya_yok.db"))
    assert not r["ok"] and "bulunamadı" in r["mesaj"]
    assert not os.path.exists("boyle_bir_dosya_yok.db")  # yan etki bırakma


def test_profil_sifre_diske_yazilmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(connections, "PROFIL_DOSYASI", str(tmp_path / "c.json"))
    connections.profil_kaydet("p1", {"tip": "postgres", "host": "h", "sifre": "COK_GIZLI"})
    icerik = open(tmp_path / "c.json", encoding="utf-8").read()
    assert "COK_GIZLI" not in icerik
    assert connections.profilleri_yukle()["p1"]["host"] == "h"
    connections.profil_sil("p1")
    assert connections.profilleri_yukle() == {}
