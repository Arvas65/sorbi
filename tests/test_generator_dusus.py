"""API → yerel düşüşü gözlemlenebilir mi (İP-15 / E-3).

Düşüşün kendisi tasarım gereği (Böl. 9 son-değer). Sessiz olması değildi:
hata yutulunca sahada 'neden API kullanılmıyor' sorusunun cevabı yoktu.
"""
import logging

import pytest

from app import generator


@pytest.fixture(autouse=True)
def _temiz():
    generator.SON_API_HATASI = None
    yield
    generator.SON_API_HATASI = None


def test_api_patlayinca_yerele_duser_ve_hata_kaydedilir(monkeypatch, caplog):
    monkeypatch.setattr(generator.config, "API_KEY", "x")
    monkeypatch.setattr(generator, "generate_api",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kota bitti")))
    monkeypatch.setattr(generator, "generate_local",
                        lambda *a, **k: {"sql": "SELECT 1", "guven": 1.0})

    with caplog.at_level(logging.WARNING):
        sonuc, mod = generator.generate("soru", "bağlam", mode="api")

    assert mod == "local"                       # düşüş çalışıyor
    assert sonuc["sql"] == "SELECT 1"
    assert "kota bitti" in generator.SON_API_HATASI
    assert "yerel" in caplog.text.lower()       # ve artık görünür


def test_api_calisiyorsa_hata_kaydi_kalmaz(monkeypatch):
    monkeypatch.setattr(generator.config, "API_KEY", "x")
    monkeypatch.setattr(generator, "generate_api",
                        lambda *a, **k: {"sql": "SELECT 2", "guven": 1.0})
    _sonuc, mod = generator.generate("soru", "bağlam", mode="api")
    assert mod == "api"
    assert generator.SON_API_HATASI is None


def test_yerel_modda_api_hic_denenmez(monkeypatch):
    monkeypatch.setattr(generator.config, "API_KEY", "x")

    def patlat(*a, **k):
        raise AssertionError("yerel modda API çağrılmamalı")

    monkeypatch.setattr(generator, "generate_api", patlat)
    monkeypatch.setattr(generator, "generate_local",
                        lambda *a, **k: {"sql": "SELECT 3", "guven": 1.0})
    _sonuc, mod = generator.generate("soru", "bağlam", mode="local")
    assert mod == "local"
