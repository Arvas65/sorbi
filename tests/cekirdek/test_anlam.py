"""A-1 kabul testleri — anlam modeli şeması ve doğrulaması.

SPEC A-1 kabul kriteri: `dogrula()` eksik zorunlu alanı ADIYLA reddeder
(tane, olay tarihi, geçerlilik üçü zorunlu); geçerli bir model ve EN AZ ALTI
farklı geçersiz model üzerinde koşar; kapalı devre — fırlatmaz, liste döner.
"""
from __future__ import annotations

import json

import pytest
from ornek import gecerli_model

from app.cekirdek.anlam import AnlamModeli, yukle
from app.cekirdek.tipler import Iliski, IliskiGuveni, Karar, Toplama, Tur

# --------------------------------------------------------------------------- #
#  Geçerli bir model — diğer her testin sapma noktası
# --------------------------------------------------------------------------- #

def test_gecerli_model_temiz_gecer():
    assert gecerli_model().dogrula() == []
    assert gecerli_model().gecerli


# --------------------------------------------------------------------------- #
#  Geçersiz modeller — her biri ayrı bir sessiz yanlış sınıfı
# --------------------------------------------------------------------------- #

def _tabloyu_degistir(m: AnlamModeli, ad: str, **alanlar) -> AnlamModeli:
    from dataclasses import replace
    yeni = dict(m.tablolar)
    yeni[ad] = replace(yeni[ad], **alanlar)
    return replace(m, tablolar=yeni)


def _boyutu_degistir(m: AnlamModeli, ad: str, **alanlar) -> AnlamModeli:
    from dataclasses import replace
    yeni = dict(m.boyutlar)
    yeni[ad] = replace(yeni[ad], **alanlar)
    return replace(m, boyutlar=yeni)


def test_gecersiz_1_tane_yazilmamis():
    m = _tabloyu_degistir(gecerli_model(), "randevu", tane="  ")
    sorunlar = m.dogrula()
    assert any("tane" in s and "randevu" in s for s in sorunlar), sorunlar


def test_gecersiz_2_olay_tarihi_secilmemis():
    m = _tabloyu_degistir(gecerli_model(), "randevu", olay_tarihi=None)
    sorunlar = m.dogrula()
    assert any("olay tarihi" in s for s in sorunlar), sorunlar


def test_gecersiz_3_olay_tarihi_olmayan_kolonu_gosteriyor():
    m = _tabloyu_degistir(gecerli_model(), "randevu", olay_tarihi="olmayan_kolon")
    sorunlar = m.dogrula()
    assert any("olmayan_kolon" in s for s in sorunlar), sorunlar


def test_gecersiz_4_gecerlilik_sorulmamis():
    """Eksen 8. `SORULMADI` ile `YOK` aynı şey değildir: birincisi bilgi
    eksikliği, ikincisi bir karardır."""
    m = _tabloyu_degistir(gecerli_model(), "randevu",
                          gecerlilik_karari=Karar.SORULMADI, gecerlilik=None)
    sorunlar = m.dogrula()
    assert any("sayılmaması" in s for s in sorunlar), sorunlar


def test_gecersiz_5_gecerlilik_var_ama_ifade_bos():
    m = _tabloyu_degistir(gecerli_model(), "randevu",
                          gecerlilik_karari=Karar.VAR, gecerlilik="")
    assert any("filtre ifadesi boş" in s for s in m.dogrula())


def test_gecersiz_6_varlik_tablosuna_olay_tarihi_verilmis():
    m = _tabloyu_degistir(gecerli_model(), "doktor", olay_tarihi="ad")
    assert any("Varlık tabloları olay taşımaz" in s for s in m.dogrula())


def test_gecersiz_7_olcu_olmayan_tabloya_dayaniyor():
    from dataclasses import replace
    m = gecerli_model()
    o = dict(m.olculer)
    o["randevu_sayisi"] = replace(o["randevu_sayisi"], tablo="yok_boyle_tablo")
    assert any("yok_boyle_tablo" in s for s in replace(m, olculer=o).dogrula())


def test_gecersiz_8_boyut_olmayan_kolonu_gosteriyor():
    m = _boyutu_degistir(gecerli_model(), "unvan", kolon="olmayan")
    assert any("olmayan" in s for s in m.dogrula())


