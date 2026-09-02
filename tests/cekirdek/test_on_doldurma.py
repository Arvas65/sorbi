"""A-2 kabul testleri — şemadan ön-doldurma.

SPEC A-2 kabul kriteri: ön-doldurma bir ÖNERİ üretir, karar üretmez; öneri
`dogrula()`'dan geçmez; sihirbazın soru kümesi doğrulamanın istediği her şeyi
kapsar (boşluk yok).

Buradaki testlerin çoğu, ilk taslakta GERÇEKTEN olmuş bir hatanın nöbetçisidir.
Taslak `demo/hospital.db` üzerinde denendiğinde:

  * `hasta.olay_tarihi = "dogum_tarihi"` yazdı — hastalar doğum tarihine göre
    sayılırdı ve alan dolu göründüğü için sihirbaz bunu SORMUYORDU.
  * `bolum.ad` ve `islem.ad`'ı kişisel veri sayıp maskeledi — şemanın
    okunabilir tek etiketleri yok oldu.
  * 32 boyutun yarısı anahtar kolonuydu (`hasta_id`, `randevu_id`, ...).

Üçü de sessiz: ne tip sistemi, ne `dogrula()`, ne de bir birim testi yakalar.
Yalnız gerçek şema üzerinde ÇALIŞTIRMAK yakaladı — SPEC R-6'nın aynısı.
"""
from __future__ import annotations

import ast
import dataclasses
import pathlib
import sqlite3
from dataclasses import replace

import pytest

from app.cekirdek import on_doldurma as od
from app.cekirdek.on_doldurma import (
    OlcumGirdisi,
    Oneri,
    acik_sorular,
    gecerlilik_adaylari,
    kardinalite_belirle,
    maskeli_adaylari,
    oner,
    tarih_adaylari,
    tur_tahmini,
    turleri_tahmin_et,
)
from app.cekirdek.tipler import (
    Iliski,
    Karar,
    Kardinalite,
    KolonSemasi,
    TabloSemasi,
    Toplama,
    Tur,
)

DEMO = pathlib.Path(__file__).resolve().parents[2] / "demo" / "hospital.db"


def kol(ad: str, tip: str = "TEXT") -> KolonSemasi:
    return KolonSemasi(ad=ad, tip=tip)


def tablo(ad: str, *kolonlar: KolonSemasi) -> TabloSemasi:
    return TabloSemasi(ad=ad, kolonlar=tuple(kolonlar))


# --------------------------------------------------------------------------- #
#  Taşıyıcı kural — öneri bir KARAR DEĞİLDİR
# --------------------------------------------------------------------------- #

def test_oneri_gecerli_bir_model_degildir():
    """Modülün tek taşıyıcı kuralı. Bu test kırmızıya dönerse, ön-doldurma
    insan onayı olmadan kaydedilebilir bir model üretiyor demektir."""
    o = oner("x", [tablo("satis", kol("satis_id", "INTEGER"), kol("tarih", "DATE"))], [])
    assert not o.model.gecerli
    assert o.model.dogrula()


def test_hicbir_karar_alani_doldurulmaz():
    o = oner("x", [tablo("satis", kol("satis_id", "INTEGER"), kol("tarih", "DATE"),
                         kol("durum"))], [])
    t = o.model.tablolar["satis"]
    assert t.olay_tarihi is None                 # eksen 7 — insan seçer
    assert t.gecerlilik_karari is Karar.SORULMADI  # eksen 8 — insan cevaplar
    assert all(b.sozluk_karari is Karar.SORULMADI
               for b in o.model.boyutlar.values())  # eksen 4 — insan onaylar


def test_olay_tarihi_asla_doldurulmaz_aday_olarak_verilir():
    """İlk taslağın hatası: en güçlü adayı alana YAZIYORDU.

    Dolu bir alan alınmış bir karar gibi okunur ve `acik_sorular()` onu
    sormaz. `hasta` tablosunda bunun sonucu `olay_tarihi = dogum_tarihi`
    idi — sessiz, kalıcı ve tam olarak eksen 7'nin kaçındığımız yanlışı.
    """
    t = tablo("yatis", kol("yatis_id", "INTEGER"), kol("hasta_id", "INTEGER"),
              kol("giris_tarihi", "DATE"))
    o = oner("x", [t, tablo("hasta", kol("hasta_id", "INTEGER"))],
             [Iliski("yatis", "hasta_id", "hasta", "hasta_id")])
    assert o.model.tablolar["yatis"].olay_tarihi is None
    assert o.tarih_adaylari["yatis"] == ("giris_tarihi",)
    soru = " ".join(acik_sorular(o)["yatis"])
    assert "Ne zaman oldu" in soru and "giris_tarihi" in soru


