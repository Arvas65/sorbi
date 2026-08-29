"""Anlam modeli (ADR-8, ADR-9) — şemanın söyleyemediğini insanın söylediği yer.

Bir veritabanı şeması, sorulan iş sorusunu cevaplamak için gereken bilginin
yalnız bir kısmını taşır. Üç eksen şemada HİÇ yoktur ve tahminle doldurulamaz
(v4 SPEC §2):

    eksen 6 — TANE:        bir satır neyi temsil ediyor?
    eksen 7 — OLAY TARİHİ: "ne zaman oldu" hangi kolon?
    eksen 8 — GEÇERLİLİK:  hangi satırlar sayılmamalı?

Hiçbir model `iptal` kolonunun varlığından o satırların sayımdan çıkarılması
gerektiğini BİLEMEZ; tahmin eder ve tahmini sessizce yanlış çıkar. Bu modül,
o üç cevabın yaşadığı yerdir ve `dogrula()` üçünün de verilmiş olmasını
zorunlu kılar.

Sözleşme: `dogrula()` İSTİSNA FIRLATMAZ. Bozuk bir modelin yüklenmesi bir
program hatası değil, beklenen bir durumdur — kullanıcı dosyayı elle
düzenlemiş olabilir. Kapalı devre: sorun varsa liste dolu döner, model
yüklenmez (`validator.py`'nin kapı sözleşmesiyle aynı kalıp).
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

from app.cekirdek.tipler import Iliski, IliskiGuveni, Karar, Toplama, Tur

SEMA_SURUMU = 1          # bu DOSYA biçiminin sürümü; modelin kendi sürümü ayrı


def _donmus(d: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Sözlüğü salt-okunur görünüme çevirir.

    `frozen=True` bir dataclass'ın ALANLARINI korur, alanın işaret ettiği
    sözlüğü korumaz. Değişmezlik iddiası buradan sızardı.
    """
    return MappingProxyType(dict(d or {}))


# --------------------------------------------------------------------------- #
#  Parçalar
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Olcu:
    """Sayılabilir bir şey. Model bunu ADIYLA seçer, ifadesini görmez."""

    ad: str
    ifade: str                            # ör. "COUNT(DISTINCT muayene.muayene_id)"
    tablo: str                            # hangi tabloya ait (JOIN yolu bundan çıkar)
    toplama: Toplama = Toplama.SAYIM
    birim: str = ""
    kaynak_kosulu: str | None = None      # eksen 2+3: "olcum.tip = 'BOY'"
    gosterim: str = ""                    # panoda görünen ad
    uyari: str | None = None

    @property
    def yeniden_toplanabilir(self) -> bool:
        return self.toplama.yeniden_toplanabilir


@dataclass(frozen=True)
class Boyut:
    """Gruplanabilir bir şey."""

    ad: str
    tablo: str
    kolon: str
    gosterim: str = ""
    sozluk_karari: Karar = Karar.SORULMADI
    # Yalnız İNSAN ONAYLI değerler (SPEC A-4, K-3). Onaylanmamış bir değer
    # buraya hiç yazılmaz — dolayısıyla bu sözlük istemle paylaşılabilir.
    sozluk: Mapping[str, str] = field(default_factory=dict)
    tarih_mi: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "sozluk", _donmus(self.sozluk))


@dataclass(frozen=True)
class TabloAnlami:
    """Bir tablonun ne olduğu — şemanın söyleyemediği kısım."""

    ad: str
    tur: Tur
    tane: str                                   # eksen 6 — insan söyler
    kolonlar: tuple[str, ...] = ()              # etiketleme anındaki kolon adları
    olay_tarihi: str | None = None              # eksen 7 — olay tablolarında zorunlu
    gecerlilik_karari: Karar = Karar.SORULMADI  # eksen 8
    gecerlilik: str | None = None               # "randevu.iptal = 0"
    iliskiler: tuple[Iliski, ...] = ()

    @property
    def olay_mi(self) -> bool:
        return self.tur is Tur.OLAY


@dataclass(frozen=True)
class AnlamModeli:
    """Bir bağlantının anlamı. Veri tutmaz — yalnız tanım (ADR-9)."""

    baglanti: str
    surum: int = 1
    onaylayan: str = ""
    tablolar: Mapping[str, TabloAnlami] = field(default_factory=dict)
    olculer: Mapping[str, Olcu] = field(default_factory=dict)
    boyutlar: Mapping[str, Boyut] = field(default_factory=dict)
    maskeli: frozenset[str] = frozenset()       # "hasta.tckn" biçiminde

    def __post_init__(self) -> None:
        object.__setattr__(self, "tablolar", _donmus(self.tablolar))
        object.__setattr__(self, "olculer", _donmus(self.olculer))
        object.__setattr__(self, "boyutlar", _donmus(self.boyutlar))
        object.__setattr__(self, "maskeli", frozenset(self.maskeli))

    # ---------------------------------------------------------------- sorgular

    def olay_tablolari(self) -> tuple[str, ...]:
        return tuple(sorted(a for a, t in self.tablolar.items() if t.olay_mi))

    def sozluk(self) -> dict[str, Any]:
        """Eşleyiciye (LLM) gidecek TEK malzeme — Sınır 1 (SPEC E-1).

        İçinde ne var: ölçü ve boyut adları, gösterimleri, birimleri, insan
        onaylı değer sözlükleri, zaman taneleri.
        İçinde ne YOK: tablo/kolon ifadeleri, SQL parçaları, örneklenmiş
        değerler, şema metni.

        Bu ayrım kozmetik değil: eşleyici bir kolon adı görebilseydi onu
        kullanmaya çalışır ve eksen 1/4 (ad ve kodlama farkları) geri gelirdi.
        """
        return {
            "olculer": [
                {"ad": o.ad, "gosterim": o.gosterim or o.ad, "birim": o.birim}
                for o in sorted(self.olculer.values(), key=lambda x: x.ad)
            ],
            "boyutlar": [
                {"ad": b.ad, "gosterim": b.gosterim or b.ad,
                 "tarih_mi": b.tarih_mi,
                 "degerler": sorted(b.sozluk.values()) if b.sozluk else []}
                for b in sorted(self.boyutlar.values(), key=lambda x: x.ad)
            ],
        }

    def yeni_surum(self, **degisiklikler: Any) -> AnlamModeli:
        """Sürüm artırarak yeni bir model döndürür. Mevcut nesne değişmez."""
        degisiklikler.setdefault("surum", self.surum + 1)
        return replace(self, **degisiklikler)

    # ------------------------------------------------------------- doğrulama

    def dogrula(self) -> list[str]:
        """Modeli denetler. Boş liste = geçerli. ASLA istisna fırlatmaz.

        Her ileti, sorunun HANGİ alanda olduğunu adıyla söyler — çünkü bu
        iletiyi okuyacak olan sihirbazdaki insandır, geliştirici değil.
        """
        try:
            return self._dogrula()
        except Exception as e:                      # noqa: BLE001 — kapalı devre
            return [f"Model çözümlenemedi ({type(e).__name__}: {e}). "
                    "Dosya bozuk olabilir; önceki sürüme dönün."]

    def _dogrula(self) -> list[str]:
        s: list[str] = []

        if self.surum < 1:
            s.append(f"Sürüm numarası 1'den küçük olamaz (bulunan: {self.surum}).")
        if not self.baglanti:
            s.append("Model bir bağlantı adı taşımıyor.")

        for ad, t in self.tablolar.items():
            if ad != t.ad:
                s.append(f"'{ad}' anahtarı ile tablo adı '{t.ad}' uyuşmuyor.")
            if not isinstance(t.tur, Tur):
                s.append(f"'{ad}': tablo türü geçersiz — 'olay' ya da 'varlik' olmalı.")
                continue
            if not (t.tane or "").strip():
                s.append(f"'{ad}': bir satırın neyi temsil ettiği (tane) yazılmamış. "
                         "Bu olmadan 'ortalama' ve 'sayı' soruları anlamsızdır.")

            if t.olay_mi:
                if not t.olay_tarihi:
                    s.append(f"'{ad}': olay tablosu ama olay tarihi kolonu seçilmemiş. "
                             "'Ne zaman oldu' sorusunun cevabı olmadan zaman "
                             "filtresi uygulanamaz.")
                elif t.kolonlar and t.olay_tarihi not in t.kolonlar:
                    s.append(f"'{ad}': olay tarihi olarak '{t.olay_tarihi}' seçilmiş "
                             f"ama bu tabloda böyle bir kolon yok.")
            elif t.olay_tarihi:
                s.append(f"'{ad}': varlık tablosuna olay tarihi verilmiş "
                         f"('{t.olay_tarihi}'). Varlık tabloları olay taşımaz.")

            if t.gecerlilik_karari is Karar.SORULMADI:
                s.append(f"'{ad}': hangi satırların sayılmaması gerektiği "
                         "sorulmamış. İptal/silinmiş kayıtlar sessizce sayıma "
                         "girerse sonuç tutarlı biçimde yanlış olur.")
            elif t.gecerlilik_karari is Karar.VAR and not (t.gecerlilik or "").strip():
                s.append(f"'{ad}': geçerlilik filtresi 'var' işaretlenmiş ama "
                         "filtre ifadesi boş.")
            elif t.gecerlilik_karari is Karar.YOK and t.gecerlilik:
                s.append(f"'{ad}': geçerlilik filtresi 'yok' işaretlenmiş ama "
                         f"bir ifade yazılmış ('{t.gecerlilik}').")

            for i in t.iliskiler:
                if i.hedef not in self.tablolar:
                    s.append(f"'{ad}': ilişki modelde olmayan '{i.hedef}' "
                             "tablosuna gidiyor.")
                if i.guven is IliskiGuveni.DUSUK:
                    s.append(f"'{ad}': '{i.hedef}' ilişkisi ad benzerliğinden "
                             "türetilmiş ve onaylanmamış. Onaylayın ya da silin.")

        for ad, o in self.olculer.items():
            if ad != o.ad:
                s.append(f"Ölçü anahtarı '{ad}' ile adı '{o.ad}' uyuşmuyor.")
            if o.tablo not in self.tablolar:
                s.append(f"'{ad}' ölçüsü modelde olmayan '{o.tablo}' tablosuna dayanıyor.")
            if not (o.ifade or "").strip():
                s.append(f"'{ad}' ölçüsünün ifadesi boş.")

        for ad, b in self.boyutlar.items():
            if ad != b.ad:
                s.append(f"Boyut anahtarı '{ad}' ile adı '{b.ad}' uyuşmuyor.")
            t = self.tablolar.get(b.tablo)
            if t is None:
                s.append(f"'{ad}' boyutu modelde olmayan '{b.tablo}' tablosuna dayanıyor.")
            elif t.kolonlar and b.kolon not in t.kolonlar:
                s.append(f"'{ad}' boyutu '{b.tablo}' tablosunda olmayan "
                         f"'{b.kolon}' kolonunu gösteriyor.")
            if b.sozluk_karari is Karar.SORULMADI:
                s.append(f"'{ad}': değer sözlüğü sorulmamış. Model, kolonun hangi "
                         "değerleri taşıdığını bilmeden filtre yazamaz.")
            elif b.sozluk_karari is Karar.VAR and not b.sozluk:
                s.append(f"'{ad}': değer sözlüğü 'var' işaretlenmiş ama boş.")
            if f"{b.tablo}.{b.kolon}" in self.maskeli:
                s.append(f"'{ad}' boyutu maskeli bir kolonu ({b.tablo}.{b.kolon}) "
                         "gösteriyor. Maskeli kolon boyut olamaz.")

        if self.tablolar and not self.olay_tablolari():
            s.append("Modelde hiç olay tablosu yok. En az bir olay tablosu "
                     "olmadan hiçbir iş sorusu cevaplanamaz.")

        return s

    @property
    def gecerli(self) -> bool:
        return not self.dogrula()

    # ---------------------------------------------------------- serileştirme

    def to_dict(self) -> dict[str, Any]:
        return {
            "sema_surumu": SEMA_SURUMU,
            "baglanti": self.baglanti,
            "surum": self.surum,
            "onaylayan": self.onaylayan,
            "tablolar": {
                a: {
                    "ad": t.ad, "tur": t.tur.value, "tane": t.tane,
                    "kolonlar": list(t.kolonlar),
                    "olay_tarihi": t.olay_tarihi,
                    "gecerlilik_karari": t.gecerlilik_karari.value,
                    "gecerlilik": t.gecerlilik,
                    "iliskiler": [
                        {"kaynak": i.kaynak, "kaynak_kolon": i.kaynak_kolon,
                         "hedef": i.hedef, "hedef_kolon": i.hedef_kolon,
                         "guven": i.guven.value}
                        for i in t.iliskiler
                    ],
                } for a, t in sorted(self.tablolar.items())
            },
            "olculer": {
                a: {"ad": o.ad, "ifade": o.ifade, "tablo": o.tablo,
                    "toplama": o.toplama.value, "birim": o.birim,
                    "kaynak_kosulu": o.kaynak_kosulu, "gosterim": o.gosterim,
                    "uyari": o.uyari}
                for a, o in sorted(self.olculer.items())
            },
            "boyutlar": {
                a: {"ad": b.ad, "tablo": b.tablo, "kolon": b.kolon,
                    "gosterim": b.gosterim,
                    "sozluk_karari": b.sozluk_karari.value,
                    "sozluk": dict(b.sozluk), "tarih_mi": b.tarih_mi}
                for a, b in sorted(self.boyutlar.items())
            },
            "maskeli": sorted(self.maskeli),
        }

    def to_json(self, girinti: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=girinti)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> AnlamModeli:
        """Sözlükten model kurar. Bozuk girdi için istisna fırlatabilir —
        çağıran `yukle()` kullanmalıdır (kapalı devre sarmalayıcı)."""
        tablolar = {
            a: TabloAnlami(
                ad=t["ad"], tur=Tur(t["tur"]), tane=t.get("tane", ""),
                kolonlar=tuple(t.get("kolonlar", ())),
                olay_tarihi=t.get("olay_tarihi"),
                gecerlilik_karari=Karar(t.get("gecerlilik_karari", "sorulmadi")),
                gecerlilik=t.get("gecerlilik"),
                iliskiler=tuple(
                    Iliski(kaynak=i["kaynak"], kaynak_kolon=i["kaynak_kolon"],
                           hedef=i["hedef"], hedef_kolon=i["hedef_kolon"],
                           guven=IliskiGuveni(i.get("guven", "kesin")))
                    for i in t.get("iliskiler", ())
                ),
            ) for a, t in (d.get("tablolar") or {}).items()
        }
        olculer = {
            a: Olcu(ad=o["ad"], ifade=o["ifade"], tablo=o["tablo"],
                    toplama=Toplama(o.get("toplama", "sayim")),
                    birim=o.get("birim", ""),
                    kaynak_kosulu=o.get("kaynak_kosulu"),
                    gosterim=o.get("gosterim", ""), uyari=o.get("uyari"))
            for a, o in (d.get("olculer") or {}).items()
        }
        boyutlar = {
            a: Boyut(ad=b["ad"], tablo=b["tablo"], kolon=b["kolon"],
                     gosterim=b.get("gosterim", ""),
                     sozluk_karari=Karar(b.get("sozluk_karari", "sorulmadi")),
                     sozluk=b.get("sozluk") or {},
                     tarih_mi=bool(b.get("tarih_mi", False)))
            for a, b in (d.get("boyutlar") or {}).items()
        }
        return AnlamModeli(
            baglanti=d.get("baglanti", ""), surum=int(d.get("surum", 1)),
            onaylayan=d.get("onaylayan", ""),
            tablolar=tablolar, olculer=olculer, boyutlar=boyutlar,
            maskeli=frozenset(d.get("maskeli") or ()),
        )


def yukle(metin: str) -> tuple[AnlamModeli | None, list[str]]:
    """JSON metninden model yükler — kapalı devre.

    Döner: (model, sorunlar). Sorunlar doluysa model None'dır ve YÜKLENMEZ.
    Yarı geçerli bir model asla döndürülmez: elde tutulan her `AnlamModeli`
    doğrulamadan geçmiştir.
    """
    try:
        ham = json.loads(metin)
    except Exception as e:                          # noqa: BLE001
        return None, [f"Dosya geçerli bir JSON değil ({type(e).__name__}: {e})."]

    if not isinstance(ham, dict):
        return None, ["Dosyanın en dış katmanı bir nesne olmalı."]

    ds = ham.get("sema_surumu", SEMA_SURUMU)
    if ds != SEMA_SURUMU:
        return None, [f"Dosya biçimi sürümü {ds}, bu sürüm {SEMA_SURUMU} bekliyor. "
                      "Göç gerekiyor."]
    try:
        model = AnlamModeli.from_dict(ham)
    except Exception as e:                          # noqa: BLE001
        return None, [f"Model kurulamadı ({type(e).__name__}: {e})."]

    sorunlar = model.dogrula()
    return (None, sorunlar) if sorunlar else (model, [])
