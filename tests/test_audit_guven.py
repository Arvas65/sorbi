"""B7R-05: güven bayrakları denetim izine yazılıyor mu.

Triyaj notu: "Bugün yalnız kullanıcıya gösteriliyor." Ekran kapanınca bayrak
kayboluyordu; sahada hangi kontrolün kaç kez konuştuğunu kimse bilemiyordu.
Oysa B-7'nin SAHA karnesi (mutasyon karnesi değil) bu veriyle ölçülür.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import audit, config  # noqa: E402


def _izole(tmp_path, monkeypatch):
    yol = str(tmp_path / "denetim.db")
    monkeypatch.setattr(config, "AUDIT_DB", yol)
    return yol


def test_kodlar_yaziliyor_ve_geri_okunuyor(tmp_path, monkeypatch):
    _izole(tmp_path, monkeypatch)
    audit.write("ihsan", "iptal sayısı", "SELECT 1", "BASARILI", 3,
                guven_kodlari=["bos_sonuc", "deger_uyumsuz"])
    (satir,) = audit.recent(5)
    assert satir[-1] == "bos_sonuc,deger_uyumsuz"


def test_bayraksiz_kayit_bos_kalir(tmp_path, monkeypatch):
    _izole(tmp_path, monkeypatch)
    audit.write("ihsan", "kaç hasta", "SELECT 1", "BASARILI", 1)
    (satir,) = audit.recent(5)
    assert satir[-1] is None


def test_saha_karnesi_kod_bazinda_sayiyor(tmp_path, monkeypatch):
    _izole(tmp_path, monkeypatch)
    audit.write("a", "s1", "SELECT 1", "BASARILI", 1, guven_kodlari=["filtresiz"])
    audit.write("a", "s2", "SELECT 1", "BASARILI", 1,
                guven_kodlari=["filtresiz", "bos_sonuc"])
    audit.write("a", "s3", "SELECT 1", "BASARILI", 1)
    assert audit.guven_karnesi() == {"filtresiz": 2, "bos_sonuc": 1}


def test_eski_tablo_yerinde_goc_ediyor(tmp_path, monkeypatch):
    """Denetim izi ekleme-yalnızdır: tabloyu silip yeniden yaratmak kaydı yok
    etmek olurdu. Var olan kurulumda kolon yerinde eklenmeli."""
    yol = _izole(tmp_path, monkeypatch)
    con = sqlite3.connect(yol)
    con.execute("""CREATE TABLE denetim (
        id INTEGER PRIMARY KEY AUTOINCREMENT, zaman TEXT NOT NULL,
        kullanici TEXT NOT NULL, soru TEXT NOT NULL, sql TEXT,
        durum TEXT NOT NULL, satir_sayisi INTEGER, mod TEXT, sure_s REAL,
        elle_yazildi INTEGER DEFAULT 0)""")
    con.execute("INSERT INTO denetim (zaman, kullanici, soru, sql, durum) "
                "VALUES ('2026-08-01','eski','eski soru','SELECT 1','BASARILI')")
    con.commit()
    con.close()

    audit.write("yeni", "yeni soru", "SELECT 2", "BASARILI", 1,
                guven_kodlari=["filtresiz"])
    satirlar = audit.recent(10)
    assert len(satirlar) == 2, "eski kayıt silinmiş — denetim izi ekleme-yalnızdır"
    assert satirlar[0][-1] == "filtresiz"
    assert satirlar[1][-1] is None
