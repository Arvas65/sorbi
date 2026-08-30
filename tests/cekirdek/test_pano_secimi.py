"""D-1 kabul testleri — deterministik grafik seçimi.

SPEC D-1 kabul kriteri: `claude/26` §04 tablosundaki her satır için bir vaka;
ve grafik tipinin hiçbir kod yolunda LLM çıktısından okunmadığını zorlayan bir
erişim testi.
"""
from __future__ import annotations

import ast
import pathlib

from ornek import gecerli_model

from app.cekirdek import pano
from app.cekirdek.pano import GrafikTipi, grafik_sec, parca, plan, varsayim_metni
from app.cekirdek.secim import Secim
from app.cekirdek.tipler import Sonuc, Zaman, ZamanTanesi


def sonuc(n: int, durum: str = "BASARILI") -> Sonuc:
    return Sonuc(durum=durum, satir_sayisi=n,
                 satirlar=tuple(("x", i) for i in range(min(n, 3))))


# --------------------------------------------------------------------------- #
#  §04 tablosunun her satırı
# --------------------------------------------------------------------------- #

def test_1satir_1sayi_kpi():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"])
    assert grafik_sec(s, m, 1) is GrafikTipi.KPI


def test_tarih_boyutu_cizgi():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["randevu_tarihi"])
    assert grafik_sec(s, m, 12) is GrafikTipi.CIZGI


def test_uzun_zaman_serisi_hala_cizgi():
    """SPEC'ten sapma, bilinçli: 3 yıllık günlük seri 1000 noktadır ve çizgi
    onu sorunsuz gösterir. '>200 satır -> tablo' kuralı yalnız kategorik
    tarafa uygulanır; buraya uygulamak bilgi kaybı olurdu."""
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["randevu_tarihi"])
    assert grafik_sec(s, m, 1095) is GrafikTipi.CIZGI


def test_kategori_1sayi_cubuk():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    assert grafik_sec(s, m, 4) is GrafikTipi.CUBUK


def test_cok_kategori_cubuk_kalir_ama_kirpilir():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    assert grafik_sec(s, m, 60) is GrafikTipi.CUBUK
    p = parca(s, m, sonuc(60))
    assert p.kirpildi
    assert any("ilk 15" in n for n in p.notlar)


def test_tarih_arti_kirilim_coklu_cizgi():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"],
                  boyutlar=["randevu_tarihi", "unvan"])
    assert grafik_sec(s, m, 48) is GrafikTipi.COKLU_CIZGI


def test_cok_seri_kucuk_katlara_duser():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"],
                  boyutlar=["randevu_tarihi", "unvan"])
    assert grafik_sec(s, m, 5000) is GrafikTipi.KUCUK_KATLAR


def test_iki_boyut_iki_olcu_tabloya_duser():
    """Adı konmamış her desen tabloya düşer. 'Emin değilsem tablo' bilinçli
    varsayılan: yanlış bir grafik yanlış bir hikâye anlatır."""
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan", "cinsiyet"])
    assert grafik_sec(s, m, 20) is GrafikTipi.TABLO


def test_bos_sonuc_grafik_uretmez():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    assert grafik_sec(s, m, 0) is GrafikTipi.YOK


def test_kurulamayan_secim_grafik_uretmez():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["yok_boyle_bir_olcu"])
    assert grafik_sec(s, m, 10) is GrafikTipi.YOK


# --------------------------------------------------------------------------- #
#  Değişmez #6 — eksik parça sessizce kaybolmaz
# --------------------------------------------------------------------------- #

def test_bos_sonuca_sebep_yazilir():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    p = parca(s, m, sonuc(0))
    assert p.tip is GrafikTipi.YOK
    assert p.notlar and "kayıt bulunamadı" in p.notlar[0]


def test_hatali_sorgu_sebebiyle_gelir():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"])
    p = parca(s, m, Sonuc(durum="ZAMAN_ASIMI", hata="30 sn'de bitmedi"))
    assert p.tip is GrafikTipi.YOK
    assert "30 sn" in p.notlar[0]


