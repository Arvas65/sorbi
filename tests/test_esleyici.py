"""Eşleyici (İP-53a) — LLM'siz testler; sohbet sahte bir işlevdir.

Üç şeyi sabitler:
1. Sınır 1 (SPEC E-1, değişmez 3): API modunda sözlükteki değerler dışarı ÇIKMAZ.
2. Sözleşme: `esle()` hiçbir girdide istisna fırlatmaz.
3. Yerel ve deterministik işler: tarih aralığı ve değerin sözlüğe oturtulması.
"""
import json
import sys
from pathlib import Path

import pytest

from app.baglanti.esleyici import LlmEsleyici, _tr_kucuk
from app.cekirdek.derleyici import derle
from app.cekirdek.portlar import Esleyici
from app.cekirdek.secim import EslemeSonucu, Secim
from app.cekirdek.tipler import ZamanTanesi
from app.preprocess import resolve_dates

sys.path.insert(0, str(Path(__file__).parent / "cekirdek"))
from ornek import gecerli_model  # noqa: E402

KANARYA = "KANARYA-7731"


def _sahte(cevap, kayit=None):
    def sohbet(mesajlar):
        if kayit is not None:
            kayit.append(mesajlar)
        return cevap if isinstance(cevap, str) else json.dumps(cevap, ensure_ascii=False)
    return sohbet


def _sozluk():
    s = gecerli_model().sozluk()
    for b in s["boyutlar"]:
        if b["ad"] == "bolum":
            b["degerler"] = [*b["degerler"], KANARYA]
    return s


def test_port_sozlesmesine_uyar():
    assert isinstance(LlmEsleyici(_sahte("{}")), Esleyici)


# ------------------------------------------------------------------ Sınır 1

def test_api_modunda_sozluk_degerleri_disari_cikmaz():
    kayit = []
    LlmEsleyici(_sahte({"olculer": ["ciro"]}, kayit), degerleri_gonder=False) \
        .esle("bölümlere göre ciro", _sozluk())
    giden = json.dumps(kayit, ensure_ascii=False)
    assert KANARYA not in giden
    for deger in ("Kardiyoloji", "Dahiliye", "Kadın", "Prof. Dr."):
        assert deger not in giden, deger
    assert "bolum" in giden and "ciro" in giden          # adlar gider


def test_yerel_modda_degerler_gider():
    kayit = []
    LlmEsleyici(_sahte({"olculer": ["ciro"]}, kayit), degerleri_gonder=True) \
        .esle("ciro", _sozluk())
    assert KANARYA in json.dumps(kayit, ensure_ascii=False)


def test_kimlik_numarasi_maskelenir():
    kayit = []
    LlmEsleyici(_sahte({"olculer": ["ciro"]}, kayit)).esle("12345678901 hastanın cirosu", _sozluk())
    giden = json.dumps(kayit, ensure_ascii=False)
    assert "12345678901" not in giden                  # uzun sayı jetonlanır (ADR-10)


def test_istem_kolon_ya_da_sql_tasimaz():
    """Sözlükte tablo/kolon ifadesi yok; istem de taşımamalı (ADR-8)."""
    kayit = []
    LlmEsleyici(_sahte({"olculer": ["ciro"]}, kayit), degerleri_gonder=True).esle("ciro", _sozluk())
    kullanici = kayit[0][1]["content"]
    for yasak in ("SELECT", "JOIN", "fatura.tutar", "randevu.durum"):
        assert yasak not in kullanici, yasak


# ------------------------------------------------------------ mutlu yol

def test_esleme_dogrulanir_ve_derlenir():
    """Eşleyici → Secim.kur (model) → derle: akışın çekirdek yarısı, LLM'siz."""
    cevap = {"olculer": ["randevu_sayisi"], "boyutlar": ["bolum"],
             "filtreler": [{"boyut": "cinsiyet", "islec": "esittir", "degerler": ["kadın"]}],
             "sirala": "randevu_sayisi azalan", "limit": 5}
    s = LlmEsleyici(_sahte(cevap)).esle("kadın hastaların bölümlere göre randevu sayısı", _sozluk())
    assert not s.hata and not s.netlestirme_sorusu
    m = gecerli_model()
    ham = s.secim
    secim = Secim.kur(m, ham.olculer, ham.boyutlar, ham.filtreler, ham.zaman, ham.sirala, ham.limit)
    assert secim.kurulabilir, secim.gecersiz
    assert secim.filtreler[0].degerler == ("Kadın",)       # yerelde oturtuldu
    assert derle(secim, m).ok


@pytest.mark.parametrize("boyut,yazilan,kanonik", [
    ("bolum", "kardiyoloji", "Kardiyoloji"), ("bolum", "KARDİYOLOJİ", "Kardiyoloji"),
    ("cinsiyet", "KADIN", "Kadın"), ("unvan", "prof. dr.", "Prof. Dr.")])
