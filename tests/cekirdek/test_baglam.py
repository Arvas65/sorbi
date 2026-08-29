"""E-4 testleri — oturum bağlamı ve indeks yalıtımı.

SPEC E-4 kabul kriteri: iki bağlantı + iki anlam modeliyle eşzamanlı çağrı
testi; her cevap kendi veritabanından VE kendi anlamından gelir.
"""
from __future__ import annotations

import threading

from app.akis.baglam import IndeksDeposu, OturumBaglami

A = OturumBaglami("sqlite:///a.db", "sqlite", anlam_surumu=1, baglanti_adi="A")
B = OturumBaglami("postgresql://h/b", "postgres", anlam_surumu=1, baglanti_adi="B")


class SahteIndeks:
    """Kurulduğu bağlamı hatırlayan sahte indeks."""

    def __init__(self, baglam: OturumBaglami):
        self.baglam = baglam


def depo(azami: int = 4, gecikme: float = 0.0) -> IndeksDeposu:
    def fabrika(b: OturumBaglami) -> SahteIndeks:
        if gecikme:
            import time
            time.sleep(gecikme)
        return SahteIndeks(b)
    return IndeksDeposu(fabrika, azami=azami)


# --------------------------------------------------------------- bağlam değeri

def test_baglam_degismez():
    import dataclasses

    import pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        A.db_url = "baska"          # type: ignore[misc]


def test_anahtar_anlam_surumunu_icerir():
    """Model yeni sürüme geçince eski indeks kendiliğinden geçersizleşir.

    Sürümü anahtara koymamak, İP-23'ün cetvel çürümesinin önbellek tarafını
    üretirdi: aynı anahtar, değişmiş anlam.
    """
    assert A.anahtar != A.yeni_anlam(2).anahtar


def test_ayni_url_farkli_lehce_ayri_anahtar():
    ayni_url = OturumBaglami("sqlite:///a.db", "postgres", anlam_surumu=1)
    assert ayni_url.anahtar != A.anahtar


# ------------------------------------------------------- yalıtım (E-4 çekirdeği)

def test_iki_baglanti_birbirine_karismaz():
    d = depo()
    ia, ib = d.al(A), d.al(B)
    assert ia.baglam is A
    assert ib.baglam is B
    assert ia is not ib


def test_ayni_baglam_ayni_indeksi_alir():
    d = depo()
    assert d.al(A) is d.al(A)


def test_anlam_surumu_artinca_yeni_indeks_kurulur():
    d = depo()
    eski = d.al(A)
    yeni = d.al(A.yeni_anlam(2))
    assert eski is not yeni
    assert yeni.baglam.anlam_surumu == 2


def test_dus_yalniz_kendi_anahtarini_atar():
    d = depo()
    ia, ib = d.al(A), d.al(B)
    d.dus(A)
    assert d.al(B) is ib          # B dokunulmadan durdu
    assert d.al(A) is not ia      # A yeniden kuruldu


# --------------------------------------------------------------- eşzamanlılık

def test_eszamanli_cagrilar_kendi_baglamlarindan_doner():
    """E-4'ün kabul kriteri.

    v3'te bu senaryo yanlış VERİTABANI demekti. v4'te yanlış ANLAM demek:
    aynı DB'ye doğru bağlanıp başka müşterinin modeliyle derlemek. Sorgu
    çalışır, tablo döner, sayı yanlıştır ve hiçbir kontrol yakalayamaz.
    """
    d = depo(gecikme=0.01)
    baglamlar = [A, B, A.yeni_anlam(7), B.yeni_anlam(9)] * 6
    sonuclar: list[tuple[OturumBaglami, OturumBaglami]] = []
    kilit = threading.Lock()

    def kos(b: OturumBaglami) -> None:
        idx = d.al(b)
        with kilit:
            sonuclar.append((b, idx.baglam))

    is_parcaciklari = [threading.Thread(target=kos, args=(b,)) for b in baglamlar]
    for t in is_parcaciklari:
        t.start()
    for t in is_parcaciklari:
        t.join()

    assert len(sonuclar) == len(baglamlar)
    for istenen, gelen in sonuclar:
        assert gelen.anahtar == istenen.anahtar, (istenen, gelen)


def test_yaris_kaybedeni_atilir_sonuc_tutarli_kalir():
    """Aynı bağlam için eşzamanlı iki istek indeksi iki kez kurabilir; depo
    tek bir tanesini saklar ve herkes AYNI nesneyi görür."""
    d = depo(gecikme=0.02)
    alinanlar: list[object] = []
    kilit = threading.Lock()

    def kos() -> None:
        idx = d.al(A)
        with kilit:
            alinanlar.append(idx)

    ts = [threading.Thread(target=kos) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    yerlesik = d.al(A)
    assert all(x is yerlesik for x in alinanlar[-4:])   # yerleştikten sonra tek nesne
    assert len(d) == 1


# ----------------------------------------------------------------------- sınır

def test_lru_siniri_bellegi_buyutmez():
    d = depo(azami=2)
    for i in range(5):
        d.al(OturumBaglami(f"sqlite:///{i}.db", "sqlite", anlam_surumu=1))
    assert len(d) == 2


def test_en_son_kullanilan_kalir():
    d = depo(azami=2)
    d.al(A)
    d.al(B)
    d.al(A)                                    # A tazelenir
    d.al(OturumBaglami("sqlite:///c.db", "sqlite", anlam_surumu=1))
    assert A.anahtar in d.anahtarlar
    assert B.anahtar not in d.anahtarlar        # en eski düştü


def test_bosalt():
    d = depo()
    d.al(A)
    d.al(B)
    d.bosalt()
    assert len(d) == 0
