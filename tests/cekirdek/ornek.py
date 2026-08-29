"""Örnek anlam modeli — çekirdek testlerinin ortak sapma noktası.

Hastane demo şemasının etiketlenmiş hâli. Geçerli bir modeldir; testler
ondan tek bir alanı bozarak her sessiz yanlış sınıfını ayrı ayrı sınar.
"""
from __future__ import annotations

from app.cekirdek.anlam import AnlamModeli, Boyut, Olcu, TabloAnlami
from app.cekirdek.tipler import Iliski, Karar, Toplama, Tur


def gecerli_model() -> AnlamModeli:
    randevu = TabloAnlami(
        ad="randevu", tur=Tur.OLAY,
        tane="bir satır = bir randevu",
        kolonlar=("randevu_id", "hasta_id", "doktor_id", "tarih", "iptal"),
        olay_tarihi="tarih",
        gecerlilik_karari=Karar.VAR, gecerlilik="randevu.iptal = 0",
        iliskiler=(Iliski("randevu", "doktor_id", "doktor", "doktor_id"),
                   Iliski("randevu", "hasta_id", "hasta", "hasta_id")),
    )
    doktor = TabloAnlami(
        ad="doktor", tur=Tur.VARLIK, tane="bir satır = bir doktor",
        kolonlar=("doktor_id", "ad", "unvan", "bolum_id"),
        gecerlilik_karari=Karar.YOK,
    )
    hasta = TabloAnlami(
        ad="hasta", tur=Tur.VARLIK, tane="bir satır = bir hasta",
        kolonlar=("hasta_id", "ad_soyad", "sehir", "cinsiyet", "tckn"),
        gecerlilik_karari=Karar.YOK,
    )
    return AnlamModeli(
        baglanti="hbys-demo", surum=3, onaylayan="ihsan",
        tablolar={"randevu": randevu, "doktor": doktor, "hasta": hasta},
        olculer={
            "randevu_sayisi": Olcu(
                ad="randevu_sayisi", tablo="randevu",
                ifade="COUNT(DISTINCT randevu.randevu_id)",
                toplama=Toplama.BENZERSIZ_SAYIM, birim="adet",
                gosterim="Randevu sayısı"),
        },
        boyutlar={
            "unvan": Boyut(ad="unvan", tablo="doktor", kolon="unvan",
                           gosterim="Doktor unvanı",
                           sozluk_karari=Karar.VAR,
                           sozluk={"Prof. Dr.": "Prof. Dr.", "Uzm. Dr.": "Uzm. Dr."}),
            "cinsiyet": Boyut(ad="cinsiyet", tablo="hasta", kolon="cinsiyet",
                              gosterim="Cinsiyet", sozluk_karari=Karar.VAR,
                              sozluk={"E": "Erkek", "K": "Kadın"}),
            "randevu_tarihi": Boyut(ad="randevu_tarihi", tablo="randevu",
                                    kolon="tarih", gosterim="Randevu tarihi",
                                    sozluk_karari=Karar.YOK, tarih_mi=True),
        },
        maskeli=frozenset({"hasta.tckn", "hasta.ad_soyad"}),
    )
