"""Yürütme katmanı testleri (G-14 salt-okunur + satır limiti).
Önkoşul: demo/hospital.db üretilmiş olmalı (python demo/seed_data.py).
"""
import os

import pytest

from app import executor

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "demo", "hospital.db")
DB_URL = f"sqlite:///{DB}"

pytestmark = pytest.mark.skipif(not os.path.exists(DB),
                                reason="demo/hospital.db yok — önce demo/seed_data.py çalıştırın")


def test_basarili_sorgu():
    r = executor.run("SELECT COUNT(*) FROM doktor", db_url=DB_URL)
    assert r.status == "BASARILI"
    assert r.rowcount == 1 and r.rows[0][0] > 0


def test_satir_limiti():
    r = executor.run("SELECT * FROM hasta", db_url=DB_URL, max_rows=10)
    assert r.status == "BASARILI" and r.rowcount == 10


def test_salt_okunur_yazma_engellenir():
    # Doğrulayıcı atlansa bile dosya düzeyinde mode=ro yazmayı engellemeli
    r = executor.run("INSERT INTO hasta (ad, soyad) VALUES ('x', 'y')", db_url=DB_URL)
    assert r.status != "BASARILI"


def test_calisma_hatasi_durumu():
    r = executor.run("SELECT olmayan_kolon FROM doktor", db_url=DB_URL)
    assert r.status == "CALISMA_HATASI" and r.error


def test_readonly_url_donusumu():
    url = executor._readonly_url("sqlite:///demo/hospital.db")
    assert "mode=ro" in url and "uri=true" in url
    # sqlite olmayan URL değişmez
    pg = "postgresql://u@h/db"
    assert executor._readonly_url(pg) == pg
