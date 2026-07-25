"""Ön işleme birim testleri (G-07 tarih çözümleme, G-09 kök indirgeme)."""
from datetime import date

from app.preprocess import resolve_dates, light_stem, keywords

TODAY = date(2026, 7, 25)  # Cumartesi — testler deterministik olsun diye sabit


def _found(question):
    _, found = resolve_dates(question, today=TODAY)
    return found


def test_gecen_ay():
    f = _found("geçen ay kaç muayene yapıldı")
    assert f == [{"ifade": "geçen ay", "baslangic": "2026-06-01", "bitis": "2026-06-30"}]


def test_gecen_ay_yilbasi_siniri():
    # Ocak'ta sorulursa geçen ay = önceki yılın Aralık'ı
    _, f = resolve_dates("geçen ay ciro", today=date(2026, 1, 10))
    assert f[0]["baslangic"] == "2025-12-01" and f[0]["bitis"] == "2025-12-31"


def test_son_n_gun():
    f = _found("son 7 gün randevu sayısı")
    assert f[0]["ifade"] == "son 7 gün"
    assert f[0]["baslangic"] == "2026-07-18" and f[0]["bitis"] == "2026-07-25"


def test_bu_yil_ve_gecen_yil():
    f = _found("bu yıl toplam ciro")
    assert f[0]["baslangic"] == "2026-01-01" and f[0]["bitis"] == "2026-07-25"
    f = _found("geçen yıl toplam ciro")
    assert f[0]["baslangic"] == "2025-01-01" and f[0]["bitis"] == "2025-12-31"


def test_ceyrek():
    # Temmuz = 3. çeyrek; son/geçen çeyrek = Q2
    f = _found("son çeyrekte gelmeyen hasta sayısı")
    assert f[0]["baslangic"] == "2026-04-01" and f[0]["bitis"] == "2026-06-30"


def test_tarihsiz_soru_degismez():
    q = "bölümlere göre doktor sayısı"
    annotated, found = resolve_dates(q, today=TODAY)
    assert annotated == q and found == []


def test_tarihli_soruya_aciklama_eklenir():
    annotated, _ = resolve_dates("dün kaç randevu vardı", today=TODAY)
    assert "[TARIH ARALIĞI:" in annotated and "2026-07-24" in annotated


def test_light_stem():
    # Amaç tam morfoloji değil; aynı kelimenin çekimleri AYNI köke inmeli
    assert light_stem("müşterilerimizin") == light_stem("müşterileri")
    assert light_stem("doktorlar") == "doktor"
    assert light_stem("randevular") == light_stem("randevu")
    # Kök 3 harften kısa kalamaz
    assert len(light_stem("ayda")) >= 3


def test_keywords_tekrarsiz_ve_kisa_atilir():
    kws = keywords("Doktorlar ve doktor sayısı en çok kaç?")
    assert kws.count("doktor") == 1
    assert all(len(k) >= 3 for k in kws)
