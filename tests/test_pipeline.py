"""Uçtan uca akışın LLM'siz testleri.

`app/pipeline.py` bugüne kadar hiç test edilmemişti (kapsam %0) — oysa K1
güven eşiği, K2 doğrulama, K3 yürütme ve öz-onarım kararlarının hepsi burada
veriliyor. Üretici monkeypatch ile değiştirilerek her dal LLM'siz koşuluyor.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, pipeline  # noqa: E402


class Uretici:
    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.repair_cagrisi = 0

    def _al(self):
        return self.cevaplar.pop(0) if self.cevaplar else {"sql": "", "guven": 0.0}

    def generate(self, question, context, mode=None):
        return self._al(), "local"

    def repair(self, question, context, bad_sql, error, mode=None):
        self.repair_cagrisi += 1
        return self._al(), "local"


@pytest.fixture
def hat(monkeypatch, tmp_path):
    """Gerçek demo veritabanına karşı, sahte üreticiyle kurulmuş hat."""
    monkeypatch.setattr(config, "AUDIT_DB", str(tmp_path / "audit.db"))
    pipeline.reset_index()
    yield
    pipeline.reset_index()


def _kur(monkeypatch, *cevaplar):
    u = Uretici(*cevaplar)
    monkeypatch.setattr(pipeline, "generator", u)
    return u


# --------------------------------------------------------------- mutlu yol

def test_gecerli_sorgu_calisir_ve_sonuc_doner(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT COUNT(*) FROM doktor", "guven": 1.0})
    a = pipeline.ask("Kaç doktor var?")
    assert a.status == "OK"
    assert a.rowcount == 1 and a.rows[0][0] > 0


def test_uretilen_sql_her_zaman_geri_doner(hat, monkeypatch):
    """G-02: SQL kullanıcıdan gizlenmez — hata durumunda bile."""
    _kur(monkeypatch, {"sql": "SELECT COUNT(*) FROM doktor", "guven": 1.0})
    assert pipeline.ask("Kaç doktor var?").sql.upper().startswith("SELECT")


# --------------------------------------------------------------- K1 güven eşiği

def test_dusuk_guven_netlestirme_ister(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT 1", "guven": 0.1, "aciklama": "Belirsiz."})
    a = pipeline.ask("şey")
    assert a.status == "DUSUK_GUVEN"
    assert "netleştirir misiniz" in a.message


def test_dusuk_guvende_sorgu_calistirilmaz(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT COUNT(*) FROM doktor", "guven": 0.0})
    assert pipeline.ask("şey").rowcount == 0


# --------------------------------------------------------------- K2 doğrulama

def test_yazma_sorgusu_reddedilir(hat, monkeypatch):
    """G-18: SELECT dışı hiçbir şey çalıştırılmaz — onarım da kurtaramaz."""
    _kur(monkeypatch,
         {"sql": "DELETE FROM doktor", "guven": 1.0},
         {"sql": "DROP TABLE doktor", "guven": 1.0})
    assert pipeline.ask("hepsini sil").status == "RED"


def test_olmayan_tablo_once_onarima_gider(hat, monkeypatch):
    u = _kur(monkeypatch,
             {"sql": "SELECT * FROM olmayan_tablo", "guven": 1.0},
             {"sql": "SELECT COUNT(*) FROM doktor", "guven": 1.0})
    a = pipeline.ask("Kaç doktor var?")
    assert u.repair_cagrisi == 1
    assert a.status == "OK"


def test_onarim_da_basarisizsa_red(hat, monkeypatch):
    _kur(monkeypatch,
         {"sql": "SELECT * FROM yok_1", "guven": 1.0},
         {"sql": "SELECT * FROM yok_2", "guven": 1.0})
    assert pipeline.ask("x").status == "RED"


# --------------------------------------------------------------- B-7 bayraklar

def test_bos_sonuc_bayrak_tasir(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT * FROM doktor WHERE unvan = 'YokBoyleBirUnvan'",
                       "guven": 1.0})
    a = pipeline.ask("YokBoyleBirUnvan unvanlı doktorlar kimler?")
    assert a.status == "OK"
    assert a.bayraklar, "sıfır satır dönen sorgu uyarısız geçmemeli"


def test_dogru_sorgu_bayraksiz_gecer(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT COUNT(*) FROM doktor", "guven": 1.0})
    assert pipeline.ask("Hastanede kaç doktor çalışıyor?").bayraklar == []


def test_bayraklar_cevabi_engellemez(hat, monkeypatch):
    """Uyarı bir RED değildir: kullanıcı sonucu yine de görür."""
    _kur(monkeypatch, {"sql": "SELECT * FROM doktor WHERE unvan = 'Yok'", "guven": 1.0})
    a = pipeline.ask("Yok unvanlı doktorlar?")
    assert a.status == "OK" and a.sql


# --------------------------------------------------------------- elle SQL

def test_elle_sql_de_dogrulamadan_gecer(hat, monkeypatch):
    _kur(monkeypatch)
    assert pipeline.ask("x", manual_sql="DELETE FROM doktor").status == "RED"


def test_elle_sql_calisir_ve_mod_isaretlenir(hat, monkeypatch):
    _kur(monkeypatch)
    a = pipeline.ask("x", manual_sql="SELECT COUNT(*) FROM doktor")
    assert a.status == "OK" and a.mode == "manual"


# --------------------------------------------------------------- G-07

def test_goreli_tarih_cozumlenir_ve_cevaba_yazilir(hat, monkeypatch):
    _kur(monkeypatch, {"sql": "SELECT COUNT(*) FROM randevu", "guven": 1.0})
    a = pipeline.ask("Geçen ay kaç randevu vardı?")
    assert a.resolved_dates, "G-07: göreli tarih mutlak aralığa çevrilmeli"