# --------------------------------------------------------------------------- #
#  Tarih adayları — sıra bir görüştür, kod onu tutmak zorunda
# --------------------------------------------------------------------------- #

def test_olay_tarihi_kayit_tarihinden_once_gelir():
    """`kayit_tarihi` bilerek sonda: kaydın açıldığı tarih, olayın olduğu
    tarih değildir. İlk sürümde bu niyet koda GEÇMİYORDU — genel `_tarihi$`
    kalıbı `kayit_tarihi`'ni önce yakalıyor, özel kural hiç çalışmıyordu."""
    t = tablo("siparis", kol("kayit_tarihi", "DATE"), kol("tarih", "DATE"))
    assert tarih_adaylari(t) == ("tarih", "kayit_tarihi")


def test_dogum_ve_guncelleme_tarihleri_de_geride():
    t = tablo("kisi", kol("dogum_tarihi", "DATE"), kol("guncelleme_zamani", "DATE"),
              kol("islem_tarihi", "DATE"))
    assert tarih_adaylari(t)[0] == "islem_tarihi"
    assert set(tarih_adaylari(t)[1:]) == {"dogum_tarihi", "guncelleme_zamani"}


def test_adi_tarih_demeyen_ama_tipi_tarih_olan_kolon_en_sonda():
    t = tablo("olay", kol("bitis", "TIMESTAMP"), kol("tarih", "DATE"))
    assert tarih_adaylari(t) == ("tarih", "bitis")


def test_tarihsiz_tablo_bos_aday_verir():
    assert tarih_adaylari(tablo("bolum", kol("bolum_id", "INTEGER"), kol("ad"))) == ()


def test_gecerlilik_adaylari_durum_kolonunu_bulur():
    t = tablo("randevu", kol("randevu_id", "INTEGER"), kol("durum"), kol("tarih", "DATE"))
    assert gecerlilik_adaylari(t) == ("durum",)


def test_gecerlilik_adayi_yoksa_soru_yine_sorulur():
    """Eksen 8'in özü: aday bulunamaması "geçersiz satır yok" demek değildir.
    Kolon adı `sil_bunu` gibi tuhaf olabilir; cevabı insan bilir."""
    o = oner("x", [tablo("satis", kol("satis_id", "INTEGER"), kol("tarih", "DATE"))], [])
    assert any("sayılmamalı" in q for q in acik_sorular(o)["satis"])


# --------------------------------------------------------------------------- #
#  Maskeleme — fazla maskelemek de bir hatadır
# --------------------------------------------------------------------------- #

def test_kisisel_kolonlar_maskelenir():
    t = tablo("hasta", kol("hasta_id", "INTEGER"), kol("tckn"), kol("ad"),
              kol("soyad"), kol("sehir"))
    assert set(maskeli_adaylari(t)) == {"hasta.tckn", "hasta.ad", "hasta.soyad"}
    assert "hasta.sehir" not in maskeli_adaylari(t)


def test_bolum_adi_kisisel_veri_degildir():
    """İlk taslak `^ad$`'ı koşulsuz maskeliyordu; `bolum.ad` ve `islem.ad` de
    gitti ve şemada gruplanacak okunabilir hiçbir etiket kalmadı. Aşırı
    maskeleme gizlilik değil körlük üretir."""
    assert maskeli_adaylari(tablo("bolum", kol("bolum_id", "INTEGER"), kol("ad"),
                                  kol("kat", "INTEGER"))) == ()


def test_zayif_im_guclu_im_varsa_maskelenir():
    """`ad` tek başına karar vermez: yanında `soyad` varsa kişi tablosudur."""
    assert "doktor.ad" in maskeli_adaylari(
        tablo("doktor", kol("ad"), kol("soyad"), kol("unvan")))


