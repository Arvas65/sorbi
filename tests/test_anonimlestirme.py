"""Kişisel veri algılayıcıları ve anonimleştirici (ADR-10) — LLM'siz.

İki yönde sınanır: KAÇIRMAMALI (doğru pozitif) ve BOŞUNA ENGELLEMEMELİ (yanlış
pozitif). Çıkış kapısı yalnız doğrulanmış bulgularla engellediği için yanlış
pozitif testleri kapının kapatılmamasının teminatıdır.
"""
import json
import sys
from pathlib import Path

import pytest

from app.guvenlik.anonimlestirici import Kasa, anonimlestir, jetonlari_ayikla
from app.guvenlik.kisisel_veri import (
    bul,
    dogrulanmis,
    iban_gecerli,
    luhn_gecerli,
    tckn_gecerli,
    vkn_gecerli,
)

sys.path.insert(0, str(Path(__file__).parent / "cekirdek"))
from ornek import gecerli_model  # noqa: E402

# Bilinen geçerli test değerleri — hiçbiri gerçek bir kişiye ait değildir.
TCKN = "10000000146"                          # yaygın kullanılan test TCKN'si
IBAN = "TR33 0006 1005 1978 6457 8413 26"     # yaygın örnek IBAN (sağlaması tutar)
KART = "4111 1111 1111 1111"                  # Visa test kartı (Luhn)


def _vkn_uret(ilk9: str) -> str:
    """Algoritmaya göre geçerli bir VKN üretir (sağlama hanesi hesaplanır)."""
    for son in "0123456789":
        if vkn_gecerli(ilk9 + son):
            return ilk9 + son
    raise AssertionError("üretilemedi")


# ------------------------------------------------------------ doğrulayıcılar

def test_tckn():
    assert tckn_gecerli(TCKN)
    assert not tckn_gecerli("10000000147")          # son hane bozuk
    assert not tckn_gecerli("01234567890")          # 0 ile başlayamaz
    assert not tckn_gecerli("1234567890")           # 10 hane


def test_vkn():
    v = _vkn_uret("123456789")
    assert vkn_gecerli(v)
    assert not vkn_gecerli(v[:9] + str((int(v[9]) + 1) % 10))


def test_iban():
    assert iban_gecerli(IBAN)
    assert not iban_gecerli(IBAN.replace("26", "27"))
    assert not iban_gecerli("DE89370400440532013000")   # yalnız TR


def test_luhn():
    assert luhn_gecerli(KART)
    assert not luhn_gecerli("4111 1111 1111 1112")


# ------------------------------------------------------- doğru pozitifler

@pytest.mark.parametrize("metin,tur", [
    (f"hasta TCKN {TCKN} kaydı", "TCKN"),
    (f"IBAN: {IBAN}", "IBAN"),
    (f"kart {KART} ile ödeme", "KART"),
    ("iletişim ayse.kaya@ornek.com.tr", "EPOSTA"),
    ("cep 0532 123 45 67", "TELEFON"),
    ("cep +90 532 123 45 67", "TELEFON"),
    ("sabit (0212) 555 12 34", "TELEFON"),
])
def test_dogrulanmis_bulgular(metin, tur):
    assert tur in {b.tur for b in dogrulanmis(metin)}, bul(metin)


@pytest.mark.parametrize("metin,tur,parca", [
    ("Dr. Ayşe Kaya'nın hastaları", "KISI", "Ayşe Kaya"),
    ("Zeynep Hanım hangi bölümde", "KISI", "Zeynep"),
    ("Ahmet Yılmaz faturaları", "KISI", "Ahmet Yılmaz"),
    ("plaka 34 ABC 123 olan araç", "PLAKA", "34 ABC 123"),
    ("12.03.1985 doğumlu", "TARIH", "12.03.1985"),
    ("12 Mart 1985 doğumlu", "TARIH", "12 Mart 1985"),
    ("protokol 8812345 numaralı", "SAYI", "8812345"),
    ("sunucu 10.0.0.12 üzerinde", "IP", "10.0.0.12"),
])
def test_suphe_bulgulari(metin, tur, parca):
    assert any(b.tur == tur and b.metin == parca for b in bul(metin)), bul(metin)


# ------------------------------------------------------ yanlış pozitifler

@pytest.mark.parametrize("metin", [
    "Geçen ay kardiyolojide kaç randevu vardı?",
    "2025 yılında bölümlere göre toplam ciro",
    "En çok işlem yapan ilk 10 doktor",
    "SELECT COUNT(*) FROM randevu WHERE tarih >= '2026-01-01' LIMIT 5",
    "Son 30 günde ödenmemiş faturaların toplamı",
    "12345678901 gibi rastgele 11 hane",          # sağlaması tutmayan
])
def test_siradan_soru_dogrulanmis_bulgu_uretmez(metin):
    """Çıkış kapısı bunlarda ENGELLEMEMELİ."""
    assert dogrulanmis(metin) == [], dogrulanmis(metin)


@pytest.mark.parametrize("girdi", ["", None, 42, [], "   "])
def test_tuhaf_girdi_patlamaz(girdi):
    assert bul(girdi) == []


# ------------------------------------------------------ anonimleştirici

def _sozluk():
    return gecerli_model().sozluk()


def test_kanarya_hicbir_kisisel_veri_disari_cikmaz():
    """ADR-10'un kabulü: jetonlanmış metinde tek bir gerçek değer kalmaz."""
    soru = (f"Dr. Ayşe Kaya'nın geçen ay Kardiyoloji bölümündeki kadın hastalarından "
            f"TCKN'si {TCKN}, telefonu 0532 123 45 67, e-postası a.kaya@x.com, "
            f"IBAN'ı {IBAN} olanların faturaları")
    cikti, kasa = anonimlestir(soru, _sozluk())
    for gercek in ("Ayşe", "Kaya", "Kardiyoloji", "kadın", TCKN, "0532", "a.kaya@x.com",
                   "TR33", "Dr."):
        assert gercek.lower() not in cikti.lower(), (gercek, cikti)
    assert dogrulanmis(cikti) == []
    assert "geçen ay" in cikti and "bölümündeki" in cikti      # anlam korunur


def test_yapi_sozcukleri_gider_degerler_gitmez():
    """S1 (ad/gösterim) gider, S2/S3 (değerler) gitmez."""
    cikti, _ = anonimlestir("Bölümlere göre Ödeme durumu Gecikti olan ciro", _sozluk())
    assert "Bölümlere" in cikti and "Ödeme durumu" in cikti
    assert "Gecikti" not in cikti


def test_ekli_deger_de_jetonlanir():
    cikti, kasa = anonimlestir("kardiyolojideki randevular", _sozluk())
    assert cikti.startswith("[DEGER_1]") and cikti.endswith("deki randevular")
    assert kasa.gercegi("[DEGER_1]") == "Kardiyoloji"          # kanonik değer


def test_kisa_deger_kelime_icinde_eslesmez():
    s = {"boyutlar": [{"ad": "cinsiyet", "degerler": ["K", "E"]}]}
    cikti, _ = anonimlestir("kaç kişi var", s)
    assert "[DEGER" not in cikti
    cikti, _ = anonimlestir("cinsiyeti K olanlar", s)
    assert "[DEGER_1]" in cikti


def test_ayni_deger_ayni_jeton_ve_geri_donus():
    cikti, kasa = anonimlestir("Ahmet Yılmaz ve yine Ahmet Yılmaz", _sozluk())
    assert jetonlari_ayikla(cikti) == ["[KISI_1]", "[KISI_1]"]
    assert kasa.geri_cevir(cikti) == "Ahmet Yılmaz ve yine Ahmet Yılmaz"


def test_bilinmeyen_ozel_ad_izin_listesinde_degilse_jetonlanir():
    """İzin listesi ilkesi: güvenli olduğu kanıtlanamayan özel ad gitmez."""
    cikti, _ = anonimlestir("Mehmetcan Özdemir'in faturaları", _sozluk())
    assert "Mehmetcan" not in cikti and "Özdemir" not in cikti


def test_il_ay_ve_hitap_gider():
    cikti, _ = anonimlestir("İstanbul'daki Mart ayı ciro, Ayşe Hanım", _sozluk())
    assert "İstanbul" in cikti and "Mart" in cikti and "Hanım" in cikti
    assert "Ayşe" not in cikti


def test_kasa_icerigi_repr_ile_sizmaz():
    _, kasa = anonimlestir(f"Ahmet Yılmaz {TCKN}", _sozluk())
    for metin in (repr(kasa), str(kasa), json.dumps(kasa.sayim())):
        assert "Ahmet" not in metin and TCKN not in metin


def test_bilinmeyen_jeton_oldugu_gibi_kalir():
    assert Kasa().geri_cevir("[KISI_9] kim") == "[KISI_9] kim"


@pytest.mark.parametrize("girdi", ["", None, 5])
def test_anonimlestirici_tuhaf_girdi(girdi):
    cikti, kasa = anonimlestir(girdi, _sozluk())
    assert cikti == "" and kasa.sayim() == {}