def test_turkce_harf_kurali_ile_oturtma(boyut, yazilan, kanonik):
    cevap = {"olculer": ["ciro"], "filtreler": [{"boyut": boyut, "islec": "esittir", "degerler": [yazilan]}]}
    s = LlmEsleyici(_sahte(cevap)).esle("x", _sozluk())
    assert s.secim.filtreler[0].degerler == (kanonik,)


def test_eslesmeyen_deger_tahmin_edilmez_ve_kur_reddeder():
    """'Kardyoloji' (yazım hatası) en yakın değere SESSİZCE bağlanmaz."""
    cevap = {"olculer": ["ciro"], "filtreler": [{"boyut": "bolum", "islec": "esittir",
                                                 "degerler": ["Kardyoloji"]}]}
    ham = LlmEsleyici(_sahte(cevap)).esle("x", _sozluk()).secim
    assert ham.filtreler[0].degerler == ("Kardyoloji",)
    secim = Secim.kur(gecerli_model(), ham.olculer, filtreler=ham.filtreler)
    assert any("Kardyoloji" in g for g in secim.gecersiz)


# ----------------------------------------------------------------- zaman

def test_tarih_araligi_modelden_degil_yerelden_gelir():
    """Model yanlış bir aralık 'hesaplasa' bile kullanılmaz; aralık resolve_dates'ten."""
    cevap = {"olculer": ["ciro"], "zaman_tanesi": None,
             "baslangic": "1999-01-01", "bitis": "1999-12-31"}
    s = LlmEsleyici(_sahte(cevap)).esle("geçen ay ciro", _sozluk())
    _, bulunan = resolve_dates("geçen ay ciro")
    assert s.secim.zaman.baslangic == bulunan[0]["baslangic"]
    assert s.secim.zaman.bitis == bulunan[0]["bitis"]
    assert s.secim.zaman.ifade == "geçen ay"


def test_zaman_tanesi_modelden():
    s = LlmEsleyici(_sahte({"olculer": ["ciro"], "boyutlar": ["fatura_tarihi"],
                            "zaman_tanesi": "hafta"})).esle("bu yıl haftalık ciro", _sozluk())
    assert s.secim.zaman.tane is ZamanTanesi.HAFTA


def test_iki_zaman_ifadesi_netlestirilir():
    s = LlmEsleyici(_sahte({"olculer": ["ciro"]})).esle("geçen ay ve bu ay ciro", _sozluk())
    assert s.netlestirme_sorusu and "hangisi" in s.netlestirme_sorusu


def test_gecersiz_tane_netlestirmeye_duser():
    s = LlmEsleyici(_sahte({"olculer": ["ciro"], "zaman_tanesi": "saat"})).esle("ciro", _sozluk())
    assert s.netlestirme_sorusu and "saat" in s.netlestirme_sorusu


# ---------------------------------------------- netleştirme ve ifade edilemez

def test_netlestirme_sorusu_iletilir():
    cevap = {"netlestirme": "Ciro mu, ödenmemiş ciro mu?", "secenekler": ["ciro", "odenmemis_ciro"]}
    s = LlmEsleyici(_sahte(cevap)).esle("para", _sozluk())
    assert s.netlestirme_sorusu.startswith("Ciro mu")
    assert s.secenekler == ("ciro", "odenmemis_ciro")
    assert not s.secim.kurulabilir


def test_ifade_edilemez_bir_cikti_olarak_doner():
    s = LlmEsleyici(_sahte({"ifade_edilemez": "stok verisi yok"})).esle("stok", _sozluk())
    assert "ifade edilemiyor" in s.hata and "stok" in s.hata


# ------------------------------------------------------- kapalı devre

@pytest.mark.parametrize("cevap", [
    "", "SELECT * FROM fatura", "{bozuk json", "[]", "null",
    json.dumps({"olculer": 5, "filtreler": "x", "limit": "beş"}),
    json.dumps({"filtreler": [None, 3, {"islec": "esittir"}]}),
])
def test_bozuk_model_ciktisi_istisna_firlatmaz(cevap):
    s = LlmEsleyici(_sahte(cevap)).esle("ciro", _sozluk())
    assert isinstance(s, EslemeSonucu)
    assert not s.secim.kurulabilir          # bozuk çıktıdan hat devam edecek bir seçim doğmaz


def test_sohbet_patlarsa_hata_doner():
    def patlar(_):
        raise ConnectionError("Ollama kapalı")
    s = LlmEsleyici(patlar).esle("ciro", _sozluk())
    assert "ConnectionError" in s.hata and "Ollama kapalı" in s.hata


def test_tr_kucuk_noktali_ve_noktasiz_i():
    assert _tr_kucuk("İSTANBUL") == "istanbul" and _tr_kucuk("ISPARTA") == "ısparta"


@pytest.mark.parametrize("soru", ["", "   ", None, 123])
def test_bos_ya_da_tuhaf_soru(soru):
    assert LlmEsleyici(_sahte("{}")).esle(soru, _sozluk()).hata


def test_ham_cikti_teshis_icin_saklanir():
    s = LlmEsleyici(_sahte("model bir şey saçmaladı")).esle("ciro", _sozluk())
    assert s.ham_cikti == "model bir şey saçmaladı"
