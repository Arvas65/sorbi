"""Portlar — çekirdeğin dış dünyayla tek sözleşmesi (MIMARI §3).

Bağımlılık oku her zaman içeri bakar: çekirdek uygulamaları değil bu
Protocol'leri tanır; uygulamalar `app/baglanti/` altında yaşar ve bağlama
`app/akis/` içinde AÇIKÇA yapılır (DI konteyneri yok — MIMARI §10).

Bir soyutlamanın port olma ölçütü: **ikinci uygulaması ya bugün var, ya
SPEC'te yazılı.** "Her ihtimale karşı arayüz" aşırı mühendisliğin en yaygın
biçimidir; aşağıdaki her portun gerekçesi docstring'inde.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.cekirdek.anlam import AnlamModeli
from app.cekirdek.secim import EslemeSonucu
from app.cekirdek.tipler import Iliski, Sonuc, TabloSemasi


@runtime_checkable
class SemaKaynagi(Protocol):
    """Ham şema okuma — SİHİRBAZIN girdisi (SPEC A-2).

    Gerekçe: sqlite + postgres (SPEC H-1).

    Bu port `Yurutucu` ile BİRLEŞTİRİLMEZ ve bu kozmetik bir tercih değil.
    `farkli_degerler` veri DEĞERİ döndürür ve o değerler yalnız sihirbaz
    ekranına — yani insana — gider (SPEC A-4). Ayrı arayüzler, sorgu
    yolundaki kodun bu metoda erişiminin HİÇ OLMAMASI demektir: Sınır 1
    disiplinle değil, tip düzeyinde uygulanır (MIMARI §6/I).
    """

    def tablolar(self) -> list[TabloSemasi]: ...

    def iliskiler(self) -> list[Iliski]: ...

    def farkli_degerler(self, tablo: str, kolon: str, limit: int) -> list[str]:
        """Yalnız sihirbaza. İstem yoluna asla çıkmaz."""
        ...

    def satir_sayisi(self, tablo: str, kosul: str | None = None) -> int:
        """Sihirbazdaki sağlama göstergesi (SPEC R-6).

        İnsan 'geçerlilik' sorusunu yanlış cevaplarsa sistemin HER cevabı
        tutarlı biçimde yanlış olur ve hiçbir güven kontrolü bunu yakalayamaz
        — içeride her şey tutarlıdır. Tek çare insanın gözüdür: "bu filtreyle
        12.480 satır kalıyor, 1.204 satır düşüyor."
        """
        ...


@runtime_checkable
class Yurutucu(Protocol):
    """Salt-okunur çalıştırma (SPEC E-3).

    Gerekçe: sqlite + postgres + mysql + mssql.

    SÖZLEŞME (Liskov). Her uygulama şunları GERÇEKTEN yapar:
      1. `zaman_asimi_sn` içinde bitmeyen sorguyu iptal eder,
      2. yazma girişimini veritabanı düzeyinde imkânsız kılar,
      3. `azami_satir`i SUNUCU tarafında uygular,
      4. istisna fırlatmaz — başarısızlık `Sonuc.durum` ile döner.

    Yapamayan bir sürücü için uygulama YAZILMAZ. v3'ün G-A hatası tam olarak
    bu sözün sessizce zayıflatılmasıydı: `executor.run()` zaman aşımını yalnız
    `hasattr(raw, "interrupt")` doğruysa kuruyordu, yani SQLite'ta 30 saniye
    sözü gerçekti, Postgres'te değildi. Alt tür üst türün sözünü sessizce
    zayıflatırsa bu bir uyum sorunu değil, bir Liskov ihlalidir.

    Bu sözleşme `tests/sozlesme/test_yurutucu.py` ile HER uygulamada
    parametrik koşar; geçmeyen bir lehçe dağıtılmaz.
    """

    def calistir(self, sql: str, zaman_asimi_sn: int, azami_satir: int) -> Sonuc: ...

    def yazma_denemesi(self) -> bool:
        """True = bu hesap yazabiliyor. Bağlantı 'riskli' işaretlenir ve
        denetim izine yazılır (SPEC E-3)."""
        ...


@runtime_checkable
class AnlamDeposu(Protocol):
    """Anlam modelinin kalıcılığı (ADR-9).

    Gerekçe: bugün tek uygulama (`anlam/` dizininde dosya), ama ADR-9 §6
    başka bir deponun çağıran kodu değiştirmeden devralabilmesini gerektiriyor.
    """

    def oku(self, baglanti: str) -> AnlamModeli | None: ...

    def yaz(self, model: AnlamModeli) -> int:
        """Yeni sürüm numarasını döndürür; önceki sürümü geçmişe taşır."""
        ...

    def gecmis(self, baglanti: str) -> list[int]: ...


@runtime_checkable
class Esleyici(Protocol):
    """soru + sözlük -> Secim. Hattın TEK stokastik parçası (ADR-8).

    Gerekçe: ollama (yerel, varsayılan) + openai-uyumlu api (ADR-5 = B).

    SÖZLEŞME: istisna fırlatmaz; başarısızlık `EslemeSonucu.hata` ile döner.
    Ayrıca isteme YALNIZ `AnlamModeli.sozluk()` çıktısı konur — şema metni,
    örnek satır ya da SQL örneği konmaz (Sınır 1, SPEC E-1).
    """

    def esle(self, soru: str, sozluk: dict) -> EslemeSonucu: ...


@runtime_checkable
class Onbellek(Protocol):
    """Sonuç önbelleği — Sınır 2'nin (SPEC E-2) tek meşru veri barınağı.

    Gerekçe: bellek içi uygulama + testlerde sahte uygulama.

    SÖZLEŞME: `Sonuc` yalnız burada yaşar. Diske yazılmaz, denetim izine
    girmez, oturum sonunda `bosalt()` ile silinir. Anahtar bağlantıyı, SQL
    özetini VE anlam modeli sürümünü içerir — sürüm değişince önbellek
    kendiliğinden geçersizleşir.
    """

    def al(self, anahtar: str) -> Sonuc | None: ...

    def koy(self, anahtar: str, sonuc: Sonuc, ttl_sn: int) -> None: ...

    def bosalt(self) -> None: ...


@runtime_checkable
class Cizer(Protocol):
    """PanoPlani -> ekran.

    Gerekçe: streamlit bugün; ayrıca çizersiz test koşabilmek için sahte
    uygulama bugün de gerekli.
    """

    def ciz(self, plan: object, sonuclar: dict) -> None: ...