def test_maskeli_kolon_boyut_olamaz():
    o = oner("x", [tablo("hasta", kol("hasta_id", "INTEGER"), kol("tckn"),
                         kol("ad"), kol("soyad"), kol("sehir"))], [])
    kolonlar = {(b.tablo, b.kolon) for b in o.model.boyutlar.values()}
    assert ("hasta", "tckn") not in kolonlar
    assert ("hasta", "ad") not in kolonlar
    assert ("hasta", "sehir") in kolonlar


def test_maskeleme_kararı_insana_gosterilir():
    """`dogrula()` maskelemeden şikâyet etmez — ama maskeleme de bir
    TAHMİNDİR ve yanlışsa kimse fark etmez. Doğrulamanın susması, insanın
    görmemesi için gerekçe değil."""
    o = oner("x", [tablo("hasta", kol("hasta_id", "INTEGER"), kol("tckn"))], [])
    assert any("kişisel veri sayıldı" in q for q in acik_sorular(o)["hasta"])


# --------------------------------------------------------------------------- #
#  Olay / varlık
# --------------------------------------------------------------------------- #

def test_iki_disa_fk_olan_tablo_olaydir():
    t = tablo("muayene_islem", kol("muayene_id", "INTEGER"), kol("islem_id", "INTEGER"))
    il = [Iliski("muayene_islem", "muayene_id", "muayene", "muayene_id"),
          Iliski("muayene_islem", "islem_id", "islem", "islem_id")]
    assert tur_tahmini(t, il) is Tur.OLAY        # tarihi olmasa bile


def test_isaret_edilen_ama_isaret_etmeyen_tablo_varliktir():
    """`hasta`nın hatası buradaydı: doğum tarihi var diye OLAY sanılıyordu.
    Bir varlığı olay sanmanın maliyeti ucuz değil — ona bir olay tarihi
    atanır ve bütün zaman filtreleri sessizce yanlış kolona düşer."""
    t = tablo("hasta", kol("hasta_id", "INTEGER"), kol("dogum_tarihi", "DATE"),
              kol("kayit_tarihi", "DATE"))
    il = [Iliski("randevu", "hasta_id", "hasta", "hasta_id")]
    assert tur_tahmini(t, il) is Tur.VARLIK


def test_tarihi_ve_disa_fki_olan_tablo_olaydir():
    t = tablo("fatura", kol("fatura_id", "INTEGER"), kol("muayene_id", "INTEGER"),
              kol("tarih", "DATE"))
    assert tur_tahmini(t, [Iliski("fatura", "muayene_id", "muayene",
                                  "muayene_id")]) is Tur.OLAY


def test_iliskisiz_tarihsiz_tablo_varliktir():
    assert tur_tahmini(tablo("islem", kol("islem_id", "INTEGER"), kol("ad")), []) \
        is Tur.VARLIK


def test_olaya_isaret_eden_tablo_yayilimla_olay_olur():
    """`muayene`nin kendi tarihi yok ve tek FK'si var — yerel kural onu
    VARLIK sanıyor. Ama bir OLAY'a işaret ediyor."""
    tablolar = [tablo("randevu", kol("randevu_id", "INTEGER"),
                      kol("hasta_id", "INTEGER"), kol("tarih", "DATE")),
                tablo("hasta", kol("hasta_id", "INTEGER")),
                tablo("muayene", kol("muayene_id", "INTEGER"),
                      kol("randevu_id", "INTEGER"))]
    il = [Iliski("randevu", "hasta_id", "hasta", "hasta_id"),
          Iliski("muayene", "randevu_id", "randevu", "randevu_id")]
    assert tur_tahmini(tablolar[2], il) is Tur.VARLIK        # yerel kural kaçırır
    assert turleri_tahmin_et(tablolar, il)["muayene"] is Tur.OLAY


def test_yayilim_varliga_dokunmaz():
    """Yayılım tek yönlü: bir VARLIK'a işaret etmek olay yapmaz."""
    tablolar = [tablo("doktor", kol("doktor_id", "INTEGER"), kol("bolum_id", "INTEGER")),
                tablo("bolum", kol("bolum_id", "INTEGER"), kol("ad"))]
    il = [Iliski("doktor", "bolum_id", "bolum", "bolum_id")]
    assert turleri_tahmin_et(tablolar, il)["bolum"] is Tur.VARLIK


