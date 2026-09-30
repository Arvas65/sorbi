"""Çoklu ölçüde çoğalma (BULGU-50) — derlenen SQL gerçek demo DB'de koşar ve
elle yazılmış doğru sorguyla karşılaştırılır.

Neden birim test yetmedi: 43 altın çift ve 787 test bu hatayı görmedi, çünkü
hiçbiri İKİ FARKLI olay tablosundan ölçüyü aynı seçimde istemiyordu. Hata
SQL metninde değil SAYIDA görünür; bu yüzden bekçi sayıya bakar.
"""
import os
import sqlite3

import pytest
from ornek import gecerli_model

from app import config
from app.cekirdek.derleyici import derle
from app.cekirdek.secim import Secim

DB = os.path.join(config.DEMO_DIZINI, "hospital.db")

UNVANA_GORE_CIRO = """
SELECT d.unvan, SUM(f.tutar) FROM fatura f
JOIN muayene m ON f.muayene_id = m.muayene_id
JOIN randevu r ON m.randevu_id = r.randevu_id
JOIN doktor d ON r.doktor_id = d.doktor_id GROUP BY d.unvan"""

UNVANA_GORE_ISLEM = """
SELECT d.unvan, SUM(mi.adet) FROM muayene_islem mi
JOIN muayene m ON mi.muayene_id = m.muayene_id
JOIN randevu r ON m.randevu_id = r.randevu_id
JOIN doktor d ON r.doktor_id = d.doktor_id GROUP BY d.unvan"""


def _kos(sql):
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as c:
        return {r[0]: r[1:] for r in c.execute(sql)}


def _derle(olculer, boyutlar=("unvan",)):
    m = gecerli_model()
    s = Secim.kur(m, olculer=olculer, boyutlar=boyutlar)
    assert s.kurulabilir, s.gecersiz
    return derle(s, m)


def test_farkli_tanede_iki_toplam_derlenmez_ve_sebebini_soyler():
    """Kabulün kendisi: sessiz yanlış üretmek yerine derlenmez (SPEC R-3)."""
    d = _derle(["islem_sayisi", "ciro"])
    assert not d.ok
    assert d.gecersiz, "gerekçesiz ret — kullanıcı neden cevap alamadığını bilmez"
    metin = " ".join(d.gecersiz)
    assert "ciro" in metin and "ŞİŞER" in metin and "ayrı kart" in metin


def test_sira_degisince_de_derlenmez():
    assert not _derle(["ciro", "islem_sayisi"]).ok


def test_tek_basina_her_olcu_dogru_sayiyi_verir():
    """Ret aşırı olmasın: ayrı kartlar olarak istenince ikisi de DOĞRU."""
    for olcu, dogru_sql in (("ciro", UNVANA_GORE_CIRO), ("islem_sayisi", UNVANA_GORE_ISLEM)):
        d = _derle([olcu])
        assert d.ok, d.gecersiz
        derlenen = _kos(d.sql)
        dogru = _kos(dogru_sql)
        assert derlenen == dogru, (olcu, derlenen, dogru)


def test_ayni_tablodan_iki_olcu_derlenir():
    """Aynı tanede iki ölçü güvenlidir; ret bunu da kapmamalı."""
    d = _derle(["ciro", "odenmemis_ciro"])
    assert d.ok, d.gecersiz


def test_benzersiz_sayim_cogalmaya_bagisik_ve_derlenir():
    """COUNT(DISTINCT) tekrar eden satırdan etkilenmez; reddedilmemeli ve DOĞRU olmalı."""
    d = _derle(["islem_sayisi", "randevu_sayisi"])
    assert d.ok, d.gecersiz
    derlenen = _kos(d.sql)
    dogru_islem = _kos(UNVANA_GORE_ISLEM)
    dogru_randevu = _kos("""SELECT d.unvan, COUNT(DISTINCT r.randevu_id) FROM randevu r
        JOIN doktor d ON r.doktor_id = d.doktor_id
        JOIN muayene m ON m.randevu_id = r.randevu_id
        JOIN muayene_islem mi ON mi.muayene_id = m.muayene_id
        WHERE r.durum <> 'IPTAL' GROUP BY d.unvan""")
    for unvan, (islem, randevu) in derlenen.items():
        assert islem == dogru_islem[unvan][0]
        assert randevu == dogru_randevu[unvan][0]


@pytest.mark.parametrize("olculer", [["islem_sayisi", "ortalama_fatura"],
                                     ["islem_sayisi", "odenmemis_ciro"]])
def test_ortalama_ve_kosullu_toplam_da_korunur(olculer):
    assert not _derle(olculer).ok
