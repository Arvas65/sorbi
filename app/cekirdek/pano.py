"""Pano derleyici (SPEC D-1) — grafik tipini model seçmez, seçimin şekli seçer.

Bu, ADR-8'in bir kat yukarısı. ADR-8 modelden SQL yazma işini aldı; bu modül
ondan grafik seçme işini de alıyor. Gerekçe aynı: **stokastik parçayı küçült,
etrafını deterministik yap.**

Somut kazanç: bir LLM "bunu pasta grafik yap" derse ve yanılırsa, bunu
yakalayacak hiçbir test yazılamaz — çıktı öznel görünür. Oysa "bir tarih
boyutu + bir ölçü çizgi grafiğidir" bir kuraldır; kuralın testi yazılır ve
CI'da saniyeler içinde koşar.

Şekil bilgisi SONUCUN KENDİSİNDEN değil, `Secim`den gelir: hangi ölçüler,
hangi boyutlar, boyutların hangisi tarih. Bu bilgi zaten beyan edilmiştir —
sonuç tablosunun kolon tiplerinden geri türetmek (v3'ün `guven.py`'sinin
yaptığı arkeoloji) gereksizdir ve yanılabilir. Sonuçtan alınan tek şey
**satır sayısıdır**.

SPEC'ten sapma (Build, 2026-08-29 — kayda geçirildi):
`claude/26` §04 tablosu ">200 satır -> tablo" diyordu. Uygulamada bu kural
yalnız KATEGORİK grafiklere uygulanıyor: üç yıllık günlük bir seri 1000
noktadır ve çizgi grafiği onu sorunsuz gösterir; tabloya düşürmek bilgi
kaybıdır. Kategorik tarafta ise sınır zaten "ilk 15 + diğer" ile kapanıyor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.cekirdek.anlam import AnlamModeli
from app.cekirdek.secim import Secim
from app.cekirdek.tipler import Sonuc

# Kategorik bir grafikte gösterilebilecek en çok kategori. Üstünde "ilk N +
# diğer" devreye girer: 60 çubuk okunmaz, okunmayan grafik yanlış okunur.
AZAMI_KATEGORI = 25
KIRPMA_SONRASI = 15
# Bir çoklu çizgide en çok seri. Üstünde küçük katlar (small multiples).
AZAMI_SERI = 5
# Seri sayısını bilmiyoruz — bilmek için VERİYE bakmak gerekirdi ve bu modül
# veriye bakmaz. Elimizdeki tek sayı satır sayısı: satır ≈ seri × zaman noktası.
# Bu yüzden eşik bir VEKİLDİR: 5 seri × ~60 zaman noktası. Vekil olduğu için
# uçlarda yanılabilir; yanıldığında bedeli "çoklu çizgi yerine küçük katlar"
# olur — okunabilirlik tercihi, yanlış bir sayı değil.
AZAMI_SATIR_COKLU_CIZGI = AZAMI_SERI * 60


class GrafikTipi(str, Enum):
    KPI = "kpi"
    CIZGI = "cizgi"
    COKLU_CIZGI = "coklu_cizgi"
    KUCUK_KATLAR = "kucuk_katlar"
    CUBUK = "cubuk"
    TABLO = "tablo"
    YOK = "yok"                    # gösterilecek bir şey yok; sebebi yazılır


@dataclass(frozen=True)
class PanoParcasi:
    """Panonun tek bir kartı."""

    tip: GrafikTipi
    baslik: str
    secim: Secim
    x: str | None = None           # boyut adı
    y: str | None = None           # ölçü adı
    seri: str | None = None        # çoklu çizgi/katlarda ayıran boyut
    kirpildi: bool = False         # "ilk 15 + diğer" uygulandı mı
    satir_sayisi: int = 0
    notlar: tuple[str, ...] = ()   # kullanıcıya gösterilir, gizlenmez
    bayraklar: tuple[str, ...] = ()  # güven katmanından (D-4)


@dataclass(frozen=True)
class PanoPlani:
    """Bir iş sorusunun panosu. Geçici — önbellekte yaşar, diske yazılmaz."""

    soru: str
    parcalar: tuple[PanoParcasi, ...] = ()
    varsayimlar: tuple[str, ...] = ()
    kapsam_disi: tuple[str, ...] = ()   # maskeli kolon vb. (E-5)
    eksikler: tuple[str, ...] = field(default_factory=tuple)

    @property
    def bos(self) -> bool:
        return not any(p.tip is not GrafikTipi.YOK for p in self.parcalar)


# --------------------------------------------------------------------------- #
#  Kural: seçimin şekli -> grafik tipi
# --------------------------------------------------------------------------- #

def _sekil(secim: Secim, model: AnlamModeli) -> tuple[int, list[str], list[str]]:
    """(ölçü sayısı, tarih boyutları, kategori boyutları)"""
    tarihler, kategoriler = [], []
    for ad in secim.boyutlar:
        b = model.boyutlar.get(ad)
        (tarihler if (b is not None and b.tarih_mi) else kategoriler).append(ad)
    return len(secim.olculer), tarihler, kategoriler


def grafik_sec(secim: Secim, model: AnlamModeli, satir_sayisi: int) -> GrafikTipi:
    """Deterministik grafik seçimi. Aynı girdi her zaman aynı çıktıyı verir.

    Kurallar sırayla denenir; ilk eşleşen kazanır. Sıra keyfi değil, özelden
    genele: adı konmuş desenler önce, geri kalan tabloya düşer. "Emin
    değilsem tablo" bilinçli bir varsayılandır — yanlış bir grafik, tablodan
    daha kötüdür, çünkü yanlış bir hikâye anlatır ve düzeltilmesi zordur.
    """
    if not secim.kurulabilir:
        return GrafikTipi.YOK
    if satir_sayisi <= 0:
        return GrafikTipi.YOK

    olcu_sayisi, tarihler, kategoriler = _sekil(secim, model)
    if olcu_sayisi == 0:
        return GrafikTipi.YOK

    # 1) Boyutsuz tek sayı -> KPI kartı
    if not tarihler and not kategoriler and olcu_sayisi == 1 and satir_sayisi == 1:
        return GrafikTipi.KPI

    # 2) Zaman + tek ölçü -> çizgi
    if len(tarihler) == 1 and olcu_sayisi == 1 and not kategoriler:
        return GrafikTipi.CIZGI

    # 3) Zaman + bir kırılım + tek ölçü -> çoklu çizgi ya da küçük katlar
    if len(tarihler) == 1 and len(kategoriler) == 1 and olcu_sayisi == 1:
        return (GrafikTipi.COKLU_CIZGI if satir_sayisi <= AZAMI_SATIR_COKLU_CIZGI
                else GrafikTipi.KUCUK_KATLAR)

    # 4) Kategori + tek ölçü -> yatay çubuk (gerekirse kırpılır)
    if not tarihler and len(kategoriler) == 1 and olcu_sayisi == 1:
        return GrafikTipi.CUBUK

    # 5) Geri kalan her şey tablo. Zorlanmış grafik yok.
    return GrafikTipi.TABLO


# --------------------------------------------------------------------------- #
#  Parça ve plan
# --------------------------------------------------------------------------- #

def _baslik(secim: Secim, model: AnlamModeli) -> str:
    olcu = model.olculer.get(secim.olculer[0]) if secim.olculer else None
    ad = (olcu.gosterim or olcu.ad) if olcu else "Sonuç"
    if secim.boyutlar:
        b = model.boyutlar.get(secim.boyutlar[0])
        kirilim = (b.gosterim or b.ad) if b else secim.boyutlar[0]
        return f"{ad} — {kirilim}"
    return ad


def parca(secim: Secim, model: AnlamModeli, sonuc: Sonuc,
          bayraklar: tuple[str, ...] = ()) -> PanoParcasi:
    """Bir seçim + sonucundan tek bir pano kartı üretir."""
    notlar: list[str] = []

    if not secim.kurulabilir:
        return PanoParcasi(GrafikTipi.YOK, _baslik(secim, model) if secim.olculer
                           else "Kurulamayan seçim", secim,
                           notlar=tuple(secim.gecersiz), bayraklar=bayraklar)
    if not sonuc.basarili:
        # Değişmez #6: eksik parça sessizce boş kart olmaz, sebebi yazılır.
        return PanoParcasi(GrafikTipi.YOK, _baslik(secim, model), secim,
                           notlar=(sonuc.hata or f"Sorgu durumu: {sonuc.durum}",),
                           bayraklar=bayraklar)

    tip = grafik_sec(secim, model, sonuc.satir_sayisi)
    if tip is GrafikTipi.YOK and sonuc.satir_sayisi == 0:
        notlar.append("Bu soruya uyan kayıt bulunamadı. "
                      "Filtreleri ya da tarih aralığını gözden geçirin.")

    _, tarihler, kategoriler = _sekil(secim, model)
    x = (tarihler[0] if tarihler else (kategoriler[0] if kategoriler else None))
    seri = kategoriler[0] if (tarihler and kategoriler) else None
    y = secim.olculer[0] if secim.olculer else None

    kirpildi = False
    if tip is GrafikTipi.CUBUK and sonuc.satir_sayisi > AZAMI_KATEGORI:
        kirpildi = True
        notlar.append(f"{sonuc.satir_sayisi} kategori var; ilk {KIRPMA_SONRASI} "
                      "gösteriliyor, kalanı 'diğer' altında toplandı.")
    if tip is GrafikTipi.KUCUK_KATLAR:
        notlar.append("Seri sayısı çok; tek grafik yerine küçük katlar.")

    return PanoParcasi(tip=tip, baslik=_baslik(secim, model), secim=secim,
                       x=x, y=y, seri=seri, kirpildi=kirpildi,
                       satir_sayisi=sonuc.satir_sayisi,
                       notlar=tuple(notlar), bayraklar=bayraklar)


# Panodaki sıralama: önce tek sayılar, sonra zaman, sonra kırılım, sonra
# tablolar, en sonda gösterilemeyenler. Sıra da deterministiktir — aynı soru
# iki kez sorulduğunda kartlar yer değiştirmez.
_SIRA = {GrafikTipi.KPI: 0, GrafikTipi.CIZGI: 1, GrafikTipi.COKLU_CIZGI: 2,
         GrafikTipi.KUCUK_KATLAR: 3, GrafikTipi.CUBUK: 4,
         GrafikTipi.TABLO: 5, GrafikTipi.YOK: 6}


def plan(soru: str, parcalar: list[PanoParcasi],
         varsayimlar: tuple[str, ...] = (),
         kapsam_disi: tuple[str, ...] = ()) -> PanoPlani:
    """Kartları panoya dizer.

    Gösterilemeyen kartlar ATILMAZ — sona konur ve `eksikler` listesine
    sebepleriyle yazılır (SPEC D-3 / Değişmez #6). Sessizce eksilen bir
    pano, kullanıcıya eksik olduğunu söylemeyen bir panodur.
    """
    sirali = tuple(sorted(parcalar, key=lambda p: (_SIRA[p.tip], p.baslik)))
    eksikler = tuple(f"{p.baslik}: {p.notlar[0] if p.notlar else 'sebep yazılmadı'}"
                     for p in sirali if p.tip is GrafikTipi.YOK)
    return PanoPlani(soru=soru, parcalar=sirali, varsayimlar=varsayimlar,
                     kapsam_disi=kapsam_disi, eksikler=eksikler)


def varsayim_metni(secim: Secim) -> tuple[str, ...]:
    """Kullanıcıya gösterilecek varsayımlar (SPEC C-3).

    "Bu yıl" gibi bir ifadenin neye çözüldüğü gösterilmezse, kullanıcı sayının
    hangi aralığa ait olduğunu bilemez ve yanlış okur.
    """
    z = secim.zaman
    if z is None or not (z.baslangic or z.bitis):
        return ()
    etiket = z.ifade or "zaman aralığı"
    return (f"'{etiket}' = {z.baslangic or '…'} … {z.bitis or '…'} "
            f"({z.tane.value} bazında)",)