def test_yayilim_donguda_takilmaz():
    """Kendine dönen FK'ler gerçek şemalarda var (`calisan.yonetici_id`).
    Yayılım tek yönlü olduğu için sabit noktaya ulaşır; bu test sonsuz
    döngüyü zaman aşımıyla değil, dönerek kanıtlar."""
    tablolar = [tablo("a", kol("a_id", "INTEGER"), kol("b_id", "INTEGER"),
                      kol("tarih", "DATE")),
                tablo("b", kol("b_id", "INTEGER"), kol("a_id", "INTEGER"))]
    il = [Iliski("a", "b_id", "b", "b_id"), Iliski("b", "a_id", "a", "a_id")]
    assert turleri_tahmin_et(tablolar, il) == {"a": Tur.OLAY, "b": Tur.OLAY}


# --------------------------------------------------------------------------- #
#  Kardinalite — ölçüm yorumu
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("kaynak,hedef,beklenen", [
    (True, True, Kardinalite.BIR_BIR),
    (False, True, Kardinalite.COK_BIR),
    (True, False, Kardinalite.COK_COK),
    (False, False, Kardinalite.COK_COK),
])
def test_kardinalite_dogruluk_tablosu(kaynak, hedef, beklenen):
    assert kardinalite_belirle(kaynak, hedef) is beklenen


def test_hedef_benzersiz_degilse_iki_yon_de_cogaltir():
    k = kardinalite_belirle(kaynak_benzersiz=True, hedef_benzersiz=False)
    assert not k.ileri_guvenli and not k.geri_guvenli


def test_olculmeyen_iliski_olculmedi_kalir():
    """`OLCULMEDI` bir varsayılan değil, bir itiraftır: ölçmeden birleştirme
    yapılamaz, çünkü çoğaltıp çoğaltmadığı bilinmiyor."""
    o = oner("x", [tablo("a", kol("a_id", "INTEGER"), kol("b_id", "INTEGER")),
                   tablo("b", kol("b_id", "INTEGER"))],
             [Iliski("a", "b_id", "b", "b_id")])
    (i,) = o.model.tablolar["a"].iliskiler
    assert i.kardinalite is Kardinalite.OLCULMEDI
    assert any("kardinalite" in q for q in acik_sorular(o)["a"])


def test_olculmus_iliski_modele_gecer():
    olcum = OlcumGirdisi(benzersiz={("a", "b_id"): False, ("b", "b_id"): True},
                         farkli_sayisi={})
    o = oner("x", [tablo("a", kol("a_id", "INTEGER"), kol("b_id", "INTEGER")),
                   tablo("b", kol("b_id", "INTEGER"))],
             [Iliski("a", "b_id", "b", "b_id")], olcum)
    (i,) = o.model.tablolar["a"].iliskiler
    assert i.kardinalite is Kardinalite.COK_BIR
    assert not any("kardinalite" in q for q in acik_sorular(o)["a"])


def test_semada_olmayan_tabloya_giden_iliski_dusurulur():
    """Şema kaynağı silinmiş bir tabloya FK verebilir. Modele girerse
    `dogrula()` sonsuza dek şikâyet eder ve sihirbaz kilitlenir."""
    o = oner("x", [tablo("a", kol("a_id", "INTEGER"), kol("z_id", "INTEGER"))],
             [Iliski("a", "z_id", "yok_boyle_tablo", "z_id")])
    assert o.model.tablolar["a"].iliskiler == ()


# --------------------------------------------------------------------------- #
#  Ölçü ve boyut üretimi
# --------------------------------------------------------------------------- #

def test_anahtarli_tabloya_benzersiz_sayim_olcusu():
    o = oner("x", [tablo("randevu", kol("randevu_id", "INTEGER"), kol("tarih", "DATE"))], [])
    m = o.model.olculer["randevu_sayisi"]
    assert m.toplama is Toplama.BENZERSIZ_SAYIM and m.ifade == "randevu.randevu_id"


