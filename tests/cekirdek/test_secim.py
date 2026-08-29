"""B-1 / G-1 testleri — seçim nesnesi.

Buradaki her test, v3'te SQL üretildikten SONRA yakalanmaya çalışılan bir
hata sınıfının üretimden ÖNCE yakalanmasıdır.
"""
from __future__ import annotations

from ornek import gecerli_model

from app.cekirdek.secim import Secim
from app.cekirdek.tipler import Filtre, Zaman, ZamanTanesi


def test_gecerli_secim_kurulur():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"])
    assert s.gecersiz == ()
    assert s.kurulabilir
    assert s.model_surumu == m.surum


def test_uydurulmus_olcu_adi_sqle_hic_donusmez():
    """v3'te model olmayan bir tablo/kolon uydurduğunda bu ancak SQL
    ayrıştırıldıktan sonra yakalanabiliyordu. Artık ad, sözlükte yoksa
    seçim hiç kurulmaz."""
    s = Secim.kur(gecerli_model(), olculer=["ciro"])
    assert not s.kurulabilir
    assert any("'ciro' diye bir ölçü yok" in g for g in s.gecersiz)
    # Hata iletisi öz-onarım için besleyici olmalı: var olanları sayar.
    assert any("randevu_sayisi" in g for g in s.gecersiz)


def test_bilinmeyen_boyut_reddedilir():
    s = Secim.kur(gecerli_model(), olculer=["randevu_sayisi"], boyutlar=["sehir"])
    assert any("'sehir' diye bir boyut yok" in g for g in s.gecersiz)


def test_sozluk_disi_filtre_degeri_reddedilir():
    """Eksen 4 — v3'ün en sık sessiz yanlışı.

    Model 'Kadın' yazar, kolonda 'K' vardır; sorgu çalışır, sıfır satır döner
    ve kullanıcı bunu "kayıt yok" diye okur. Sözlük varsa değer oradan
    gelmek zorundadır.
    """
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"],
                  filtreler=[Filtre("cinsiyet", "esittir", ("Bayan",))])
    assert any("'Bayan' diye bir değer yok" in g for g in s.gecersiz)

    # Hem ham değer ('K') hem gösterim ('Kadın') kabul edilir.
    for deger in ("K", "Kadın"):
        t = Secim.kur(m, olculer=["randevu_sayisi"],
                      filtreler=[Filtre("cinsiyet", "esittir", (deger,))])
        assert t.gecersiz == (), (deger, t.gecersiz)


def test_gecersiz_islec_reddedilir():
    s = Secim.kur(gecerli_model(), olculer=["randevu_sayisi"],
                  filtreler=[Filtre("cinsiyet", "gibi", ("K",))])
    assert any("geçerli bir işleç değil" in g for g in s.gecersiz)


def test_olcusuz_secim_kurulamaz():
    s = Secim.kur(gecerli_model(), boyutlar=["unvan"])
    assert any("Hiç ölçü seçilmedi" in g for g in s.gecersiz)


def test_siralama_secimde_olmayan_ada_yapilamaz():
    s = Secim.kur(gecerli_model(), olculer=["randevu_sayisi"],
                  sirala="cinsiyet azalan")
    assert any("seçimde yok" in g for g in s.gecersiz)


def test_negatif_limit_reddedilir():
    s = Secim.kur(gecerli_model(), olculer=["randevu_sayisi"], limit=0)
    assert any("Limit" in g for g in s.gecersiz)


# ------------------------------------------------------------------ G-1: saklama

def test_gidis_donus():
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"], boyutlar=["unvan"],
                  filtreler=[Filtre("cinsiyet", "icinde", ("K", "E"))],
                  zaman=Zaman(ZamanTanesi.AY, "2026-01-01", "2026-08-28", "bu yıl"),
                  sirala="randevu_sayisi azalan", limit=10)
    geri = Secim.from_json(s.to_json())
    assert geri.to_dict() == s.to_dict()
    assert geri.gecersiz == ()


def test_surum_uyusmazligi_sessizce_gecmez():
    """İP-23 dersinin seçim tarafı.

    Ölçü ADI aynı kalıp İFADESİ değişmiş olabilir. O durumda eski bir seçim
    yeni modelde başka bir şey ölçer ve kimse fark etmez. Bu yüzden sürüm
    uyuşmazlığı bir uyarı değil, bir DURDURMADIR.
    """
    m = gecerli_model()
    s = Secim.kur(m, olculer=["randevu_sayisi"])
    geri = Secim.from_json(s.to_json(), model_surumu=m.surum + 1)
    assert not geri.kurulabilir
    assert any("yeniden kurulmalı" in g for g in geri.gecersiz)


def test_bozuk_json_kapali_devre():
    s = Secim.from_json("{ bozuk")
    assert not s.kurulabilir
    assert any("çözümlenemedi" in g for g in s.gecersiz)


def test_kur_asla_firlatmaz():
    """Sözleşme: girdisi güvenilmeyen model çıktısıdır; kapı kapanır, çökmez."""
    s = Secim.kur(gecerli_model(), olculer=[None], boyutlar=[123])  # type: ignore[list-item]
    assert not s.kurulabilir