def test_gecersiz_9_sozluk_sorulmamis():
    m = _boyutu_degistir(gecerli_model(), "cinsiyet",
                         sozluk_karari=Karar.SORULMADI, sozluk={})
    assert any("değer sözlüğü sorulmamış" in s for s in m.dogrula())


def test_gecersiz_10_maskeli_kolon_boyut_olamaz():
    m = _boyutu_degistir(gecerli_model(), "unvan", tablo="hasta", kolon="tckn")
    assert any("Maskeli kolon boyut olamaz" in s for s in m.dogrula())


def test_gecersiz_11_dusuk_guvenli_iliski_onaysiz():
    from dataclasses import replace
    m = gecerli_model()
    t = dict(m.tablolar)
    t["randevu"] = replace(
        t["randevu"],
        iliskiler=(Iliski("randevu", "doktor_id", "doktor", "doktor_id",
                          guven=IliskiGuveni.DUSUK),))
    assert any("ad benzerliğinden" in s for s in replace(m, tablolar=t).dogrula())


def test_gecersiz_12_hic_olay_tablosu_yok():
    m = _tabloyu_degistir(gecerli_model(), "randevu",
                          tur=Tur.VARLIK, olay_tarihi=None)
    assert any("hiç olay tablosu yok" in s for s in m.dogrula())


def test_gecersiz_13_surum_sifir():
    from dataclasses import replace
    assert any("Sürüm numarası" in s
               for s in replace(gecerli_model(), surum=0).dogrula())


# --------------------------------------------------------------------------- #
#  Kapalı devre ve serileştirme
# --------------------------------------------------------------------------- #

def test_dogrula_asla_firlatmaz():
    """Sözleşme: bozuk bir alan bile istisna değil, ileti üretir."""
    from dataclasses import replace
    bozuk = replace(gecerli_model(), tablolar={"randevu": "bu bir tablo değil"})
    sorunlar = bozuk.dogrula()          # fırlatırsa test burada patlar
    assert sorunlar and isinstance(sorunlar[0], str)


def test_gidis_donus_ayni_modeli_verir():
    m = gecerli_model()
    geri, sorunlar = yukle(m.to_json())
    assert sorunlar == []
    assert geri is not None
    assert geri.to_dict() == m.to_dict()


def test_yukle_bozuk_json_kapali_devre():
    model, sorunlar = yukle("{ bu json değil")
    assert model is None and sorunlar


def test_yukle_gecersiz_modeli_YUKLEMEZ():
    """Yarı geçerli bir model asla elde tutulmaz: `yukle` ya doğrulanmış bir
    model verir ya hiçbir şey. Aksi hâlde çağıran, doğrulamayı atlayan bir
    yol bulabilirdi."""
    ham = json.loads(gecerli_model().to_json())
    ham["tablolar"]["randevu"]["gecerlilik_karari"] = "sorulmadi"
    ham["tablolar"]["randevu"]["gecerlilik"] = None
    model, sorunlar = yukle(json.dumps(ham))
    assert model is None
    assert sorunlar


def test_sozluk_istem_icin_sadelestirilmis():
    """Sınır 1: eşleyiciye giden sözlükte SQL ifadesi, tablo ya da kolon adı
    bulunmaz."""
    metin = json.dumps(gecerli_model().sozluk(), ensure_ascii=False)
    for sizinti in ("COUNT(", "randevu.iptal", "doktor.unvan", "hasta_id",
                    "SELECT", "tckn"):
        assert sizinti not in metin, f"sözlükte sızıntı: {sizinti}"


def test_ortalama_yeniden_toplanamaz():
    assert Toplama.SAYIM.yeniden_toplanabilir
    assert Toplama.TOPLAM.yeniden_toplanabilir
    assert not Toplama.ORTALAMA.yeniden_toplanabilir


def test_model_degismez():
    m = gecerli_model()
    with pytest.raises(TypeError):
        m.tablolar["yeni"] = None            # MappingProxyType — yazılamaz


def test_yeni_surum_eskisini_bozmaz():
    m = gecerli_model()
    y = m.yeni_surum(onaylayan="baskasi")
    assert y.surum == m.surum + 1
    assert m.onaylayan == "ihsan"            # eski nesne dokunulmadan durur