def test_anahtarsiz_olay_tablosu_duz_sayimla_olculur():
    o = oner("x", [tablo("log", kol("olay_id", "INTEGER"), kol("tarih", "DATE"),
                         kol("kullanici_id", "INTEGER")),
                   tablo("kullanici", kol("kullanici_id", "INTEGER"))],
             [Iliski("log", "kullanici_id", "kullanici", "kullanici_id")])
    assert o.model.olculer["log_sayisi"].toplama is Toplama.SAYIM


def test_anahtar_kolonlari_olcu_olmaz():
    o = oner("x", [tablo("satis", kol("satis_id", "INTEGER"),
                         kol("musteri_no", "INTEGER"), kol("tutar", "REAL"))], [])
    assert "toplam_satis_id" not in o.model.olculer
    assert "toplam_musteri_no" not in o.model.olculer
    assert "toplam_tutar" in o.model.olculer


def test_ayni_adli_olcu_ezilmez():
    """İki tabloda da `tutar` var. İlk sürümde ikincisi birincinin ÜSTÜNE
    yazıyordu: adı doğru, tablosu yanlış bir ölçü — sessiz ve ölümcül."""
    o = oner("x", [tablo("fatura", kol("fatura_id", "INTEGER"), kol("tutar", "REAL")),
                   tablo("odeme", kol("odeme_id", "INTEGER"), kol("tutar", "REAL"))], [])
    tablolari = {m.tablo for ad, m in o.model.olculer.items() if "tutar" in ad}
    assert tablolari == {"fatura", "odeme"}


def test_anahtar_kolonlari_boyut_olmaz():
    """İlk sürümde 32 boyutun yarısı `hasta_id`, `randevu_id` gibi
    anahtarlardı. Kimse `hasta_id`'ye göre gruplamaz."""
    o = oner("x", [tablo("randevu", kol("randevu_id", "INTEGER"),
                         kol("hasta_id", "INTEGER"), kol("durum"))], [])
    kolonlar = {b.kolon for b in o.model.boyutlar.values()}
    assert kolonlar == {"durum"}


def test_serbest_metin_boyut_olmaz():
    o = oner("x", [tablo("muayene", kol("muayene_id", "INTEGER"), kol("notlar"),
                         kol("tani"))], [])
    kolonlar = {b.kolon for b in o.model.boyutlar.values()}
    assert "notlar" not in kolonlar and "tani" in kolonlar


def test_olculmus_yuksek_kardinalite_boyut_olmaz():
    """Ölçüm varsa ona uyulur: 5000 farklı değer bir boyut değil, bir
    listedir. Ölçüm YOKSA kolon içeride kalır — bilmemek, atmak için
    gerekçe değil."""
    t = tablo("hasta", kol("hasta_id", "INTEGER"), kol("sehir"), kol("cinsiyet"))
    olcum = OlcumGirdisi(benzersiz={},
                         farkli_sayisi={("hasta", "sehir"): 5000,
                                        ("hasta", "cinsiyet"): 2})
    kolonlar = {b.kolon for b in oner("x", [t], [], olcum).model.boyutlar.values()}
    assert kolonlar == {"cinsiyet"}
    olcumsuz = {b.kolon for b in oner("x", [t], []).model.boyutlar.values()}
    assert olcumsuz == {"sehir", "cinsiyet"}


def test_tarih_boyutlari_nitelenir():
    """`tarih` adı şemada tekrar eder; çıplak hâli eşleyiciye hangi tablonun
    tarihi olduğunu söylemez."""
    o = oner("x", [tablo("fatura", kol("fatura_id", "INTEGER"), kol("tarih", "DATE")),
                   tablo("randevu", kol("randevu_id", "INTEGER"), kol("tarih", "DATE"))], [])
    assert {"fatura_tarih", "randevu_tarih"} <= set(o.model.boyutlar)
    assert "tarih" not in o.model.boyutlar


def test_genel_kolon_adlari_nitelenir():
    o = oner("x", [tablo("bolum", kol("bolum_id", "INTEGER"), kol("ad")),
                   tablo("islem", kol("islem_id", "INTEGER"), kol("ad"))], [])
    assert {"bolum_ad", "islem_ad"} <= set(o.model.boyutlar)


# --------------------------------------------------------------------------- #
#  Sihirbazın soru kümesi doğrulamayı KAPSAR
# --------------------------------------------------------------------------- #