def test_kurulamayan_secimin_gerekcesi_karta_gecer():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["yok_boyle_bir_olcu"])
    p = parca(s, m, sonuc(0))
    assert any("yok_boyle_bir_olcu" in n for n in p.notlar)


def test_eksik_kartlar_planda_listelenir():
    m = gecerli_model()
    iyi = parca(Secim.kur(m, olculer=["randevu_sayisi"]), m, sonuc(1))
    kotu = parca(Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"]),
                 m, sonuc(0))
    pl = plan("Randevular nasıl gidiyor?", [iyi, kotu])
    assert len(pl.eksikler) == 1
    assert not pl.bos                       # bir kart çalışıyor, pano ayakta


# --------------------------------------------------------------------------- #
#  Determinizm ve sıralama
# --------------------------------------------------------------------------- #

def test_ayni_girdi_ayni_cikti():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    assert {grafik_sec(s, m, 7) for _ in range(50)} == {GrafikTipi.CUBUK}


def test_kart_sirasi_deterministik():
    """Aynı soru iki kez sorulduğunda kartlar yer değiştirmez."""
    m = gecerli_model()
    kpi = parca(Secim.kur(m, olculer=["randevu_sayisi"]), m, sonuc(1))
    cub = parca(Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"]),
                m, sonuc(4))
    ciz = parca(Secim.kur(m, olculer=["randevu_sayisi"],
                          boyutlar=["randevu_tarihi"]), m, sonuc(12))
    a = [p.tip for p in plan("s", [cub, ciz, kpi]).parcalar]
    b = [p.tip for p in plan("s", [ciz, kpi, cub]).parcalar]
    assert a == b == [GrafikTipi.KPI, GrafikTipi.CIZGI, GrafikTipi.CUBUK]


def test_varsayim_kullaniciya_yazilir():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"],
                  zaman=Zaman(ZamanTanesi.AY, "2026-01-01", "2026-08-29", "bu yıl"))
    (metin,) = varsayim_metni(s)
    assert "bu yıl" in metin and "2026-01-01" in metin and "2026-08-29" in metin


# --------------------------------------------------------------------------- #
#  Erişim testi — grafik tipi LLM çıktısından okunamaz
# --------------------------------------------------------------------------- #

def test_pano_llm_ciktisina_dokunmaz():
    """Grafik seçimi modelin serbest metnine bakmaz.

    Ne garanti eder: `pano.py` içinde `EslemeSonucu`'nun serbest metin
    alanlarına (`ham_cikti`, `netlestirme_sorusu`, `onerilen_olcu`) hiçbir
    erişim yoktur ve modül `Esleyici`yi tanımaz.
    Ne garanti ETMEZ: çağıranın bu alanları okuyup `PanoParcasi.tip`'i elle
    kurmasını — o yolu kapatan şey `grafik_sec`in tek kaynak olmasıdır ve
    bu, review'da denetlenir.
    """
    yol = pathlib.Path(pano.__file__)
    agac = ast.parse(yol.read_text(encoding="utf-8"))
    yasak = {"ham_cikti", "netlestirme_sorusu", "onerilen_olcu", "secenekler"}
    bulunan = {d.attr for d in ast.walk(agac)
               if isinstance(d, ast.Attribute) and d.attr in yasak}
    assert not bulunan, f"pano.py LLM serbest metnine bakıyor: {bulunan}"

    adlar = {a.name.split(".")[0] for d in ast.walk(agac)
             if isinstance(d, ast.ImportFrom) and d.module for a in d.names}
    assert "Esleyici" not in adlar
    assert "EslemeSonucu" not in adlar


def test_grafik_secim_imzasi_serbest_metin_almaz():
    """`grafik_sec`in girdileri: seçim, model, satır sayısı. Metin yok."""
    import inspect
    parametreler = list(inspect.signature(grafik_sec).parameters)
    assert parametreler == ["secim", "model", "satir_sayisi"]
