"""Anlam modelinin kalıcılığı (SPEC A-5, ADR-9) — `AnlamDeposu` portu.

Model müşterinin kendi makinesinde, depo içinde bir dosyada yaşar:

    anlam/<baglanti>.json              yürürlükteki sürüm
    anlam/gecmis/<baglanti>-v<N>.json  önceki sürümler, ekle-only

`.sorbi/` DEĞİL: orası sır dizini ve `.gitignore`'da (BULGU-15). Anlam modeli
sır değil, sürümlenmesi gereken bir varlıktır — gerekçe ADR-9 §2a.

İki tasarım kararı, gerekçeleriyle:

**1. Okuma kapalı devre, yazma yüksek sesli.**
`oku()` bozuk bir dosyada istisna fırlatmaz, `None` döner: dosyayı bir insan
elle düzenlemiş olabilir ve bu beklenen bir durumdur. `yaz()` ise geçersiz bir
modelde İSTİSNA FIRLATIR — çünkü oraya gelen model sihirbazın ürettiği bir
şeydir, güvenilmeyen bir girdi değil. Sessizce yazmamak, veri kaybıdır.
Sınırda kapalı devre, içeride yüksek ses: asimetri bilinçlidir.

**2. Yazma atomiktir.** Geçici dosyaya yazılır, sonra yerine taşınır. Yarıda
kesilmiş bir model dosyası ürünü kullanılamaz hâle getirir; kesilme anında
eski sürüm hâlâ yerinde durur.
"""
from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.cekirdek.anlam import AnlamModeli, yukle

VARSAYILAN_DIZIN = "anlam"
GECMIS_DIZIN = "gecmis"

# Bağlantı adı kullanıcıdan gelir ve dosya adına dönüşür. Yol kaçışına
# (`../../etc/passwd`) kapalı olmak zorunda: yalnız harf, rakam, tire, alt
# çizgi kalır. Testi var.
_GUVENLI = re.compile(r"[^A-Za-z0-9_-]+")


def slug(baglanti: str) -> str:
    ad = _GUVENLI.sub("-", (baglanti or "").strip()).strip("-").lower()
    return ad or "adsiz"


# --------------------------------------------------------------------------- #
#  Şema kayması
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SemaFarki:
    """Anlam modeli ile kaynak şema arasındaki fark (SPEC A-5).

    Sihirbaz bunu kullanarak **yalnız farkı** sorar. Tüm modeli baştan
    sormak, şemaya bir kolon eklendiği için kullanıcıyı yarım saatlik bir
    oturuma geri göndermek demek olurdu ve ürün kullanılmaz hâle gelirdi.
    """

    yeni_tablolar: tuple[str, ...] = ()
    kaybolan_tablolar: tuple[str, ...] = ()
    yeni_kolonlar: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    kaybolan_kolonlar: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    bozulan_olculer: tuple[str, ...] = ()
    bozulan_boyutlar: tuple[str, ...] = ()

    @property
    def var(self) -> bool:
        return bool(self.yeni_tablolar or self.kaybolan_tablolar
                    or self.yeni_kolonlar or self.kaybolan_kolonlar)

    @property
    def bozuk(self) -> bool:
        """Modelin bir parçası artık çalışmaz durumda mı?

        Yeni kolon eklenmesi zararsızdır; KAYBOLAN bir kolona dayanan ölçü ya
        da boyut ise sessiz yanlış üretmez, doğrudan patlar — ama patlamadan
        önce yakalanması gerekir.
        """
        return bool(self.bozulan_olculer or self.bozulan_boyutlar)

    @property
    def sorulacak_tablolar(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.yeni_tablolar)
                            | set(self.yeni_kolonlar)
                            | set(self.kaybolan_kolonlar)))


def fark(model: AnlamModeli,
         guncel: Mapping[str, tuple[str, ...]]) -> SemaFarki:
    """Modeli kaynak şemanın bugünkü hâliyle karşılaştırır.

    `guncel`: tablo adı -> kolon adları. `SemaKaynagi.tablolar()` çıktısından
    türetilir; bu fonksiyonun kendisi veritabanı görmez (saf).
    """
    modeldeki = {ad: set(t.kolonlar) for ad, t in model.tablolar.items()}
    guncel_kume = {ad: set(k) for ad, k in guncel.items()}

    yeni_t = tuple(sorted(set(guncel_kume) - set(modeldeki)))
    kaybolan_t = tuple(sorted(set(modeldeki) - set(guncel_kume)))

    yeni_k: dict[str, tuple[str, ...]] = {}
    kaybolan_k: dict[str, tuple[str, ...]] = {}
    for ad in sorted(set(modeldeki) & set(guncel_kume)):
        eklenen = guncel_kume[ad] - modeldeki[ad]
        silinen = modeldeki[ad] - guncel_kume[ad]
        if eklenen:
            yeni_k[ad] = tuple(sorted(eklenen))
        if silinen:
            kaybolan_k[ad] = tuple(sorted(silinen))

    def kolon_kayip(tablo: str, kolon: str) -> bool:
        if tablo in kaybolan_t:
            return True
        return kolon in kaybolan_k.get(tablo, ())

    bozulan_o = tuple(sorted(
        ad for ad, o in model.olculer.items() if o.tablo in kaybolan_t))
    bozulan_b = tuple(sorted(
        ad for ad, b in model.boyutlar.items() if kolon_kayip(b.tablo, b.kolon)))

    return SemaFarki(yeni_tablolar=yeni_t, kaybolan_tablolar=kaybolan_t,
                     yeni_kolonlar=yeni_k, kaybolan_kolonlar=kaybolan_k,
                     bozulan_olculer=bozulan_o, bozulan_boyutlar=bozulan_b)


