"""Çekirdek değer tipleri — anlam katmanının ortak sözlüğü.

Bu modül ve `app/cekirdek/` altındaki her modül **saftır**: stdlib ve `sqlglot`
dışında hiçbir şey import etmez. Kural bir temenni değil, bir testtir:
`tests/cekirdek/test_cekirdek_saf.py`.

Buradaki tiplerin tamamı `frozen=True`. Bu bir stil tercihi değil: bir anlam
modeli sürümü bir DEĞERDİR (ADR-9). Sürümleme ancak değişmezlikle güvenilir
olur — elde tutulan bir modelin altından değiştirilebiliyorsa, damgadaki sürüm
numarası neyi işaret ettiğini söyleyemez.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tur(str, Enum):
    """Bir tablonun anlam modelindeki rolü."""

    OLAY = "olay"        # bir şey oldu: randevu, satış, ölçüm
    VARLIK = "varlik"    # bir şey var: hasta, ürün, doktor


class Toplama(str, Enum):
    """Bir ölçünün toplama kuralı."""

    SAYIM = "sayim"
    BENZERSIZ_SAYIM = "benzersiz_sayim"
    TOPLAM = "toplam"
    ORTALAMA = "ortalama"
    EN_AZ = "en_az"
    EN_COK = "en_cok"

    @property
    def yeniden_toplanabilir(self) -> bool:
        """Bu toplamanın sonucu bir kez daha toplanabilir mi?

        Sayım ve toplam toplanabilir: parçaların toplamı bütünün toplamıdır.
        Ortalama TOPLANMAZ — ortalamaların ortalaması bütünün ortalaması
        değildir ve aradaki fark, sorulan soruya göre yüzdelerce olabilir.

        Bu, insanların elle SQL yazarken de sık yaptığı bir hatadır ve tam
        olarak sessiz yanlış sınıfına girer: sorgu çalışır, tablo döner,
        sayı yanlıştır. Derleyici (İP-47) bunu bir kural olarak uygular;
        buradaki bayrak o kuralın veri tarafıdır.
        """
        return self in (Toplama.SAYIM, Toplama.BENZERSIZ_SAYIM, Toplama.TOPLAM)


class ZamanTanesi(str, Enum):
    GUN = "gun"
    HAFTA = "hafta"
    AY = "ay"
    CEYREK = "ceyrek"
    YIL = "yil"


class Karar(str, Enum):
    """Sihirbazda bir sorunun durumu.

    Bu enum'ın tek varlık sebebi şu ayrım: **cevaplanmadı ile cevabı yok aynı
    şey değildir.**

    `gecerlilik = None` tek başına iki farklı anlama gelebilirdi — "bu tabloda
    iptal kaydı yok" ya da "kimse sormadı". İkincisi eksen 8'in sessiz
    yanlışıdır: model, iptal edilmiş randevuları da sayar ve kimse bunu fark
    etmez. Bu yüzden "sorulmadı" hâli modeli GEÇERSİZ yapar; "sorduk, cevabı
    yok" hâli geçerlidir.

    Aynı ayrım üç yerde kullanılır: geçerlilik filtresi, değer sözlüğü ve
    (dolaylı olarak) olay tarihi. Belirsizlik ile yokluk ayrı kodlanır.
    """

    SORULMADI = "sorulmadi"
    VAR = "var"
    YOK = "yok"


class Kardinalite(str, Enum):
    """Bir ilişkinin `kaynak -> hedef` yönündeki çokluğu.

    Neden modelde duruyor: birleştirme yönü, bir ölçünün ÇOĞALIP çoğalmayacağını
    belirler ve bu, sessiz yanlışın en pahalı türüdür. Ölçüldü (2026-08-30,
    demo/hospital.db): `fatura` ile `muayene_islem` birleştirildiğinde toplam
    ciro 14.574.050 -> 34.222.000, yani **2,35 kat** şişiyor. Sorgu çalışır,
    tablo döner, sayı yanlıştır.

    `OLCULMEDI` modeli GEÇERSİZ yapar. Ölçülmedi ile çoğaltmaz aynı şey
    değildir — `Karar` enum'ındaki ayrımın birleştirme tarafındaki karşılığı.
    """

    BIR_BIR = "1:1"        # her iki yön de güvenli (randevu <-> muayene)
    COK_BIR = "n:1"        # kaynak->hedef güvenli, ters yön çoğaltır (randevu -> doktor)
    COK_COK = "n:n"        # iki yön de çoğaltır — birleştirme reddedilir
    OLCULMEDI = "olculmedi"

    @property
    def ileri_guvenli(self) -> bool:
        """kaynak -> hedef yönünde birleştirme ölçüyü çoğaltır mı?"""
        return self in (Kardinalite.BIR_BIR, Kardinalite.COK_BIR)

    @property
    def geri_guvenli(self) -> bool:
        """hedef -> kaynak yönünde? Yalnız 1:1'de güvenli."""
        return self is Kardinalite.BIR_BIR