def _gercek_sema() -> tuple[list[TabloSemasi], list[Iliski]]:
    c = sqlite3.connect(f"file:{DEMO}?mode=ro", uri=True)
    try:
        tablolar, iliskiler = [], []
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                              "ORDER BY name"):
            tablolar.append(TabloSemasi(
                t, tuple(KolonSemasi(r[1], r[2]) for r in c.execute(f"PRAGMA table_info({t})"))))
            iliskiler += [Iliski(t, r[3], r[2], r[4])
                          for r in c.execute(f"PRAGMA foreign_key_list({t})")]
        return tablolar, iliskiler
    finally:
        c.close()


def test_her_dogrulama_sikayetinin_bir_sorusu_var():
    """Boşluk testi: `dogrula()` bir tablo için şikâyet ediyorsa,
    `acik_sorular()` o tablo için soru üretmek ZORUNDA. Aksi hâlde sihirbaz
    kullanıcıyı asla geçemeyeceği bir kapıya götürür."""
    tablolar, iliskiler = _gercek_sema()
    o = oner("hbys", tablolar, iliskiler)
    sorular = acik_sorular(o)
    for sorun in o.model.dogrula():
        if sorun.startswith("'"):
            tablo_adi = sorun.split("'", 2)[1]
            if tablo_adi in o.model.tablolar:
                assert sorular.get(tablo_adi), f"soru üretilmedi: {sorun}"


def test_sorular_cevaplaninca_model_gecerli_olur():
    """Yeterlilik testi — kapsama testinin tersi.

    Sihirbazı taklit eder: her soruya makul bir cevap verir ve modelin
    GERÇEKTEN geçerli hâle geldiğini gösterir. Bu geçmezse öneri, insanın
    kapatamayacağı bir açık bırakıyor demektir.
    """
    tablolar, iliskiler = _gercek_sema()
    o = oner("hbys", tablolar, iliskiler)
    m = o.model

    yeni_tablolar = {}
    for ad, t in m.tablolar.items():
        # "Ne zaman oldu?" — kendi tarihi varsa onu, yoksa 1:1 bağlı
        # komşudan miras (sihirbazın gerçekten sunduğu seçenek).
        tarih = None
        if t.olay_mi:
            adaylar = o.tarih_adaylari.get(ad, ())
            tarih = adaylar[0] if adaylar else next(
                (f"{i.hedef}.{h}" for i in t.iliskiler
                 if (h := (o.tarih_adaylari.get(i.hedef) or (None,))[0])), None)
            assert tarih, f"'{ad}' için hiçbir tarih seçeneği sunulmadı"
        yeni_tablolar[ad] = replace(
            t, olay_tarihi=tarih, gecerlilik_karari=Karar.YOK,
            iliskiler=tuple(replace(i, kardinalite=Kardinalite.COK_BIR)
                            for i in t.iliskiler))
    yeni_boyutlar = {ad: replace(b, sozluk_karari=Karar.YOK)
                     for ad, b in m.boyutlar.items()}
    onaylanmis = replace(m, tablolar=yeni_tablolar, boyutlar=yeni_boyutlar,
                         onaylayan="ihsan")
    assert onaylanmis.dogrula() == []


def test_gercek_semada_hicbir_varlik_olay_tarihi_almaz():
    """Bu üç iddia, ilk taslağın gerçek şemada ürettiği üç sessiz yanlıştır."""
    tablolar, iliskiler = _gercek_sema()
    o = oner("hbys", tablolar, iliskiler)
    turler = {ad: t.tur for ad, t in o.model.tablolar.items()}
    assert turler["hasta"] is Tur.VARLIK          # doğum tarihi olay değildir
    assert turler["bolum"] is Tur.VARLIK
    assert turler["muayene"] is Tur.OLAY          # yayılımla yakalanır
    assert "bolum_ad" in o.model.boyutlar         # etiketler maskelenmez
    assert "islem_ad" in o.model.boyutlar
    anahtar_boyut = [b.ad for b in o.model.boyutlar.values() if b.kolon.endswith("_id")]
    assert anahtar_boyut == []


# --------------------------------------------------------------------------- #
#  Determinizm ve saflık
# --------------------------------------------------------------------------- #