# --------------------------------------------------------------------------- #
#  Depo
# --------------------------------------------------------------------------- #

class DosyaAnlamDeposu:
    """`AnlamDeposu` portunun dosya uygulaması (ADR-9)."""

    def __init__(self, kok: str | Path, dizin: str = VARSAYILAN_DIZIN) -> None:
        self.kok = Path(kok)
        self.dizin = self.kok / dizin
        self.gecmis_dizini = self.dizin / GECMIS_DIZIN

    # ------------------------------------------------------------------ yollar

    def yol(self, baglanti: str) -> Path:
        return self.dizin / f"{slug(baglanti)}.json"

    def gecmis_yolu(self, baglanti: str, surum: int) -> Path:
        return self.gecmis_dizini / f"{slug(baglanti)}-v{surum}.json"

    # ------------------------------------------------------------------ okuma

    def oku(self, baglanti: str) -> AnlamModeli | None:
        """Yürürlükteki modeli verir. Bozuksa None — kapalı devre."""
        return self.oku_ayrintili(baglanti)[0]

    def oku_ayrintili(self, baglanti: str) -> tuple[AnlamModeli | None, list[str]]:
        """(model, sorunlar). Sihirbaz sorunları kullanıcıya gösterir."""
        p = self.yol(baglanti)
        try:
            metin = p.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None, []
        except OSError as e:
            return None, [f"Anlam modeli dosyası okunamadı: {e}"]
        model, sorunlar = yukle(metin)
        if sorunlar:
            sorunlar = [f"{p.name}: {s}" for s in sorunlar]
        return model, sorunlar

    def surum_oku(self, baglanti: str, surum: int) -> AnlamModeli | None:
        try:
            metin = self.gecmis_yolu(baglanti, surum).read_text(encoding="utf-8")
        except OSError:
            return None
        return yukle(metin)[0]

    def gecmis(self, baglanti: str) -> list[int]:
        """Arşivdeki sürüm numaraları, artan sırada."""
        onek = f"{slug(baglanti)}-v"
        surumler: list[int] = []
        try:
            adaylar = list(self.gecmis_dizini.iterdir())
        except OSError:
            return []
        for p in adaylar:
            if p.name.startswith(onek) and p.suffix == ".json":
                try:
                    surumler.append(int(p.stem[len(onek):]))
                except ValueError:
                    continue
        return sorted(surumler)

    # ------------------------------------------------------------------ yazma

    def yaz(self, model: AnlamModeli) -> int:
        """Modeli kaydeder, yeni sürüm numarasını döndürür.

        Geçersiz model YAZILMAZ ve istisna fırlatır: buraya gelen model
        sihirbazın ürettiğidir, güvenilmeyen bir girdi değil. Sessizce
        yazmamak veri kaybı olurdu (§ modül başlığı).
        """
        sorunlar = model.dogrula()
        if sorunlar:
            raise ValueError(
                "Geçersiz anlam modeli kaydedilemez:\n  - " + "\n  - ".join(sorunlar))

        self.dizin.mkdir(parents=True, exist_ok=True)
        self.gecmis_dizini.mkdir(parents=True, exist_ok=True)

        # Yürürlükteki sürüm varsa önce arşivlenir. Arşiv ekle-only: aynı
        # sürüm numarası ikinci kez yazılmaz (Değişmez #5 kalıbı).
        onceki = self.oku(model.baglanti)
        if onceki is not None:
            hedef = self.gecmis_yolu(model.baglanti, onceki.surum)
            if not hedef.exists():
                _atomik_yaz(hedef, onceki.to_json())

        _atomik_yaz(self.yol(model.baglanti), model.to_json())
        return model.surum

    def sil(self, baglanti: str) -> None:
        """Yürürlükteki modeli kaldırır. Arşive DOKUNMAZ."""
        try:
            self.yol(baglanti).unlink()
        except OSError:
            pass


def _atomik_yaz(hedef: Path, metin: str) -> None:
    """Geçici dosyaya yaz, sonra yerine taşı.

    Yarıda kesilen bir yazma, modeli okunamaz bırakırdı; bu hâliyle kesilme
    anında eski dosya bozulmadan yerinde durur.
    """
    hedef.parent.mkdir(parents=True, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=str(hedef.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, hedef)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise
