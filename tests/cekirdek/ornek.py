"""Örnek anlam modeli — çekirdek testlerinin ortak sapma noktası.

Şekli `demo/hospital.db`'den alınmıştır ve ORADAKİ kardinaliteleri taşır
(2026-08-30'da ölçüldü). Özellikle iki durum kasten içeride:

* `randevu -> muayene -> fatura` gerçek bir **1:1 zincir** — birleştirme
  çoğaltmaz, yasaklanmamalı.
* `muayene -> muayene_islem` **1:N** — bir muayenede birden çok işlem var.
  Ciroyu bu yoldan kırmak toplamı 2,35 katına çıkarır; derleyici reddetmeli.

Geçerli bir modeldir; testler ondan tek bir alanı bozarak her sessiz yanlış
sınıfını ayrı ayrı sınar.
"""
from __future__ import annotations

from app.cekirdek.anlam import AnlamModeli, Boyut, Olcu, TabloAnlami
from app.cekirdek.tipler import Iliski, Karar, Kardinalite, Toplama, Tur

N1 = Kardinalite.COK_BIR
BB = Kardinalite.BIR_BIR


def gecerli_model() -> AnlamModeli:
    tablolar = {
        "randevu": TabloAnlami(
            ad="randevu", tur=Tur.OLAY, tane="bir satır = bir randevu",
            kolonlar=("randevu_id", "hasta_id", "doktor_id", "tarih", "saat", "durum"),
            olay_tarihi="tarih",
            gecerlilik_karari=Karar.VAR, gecerlilik="randevu.durum <> 'IPTAL'",
            iliskiler=(
                Iliski("randevu", "doktor_id", "doktor", "doktor_id", kardinalite=N1),
                Iliski("randevu", "hasta_id", "hasta", "hasta_id", kardinalite=N1),
            ),
        ),
        "muayene": TabloAnlami(
            ad="muayene", tur=Tur.OLAY, tane="bir satır = bir muayene",
            kolonlar=("muayene_id", "randevu_id", "tani", "notlar"),
            # Kendi tarihi YOK — zamanı 1:1 bağlı randevudan miras alır.
            olay_tarihi="randevu.tarih", gecerlilik_karari=Karar.YOK,
            iliskiler=(
                # 1:1 — her randevunun en çok bir muayenesi var (ölçüldü)
                Iliski("muayene", "randevu_id", "randevu", "randevu_id", kardinalite=BB),
            ),
        ),
        "fatura": TabloAnlami(
            ad="fatura", tur=Tur.OLAY, tane="bir satır = bir fatura",
            kolonlar=("fatura_id", "muayene_id", "tutar", "odeme_durumu", "tarih"),
            olay_tarihi="tarih", gecerlilik_karari=Karar.YOK,
            iliskiler=(
                Iliski("fatura", "muayene_id", "muayene", "muayene_id", kardinalite=BB),
            ),
        ),
        "muayene_islem": TabloAnlami(
            ad="muayene_islem", tur=Tur.OLAY,
            tane="bir satır = bir muayenede uygulanan bir işlem",
            kolonlar=("muayene_id", "islem_id", "adet"),
            olay_tarihi="randevu.tarih", gecerlilik_karari=Karar.YOK,
            iliskiler=(
                # n:1 — muayeneye doğru güvenli, TERSİ çoğaltır
                Iliski("muayene_islem", "muayene_id", "muayene", "muayene_id",
                       kardinalite=N1),
                Iliski("muayene_islem", "islem_id", "islem", "islem_id", kardinalite=N1),
            ),
        ),
        "doktor": TabloAnlami(
            ad="doktor", tur=Tur.VARLIK, tane="bir satır = bir doktor",
            kolonlar=("doktor_id", "ad", "soyad", "unvan", "bolum_id", "ise_baslama"),
            gecerlilik_karari=Karar.YOK,
            iliskiler=(
                Iliski("doktor", "bolum_id", "bolum", "bolum_id", kardinalite=N1),
            ),
        ),
        "bolum": TabloAnlami(
            ad="bolum", tur=Tur.VARLIK, tane="bir satır = bir bölüm",
            kolonlar=("bolum_id", "ad", "kat"), gecerlilik_karari=Karar.YOK,
        ),
        "hasta": TabloAnlami(
            ad="hasta", tur=Tur.VARLIK, tane="bir satır = bir hasta",
            kolonlar=("hasta_id", "ad", "soyad", "tckn", "dogum_tarihi",
                      "cinsiyet", "sehir", "kayit_tarihi"),
            gecerlilik_karari=Karar.YOK,
        ),
        "islem": TabloAnlami(
            ad="islem", tur=Tur.VARLIK, tane="bir satır = bir işlem türü",
            kolonlar=("islem_id", "ad", "ucret"), gecerlilik_karari=Karar.YOK,
        ),
    }

    olculer = {
        "randevu_sayisi": Olcu(
            ad="randevu_sayisi", tablo="randevu", ifade="randevu.randevu_id",
            toplama=Toplama.BENZERSIZ_SAYIM, birim="adet",
            gosterim="Randevu sayısı"),
        "ciro": Olcu(
            ad="ciro", tablo="fatura", ifade="fatura.tutar",
            toplama=Toplama.TOPLAM, birim="TL", gosterim="Ciro"),
        "ortalama_fatura": Olcu(
            ad="ortalama_fatura", tablo="fatura", ifade="fatura.tutar",
            toplama=Toplama.ORTALAMA, birim="TL", gosterim="Ortalama fatura",
            uyari="ortalamanın ortalaması alınamaz"),
        "odenmemis_ciro": Olcu(
            ad="odenmemis_ciro", tablo="fatura", ifade="fatura.tutar",
            toplama=Toplama.TOPLAM, birim="TL", gosterim="Ödenmemiş ciro",
            kaynak_kosulu="fatura.odeme_durumu <> 'ODENDI'"),
        "islem_sayisi": Olcu(
            ad="islem_sayisi", tablo="muayene_islem", ifade="muayene_islem.adet",
            toplama=Toplama.TOPLAM, birim="adet", gosterim="İşlem sayısı"),
    }

    boyutlar = {
        "unvan": Boyut(ad="unvan", tablo="doktor", kolon="unvan",
                       gosterim="Doktor unvanı", sozluk_karari=Karar.VAR,
                       sozluk={"Prof. Dr.": "Prof. Dr.", "Doç. Dr.": "Doç. Dr.",
                               "Uzm. Dr.": "Uzm. Dr.", "Dr.": "Dr."}),
        "bolum": Boyut(ad="bolum", tablo="bolum", kolon="ad", gosterim="Bölüm",
                       sozluk_karari=Karar.VAR,
                       sozluk={"Kardiyoloji": "Kardiyoloji", "Dahiliye": "Dahiliye"}),
        "cinsiyet": Boyut(ad="cinsiyet", tablo="hasta", kolon="cinsiyet",
                          gosterim="Cinsiyet", sozluk_karari=Karar.VAR,
                          sozluk={"E": "Erkek", "K": "Kadın"}),
        "sehir": Boyut(ad="sehir", tablo="hasta", kolon="sehir", gosterim="Şehir",
                       sozluk_karari=Karar.YOK),
        "islem_adi": Boyut(ad="islem_adi", tablo="islem", kolon="ad",
                           gosterim="İşlem", sozluk_karari=Karar.YOK),
        "odeme_durumu": Boyut(ad="odeme_durumu", tablo="fatura",
                              kolon="odeme_durumu", gosterim="Ödeme durumu",
                              sozluk_karari=Karar.VAR,
                              sozluk={"ODENDI": "Ödendi", "BEKLIYOR": "Bekliyor",
                                      "GECIKTI": "Gecikti"}),
        "randevu_tarihi": Boyut(ad="randevu_tarihi", tablo="randevu", kolon="tarih",
                                gosterim="Randevu tarihi", sozluk_karari=Karar.YOK,
                                tarih_mi=True),
        "fatura_tarihi": Boyut(ad="fatura_tarihi", tablo="fatura", kolon="tarih",
                               gosterim="Fatura tarihi", sozluk_karari=Karar.YOK,
                               tarih_mi=True),
    }

    return AnlamModeli(
        baglanti="hbys-demo", surum=3, onaylayan="ihsan",
        tablolar=tablolar, olculer=olculer, boyutlar=boyutlar,
        maskeli=frozenset({"hasta.tckn", "hasta.ad", "hasta.soyad"}),
    )
