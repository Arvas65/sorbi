"""A-5 testleri — anlam modeli dosyası, sürüm geçmişi, şema kayması."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from ornek import gecerli_model

from app.baglanti.anlam_deposu import DosyaAnlamDeposu, fark, slug
from app.cekirdek.tipler import Karar


def depo(tmp_path) -> DosyaAnlamDeposu:
    return DosyaAnlamDeposu(tmp_path)


def guncel_sema(model) -> dict[str, tuple[str, ...]]:
    return {ad: tuple(t.kolonlar) for ad, t in model.tablolar.items()}


# --------------------------------------------------------------------- yol adı

def test_slug_yol_kacisina_kapali():
    """Bağlantı adı kullanıcıdan gelir ve dosya adına dönüşür."""
    assert "/" not in slug("../../etc/passwd")
    assert "\\" not in slug(r"..\..\windows\system32")
    assert ".." not in slug("../gizli")
    assert slug("HBYS Demo (Test)") == "hbys-demo-test"
    assert slug("   ") == "adsiz"


def test_yol_dizinin_disina_cikamaz(tmp_path):
    d = depo(tmp_path)
    p = d.yol("../../kacis")
    assert d.dizin.resolve() in p.resolve().parents


# ------------------------------------------------------------- yazma ve okuma

def test_yaz_oku_gidis_donus(tmp_path):
    d, m = depo(tmp_path), gecerli_model()
    assert d.yaz(m) == m.surum
    geri = d.oku(m.baglanti)
    assert geri is not None
    assert geri.to_dict() == m.to_dict()


def test_olmayan_model_none_doner(tmp_path):
    model, sorunlar = depo(tmp_path).oku_ayrintili("hic-yok")
    assert model is None and sorunlar == []      # yokluk bir hata değildir


def test_gecersiz_model_yazilmaz_ve_bagirir(tmp_path):
    """Sınırda kapalı devre, içeride yüksek ses.

    Buraya gelen model sihirbazın ürettiğidir; sessizce yazmamak veri kaybı
    olurdu.
    """
    d = depo(tmp_path)
    m = gecerli_model()
    t = dict(m.tablolar)
    t["randevu"] = replace(t["randevu"], gecerlilik_karari=Karar.SORULMADI,
                           gecerlilik=None)
    with pytest.raises(ValueError, match="sayılmaması"):
        d.yaz(replace(m, tablolar=t))
    assert not d.yol(m.baglanti).exists()


def test_elle_bozulmus_dosya_none_doner_ve_sebep_yazar(tmp_path):
    """Okuma tarafı kapalı devre: dosyayı bir insan düzenlemiş olabilir."""
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)
    ham = json.loads(d.yol(m.baglanti).read_text(encoding="utf-8"))
    ham["tablolar"]["randevu"]["gecerlilik_karari"] = "sorulmadi"
    ham["tablolar"]["randevu"]["gecerlilik"] = None
    d.yol(m.baglanti).write_text(json.dumps(ham), encoding="utf-8")

    model, sorunlar = d.oku_ayrintili(m.baglanti)
    assert model is None
    assert sorunlar and "sayılmaması" in sorunlar[0]


def test_bozuk_json_cokertmez(tmp_path):
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)
    d.yol(m.baglanti).write_text("{ bu json degil", encoding="utf-8")
    model, sorunlar = d.oku_ayrintili(m.baglanti)
    assert model is None and sorunlar


# ------------------------------------------------------------- sürüm geçmişi

def test_yeni_surum_oncekini_arsivler(tmp_path):
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)                                     # v3
    d.yaz(m.yeni_surum(onaylayan="ikinci"))      # v4
    assert d.gecmis(m.baglanti) == [m.surum]
    assert d.oku(m.baglanti).surum == m.surum + 1

    eski = d.surum_oku(m.baglanti, m.surum)
    assert eski is not None and eski.onaylayan == "ihsan"


def test_arsiv_ekle_only(tmp_path):
    """Aynı sürüm numarası ikinci kez üstüne yazılmaz (Değişmez #5)."""
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)
    d.yaz(m.yeni_surum())
    ilk = d.surum_oku(m.baglanti, m.surum).to_dict()

    d.sil(m.baglanti)
    d.yaz(replace(m, onaylayan="baskasi"))       # aynı sürüm, farklı içerik
    d.yaz(m.yeni_surum())
    assert d.surum_oku(m.baglanti, m.surum).to_dict() == ilk   # arşiv değişmedi


def test_gecmis_bozuk_dosya_adini_atlar(tmp_path):
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)
    d.yaz(m.yeni_surum())
    (d.gecmis_dizini / f"{slug(m.baglanti)}-vABC.json").write_text("{}", encoding="utf-8")
    assert d.gecmis(m.baglanti) == [m.surum]


def test_iki_baglanti_ayri_dosyada(tmp_path):
    d, m = depo(tmp_path), gecerli_model()
    d.yaz(m)
    d.yaz(replace(m, baglanti="satis-demo"))
    assert d.oku("hbys-demo").baglanti == "hbys-demo"
    assert d.oku("satis-demo").baglanti == "satis-demo"


# --------------------------------------------------------------- şema kayması

def test_degismemis_sema_farksiz():
    m = gecerli_model()
    f = fark(m, guncel_sema(m))
    assert not f.var and not f.bozuk
    assert f.sorulacak_tablolar == ()


def test_yeni_kolon_yalniz_o_tabloyu_sorar():
    """Sihirbaz tüm modeli değil YALNIZ farkı sorar — yoksa şemaya bir kolon
    eklendiği için kullanıcı yarım saatlik oturuma geri gönderilirdi."""
    m = gecerli_model()
    s = guncel_sema(m)
    s["hasta"] = s["hasta"] + ("email",)
    f = fark(m, s)
    assert f.yeni_kolonlar == {"hasta": ("email",)}
    assert f.sorulacak_tablolar == ("hasta",)
    assert not f.bozuk                       # yeni kolon zararsızdır


def test_yeni_tablo_sorulacaklara_girer():
    m = gecerli_model()
    s = guncel_sema(m)
    s["fatura"] = ("fatura_id", "tutar")
    f = fark(m, s)
    assert f.yeni_tablolar == ("fatura",)
    assert "fatura" in f.sorulacak_tablolar


def test_kaybolan_kolon_boyutu_bozar():
    m = gecerli_model()
    s = guncel_sema(m)
    s["doktor"] = tuple(k for k in s["doktor"] if k != "unvan")
    f = fark(m, s)
    assert f.kaybolan_kolonlar == {"doktor": ("unvan",)}
    assert "unvan" in f.bozulan_boyutlar
    assert f.bozuk


def test_kaybolan_tablo_olcuyu_bozar():
    m = gecerli_model()
    s = guncel_sema(m)
    del s["randevu"]
    f = fark(m, s)
    assert f.kaybolan_tablolar == ("randevu",)
    assert "randevu_sayisi" in f.bozulan_olculer
    assert "randevu_tarihi" in f.bozulan_boyutlar
    assert f.bozuk


def test_fark_veritabani_gormez():
    """`fark` saf: girdisi bir sözlük, çıktısı bir değer. Bu sayede
    sihirbazın kayma mantığı LLM'siz ve DB'siz test edilebiliyor."""
    import inspect
    assert list(inspect.signature(fark).parameters) == ["model", "guncel"]