class IliskiGuveni(str, Enum):
    """Bir ilişkinin nereden geldiği.

    KESIN: veritabanının kendi yabancı anahtarı.
    DUSUK: ad benzerliğinden türetildi (FK tanımlamayan eski şemalar).
           Sihirbaz bunu insana AYRI gösterir — onaylanmadan kullanılmaz.
    """

    KESIN = "kesin"
    DUSUK = "dusuk"


@dataclass(frozen=True)
class KolonSemasi:
    """Ham şemadan okunan bir kolon. Anlam taşımaz, yalnız yapı."""

    ad: str
    tip: str = ""
    bos_gecebilir: bool = True


@dataclass(frozen=True)
class TabloSemasi:
    """Ham şemadan okunan bir tablo. `SemaKaynagi` portunun çıktısı."""

    ad: str
    kolonlar: tuple[KolonSemasi, ...] = ()
    birincil_anahtar: tuple[str, ...] = ()

    def kolon_adlari(self) -> frozenset[str]:
        return frozenset(k.ad for k in self.kolonlar)


@dataclass(frozen=True)
class Iliski:
    """İki tablo arasında bir birleştirme yolu."""

    kaynak: str
    kaynak_kolon: str
    hedef: str
    hedef_kolon: str
    guven: IliskiGuveni = IliskiGuveni.KESIN
    kardinalite: Kardinalite = Kardinalite.OLCULMEDI


@dataclass(frozen=True)
class Filtre:
    """Bir seçimdeki filtre. Boyut ADIYLA gösterilir, kolonla değil.

    Sebep: filtrenin hangi kolona ineceği anlam modelinin işidir. Model
    (LLM) kolon adı söyleyemez — söylerse eksen 1 ve 4 geri gelir.
    """

    boyut: str
    islec: str                       # esittir | icinde | araliginda | buyuk | kucuk
    degerler: tuple[str, ...] = ()


@dataclass(frozen=True)
class Zaman:
    """Bir seçimin zaman kısıtı.

    `ifade` kullanıcının söylediği hâlidir ("bu yıl") ve panoya VARSAYIM olarak
    yazılır (SPEC C-3). Çözülen sınırlar `baslangic`/`bitis`'te durur.
    """

    tane: ZamanTanesi
    baslangic: str | None = None     # ISO-8601 tarih
    bitis: str | None = None
    ifade: str = ""


@dataclass(frozen=True)
class Sonuc:
    """Bir sorgunun çalıştırılmış hâli. `Yurutucu` portunun çıktısı.

    Bu nesne Sınır 2'nin (SPEC E-2) taşıdığı tek veri kabıdır: satırlar
    yalnız burada ve yalnız bellek içi önbellekte yaşar. Denetim izine
    `satir_sayisi` gider, `satirlar` gitmez.
    """

    durum: str                       # BASARILI | ZAMAN_ASIMI | CALISMA_HATASI
    kolonlar: tuple[str, ...] = ()
    satirlar: tuple[tuple, ...] = ()
    satir_sayisi: int = 0
    sure_sn: float = 0.0
    hata: str = ""

    @property
    def basarili(self) -> bool:
        return self.durum == "BASARILI"
