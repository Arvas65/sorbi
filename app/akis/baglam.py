"""Oturum bağlamı (SPEC E-4, BLOK) — süreç geneli durumun kaldırılması.

Bugünkü sızıntı iki yerde:

1. `connections.aktifle()` **süreç genelindeki** `config.DB_URL` ve
   `config.TARGET_DIALECT` değerlerini değiştiriyor.
2. `pipeline._index` modül düzeyinde tek bir nesne.

Streamlit bütün oturumları tek Python sürecinde koşturur. Sonuç: A kullanıcısı
bağlantı değiştirdiğinde B kullanıcısının sorusu **başka bir veritabanına**
gidiyor.

v3'te bunun bedeli "yanlış veritabanı"ydı — fark edilebilir bir hata. v4'te
bedeli **yanlış anlam**: aynı veritabanına doğru bağlanıp başka bir müşterinin
anlam modeliyle sorgu derlemek. Sorgu çalışır, tablo döner, sayı yanlıştır ve
hiçbir kontrol bunu yakalayamaz — içeride her şey tutarlıdır. Bu yüzden E-4
v4'te de BLOK.

Çare: bağlantı bir DEĞER olarak taşınır, bir yan etki olarak değil. İndeks de
o değerin anahtarına göre önbelleklenir.

Bu modül `app/akis/` altındadır ama yalnız stdlib import eder: indeks üretimi
dışarıdan enjekte edilen bir fabrikadır (DIP). Bu sayede `sqlalchemy` ya da
`chromadb` olmadan test edilebilir — ki indeks kurmak pahalı olduğu için
testin onu gerçekten kurmaması zaten şart.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

VARSAYILAN_AZAMI_INDEKS = 4          # aynı anda bellekte tutulacak indeks sayısı


@dataclass(frozen=True)
class OturumBaglami:
    """Bir sorunun hangi veritabanına ve hangi anlamla gideceği.

    Değişmez: bir bağlam elden ele geçerken altından değiştirilemez. Sızıntının
    kökü tam olarak buydu — paylaşılan bir nesnenin bir yerde değiştirilip
    başka yerde okunması.
    """

    db_url: str
    lehce: str = "sqlite"
    anlam_surumu: int = 0            # 0 = anlam katmanı devre dışı (v3 yolu)
    baglanti_adi: str = ""

    @property
    def anahtar(self) -> str:
        """Önbellek anahtarı.

        Anlam modeli sürümü anahtarın PARÇASIDIR: model yeni sürüme geçince
        eski indeks ve eski sonuçlar kendiliğinden geçersizleşir. Sürümü
        anahtara koymamak, İP-23'ün cetvel çürümesinin önbellek tarafını
        üretirdi — aynı anahtar, değişmiş anlam.
        """
        return f"{self.db_url}|{self.lehce}|v{self.anlam_surumu}"

    def yeni_anlam(self, surum: int) -> OturumBaglami:
        from dataclasses import replace
        return replace(self, anlam_surumu=surum)


class IndeksDeposu:
    """Bağlantı anahtarına göre indeks önbelleği. İş parçacığı güvenli.

    Sınırlıdır (LRU): her yeni bağlantı için bir indeks tutmak bellekte
    sınırsız büyürdü. Sınır aşılınca en eski düşer ve gerekirse yeniden kurulur
    — yavaşlar, ama yanlış cevap vermez.
    """

    def __init__(self, fabrika: Callable[[OturumBaglami], Any],
                 azami: int = VARSAYILAN_AZAMI_INDEKS) -> None:
        self._fabrika = fabrika
        self._azami = max(1, azami)
        self._kilit = threading.RLock()
        self._kayit: OrderedDict[str, Any] = OrderedDict()

    def al(self, baglam: OturumBaglami) -> Any:
        """Bağlama ait indeksi verir; yoksa kurar.

        Kurma işi kilidin DIŞINDA yapılır: indeks kurmak saniyeler sürebilir ve
        kilidi o süre boyunca tutmak, farklı veritabanlarına giden iki isteğin
        birbirini beklemesi demek olurdu. Bedeli: iki istek aynı anda aynı
        bağlantı için gelirse indeks iki kez kurulabilir. Yarış kaybedeni
        atılır; sonuç yine doğrudur, yalnız bir kez fazla iş yapılmıştır.
        """
        with self._kilit:
            mevcut = self._kayit.get(baglam.anahtar)
            if mevcut is not None:
                self._kayit.move_to_end(baglam.anahtar)
                return mevcut

        yeni = self._fabrika(baglam)

        with self._kilit:
            varolan = self._kayit.get(baglam.anahtar)
            if varolan is not None:          # yarışı başkası kazandı
                self._kayit.move_to_end(baglam.anahtar)
                return varolan
            self._kayit[baglam.anahtar] = yeni
            self._kayit.move_to_end(baglam.anahtar)
            while len(self._kayit) > self._azami:
                self._kayit.popitem(last=False)
            return yeni

    def dus(self, baglam: OturumBaglami) -> None:
        """Tek bir bağlamın indeksini düşürür (şema değişti, model sürümü arttı)."""
        with self._kilit:
            self._kayit.pop(baglam.anahtar, None)

    def bosalt(self) -> None:
        with self._kilit:
            self._kayit.clear()

    def __len__(self) -> int:
        with self._kilit:
            return len(self._kayit)

    @property
    def anahtarlar(self) -> tuple[str, ...]:
        with self._kilit:
            return tuple(self._kayit)