def test_ayni_sema_ayni_oneri():
    t = [tablo("a", kol("a_id", "INTEGER"), kol("tarih", "DATE"), kol("durum")),
         tablo("b", kol("b_id", "INTEGER"), kol("ad"))]
    ilk = oner("x", t, []).model.to_dict()
    assert all(oner("x", t, []).model.to_dict() == ilk for _ in range(5))


def test_on_doldurma_veritabani_gormez():
    """A-2 saf: girdisi şema nesneleri, çıktısı bir öneri. Ölçümü
    `SemaKaynagi` yapar. Bu ayrım olmadan ön-doldurma mantığı ancak canlı
    bir veritabanıyla test edilebilirdi."""
    agac = ast.parse(pathlib.Path(od.__file__).read_text(encoding="utf-8"))
    ithal = {a.name.split(".")[0] for d in ast.walk(agac)
             if isinstance(d, ast.Import) for a in d.names}
    ithal |= {(d.module or "").split(".")[0] for d in ast.walk(agac)
              if isinstance(d, ast.ImportFrom)}
    assert ithal <= {"__future__", "re", "dataclasses", "app"}


def test_oneri_degismez():
    o = oner("x", [tablo("a", kol("a_id", "INTEGER"), kol("tarih", "DATE"))], [])
    assert isinstance(o, Oneri)
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.model = None                       # type: ignore[misc]


def test_tarihsiz_olay_tablosu_komsudan_aday_alir():
    """`muayene_islem`in tarihi yok, komşusu `muayene`nin de yok — olay
    zamanı iki sıçrama ötede. Yalnız kendi kolonlarına bakan bir öneri
    burada boş liste verip kullanıcıyı geçemeyeceği bir kapıda bırakıyordu.
    """
    tablolar = [tablo("randevu", kol("randevu_id", "INTEGER"), kol("tarih", "DATE"),
                      kol("hasta_id", "INTEGER")),
                tablo("hasta", kol("hasta_id", "INTEGER")),
                tablo("muayene", kol("muayene_id", "INTEGER"),
                      kol("randevu_id", "INTEGER")),
                tablo("muayene_islem", kol("muayene_id", "INTEGER"),
                      kol("islem_id", "INTEGER"), kol("adet", "INTEGER")),
                tablo("islem", kol("islem_id", "INTEGER"), kol("ad"))]
    il = [Iliski("randevu", "hasta_id", "hasta", "hasta_id"),
          Iliski("muayene", "randevu_id", "randevu", "randevu_id"),
          Iliski("muayene_islem", "muayene_id", "muayene", "muayene_id"),
          Iliski("muayene_islem", "islem_id", "islem", "islem_id")]
    o = oner("x", tablolar, il)
    assert o.tarih_adaylari["muayene"] == ("randevu.tarih",)
    assert o.tarih_adaylari["muayene_islem"] == ("randevu.tarih",)
    assert "randevu.tarih" in " ".join(acik_sorular(o)["muayene_islem"])


def test_kendi_tarihi_varsa_miras_aranmaz():
    """En yakın cevap kendi kolonudur; komşuya bakmak onu gölgelerdi."""
    o = oner("x", [tablo("fatura", kol("fatura_id", "INTEGER"),
                         kol("muayene_id", "INTEGER"), kol("tarih", "DATE")),
                   tablo("muayene", kol("muayene_id", "INTEGER"),
                         kol("islem_tarihi", "DATE"))],
             [Iliski("fatura", "muayene_id", "muayene", "muayene_id")])
    assert o.tarih_adaylari["fatura"] == ("tarih",)


def test_maskeli_tarih_aday_olamaz():
    """`dogum_tarihi` bir tarihtir ama bir olay tarihi değildir — üstelik
    maskelidir. Miras yoluyla bile aday listesine giremez."""
    o = oner("x", [tablo("hasta", kol("hasta_id", "INTEGER"), kol("tckn"),
                         kol("dogum_tarihi", "DATE")),
                   tablo("randevu", kol("randevu_id", "INTEGER"),
                         kol("hasta_id", "INTEGER"))],
             [Iliski("randevu", "hasta_id", "hasta", "hasta_id")])
    assert "hasta.dogum_tarihi" not in o.tarih_adaylari.get("randevu", ())
