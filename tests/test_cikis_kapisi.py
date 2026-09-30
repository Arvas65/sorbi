"""Çıkış kapısı (ADR-10) — makineden dışarı giden LLM isteğinin tek denetimi.

En önemli iddia: izin yoksa ya da gövdede kişisel veri kalmışsa AĞA HİÇ İSTEK
ÇIKMAZ. Bu yüzden testler `requests.post`'u sayar; hata türüne bakmak yetmez.
"""
import os

import pytest

from app import config, generator
from app.baglanti.esleyici import _SISTEM as ESLEYICI_ISTEMI
from app.guvenlik import cikis_kapisi
from app.guvenlik.cikis_kapisi import GuvenlikEngeli, denetle, izin, kontrol

DEMO = f"sqlite:///{os.path.join(config.DEMO_DIZINI, 'hospital.db')}"
MUSTERI = "postgresql+psycopg2://salt_okur:x@hastane-replika:5432/hbys"
TCKN = "10000000146"


class _Yanit:
    status_code = 200
    ok = True
    headers: dict = {}
    text = ""

    def json(self):
        return {"choices": [{"message": {"content": '{"sql": "SELECT 1", "guven": 1}'}}]}


@pytest.fixture
def ag(monkeypatch):
    cagrilar = []

    def post(*a, **k):
        cagrilar.append(k.get("json"))
        return _Yanit()
    monkeypatch.setattr(generator.requests, "post", post)
    return cagrilar


def _mesaj(icerik):
    return [{"role": "user", "content": icerik}]


# ------------------------------------------------------------ izin

def test_izinsiz_cagri_aga_cikmaz(ag):
    with pytest.raises(GuvenlikEngeli, match="API izni yok"):
        generator._api_chat(_mesaj("kaç doktor var"))
    assert ag == []


def test_musteri_baglantisinda_izin_verilmez(ag):
    with izin(MUSTERI) as karar:
        assert karar.kilitlendi
        with pytest.raises(GuvenlikEngeli):
            generator._api_chat(_mesaj("kaç doktor var"))
    assert ag == []


def test_demo_baglantisinda_temiz_istek_gider(ag):
    with izin(DEMO):
        generator._api_chat(_mesaj("kaç doktor var"))
    assert len(ag) == 1


def test_izin_bloktan_cikinca_kapanir(ag):
    with izin(DEMO):
        pass
    with pytest.raises(GuvenlikEngeli):
        generator._api_chat(_mesaj("x"))


def test_izin_hata_sonrasi_da_kapanir(ag):
    with pytest.raises(RuntimeError, match="içeride"), izin(DEMO):
        raise RuntimeError("içeride patladı")
    with pytest.raises(GuvenlikEngeli):
        generator._api_chat(_mesaj("x"))


# ------------------------------------------------------------ gövde

@pytest.mark.parametrize("sizinti,tur", [
    (f"hasta {TCKN} kimdir", "TCKN"),
    ("IBAN TR33 0006 1005 1978 6457 8413 26", "IBAN"),
    ("mail a.kaya@ornek.com", "EPOSTA"),
    ("tel 0532 123 45 67", "TELEFON"),
])
def test_izinli_olsa_da_kisisel_veri_gitmez(ag, sizinti, tur):
    with izin(DEMO), pytest.raises(GuvenlikEngeli) as e:
        generator._api_chat(_mesaj(sizinti))
    assert ag == []
    assert tur in str(e.value)


def test_engel_iletisi_degeri_tasimaz(ag):
    """İleti log'a ve arayüze gider; içinde yakalanan değerin kendisi olmamalı."""
    with izin(DEMO), pytest.raises(GuvenlikEngeli) as e:
        generator._api_chat(_mesaj(f"hasta {TCKN}"))
    assert TCKN not in str(e.value)


def test_yasakli_sozluk_degeri_gitmez(ag):
    with izin(DEMO, yasakli_degerler=["Kardiyoloji"]), pytest.raises(GuvenlikEngeli, match="SOZLUK"):
        generator._api_chat(_mesaj("kardiyolojideki randevular"))
    assert ag == []


def test_kisa_yasakli_deger_kelime_icinde_alarm_vermez():
    with izin(DEMO, yasakli_degerler=["K"]):
        assert denetle(_mesaj("kaç kişi var")) == []
        assert denetle(_mesaj("cinsiyet K olan")) == ["SOZLUK_DEGERI"]


def test_cok_parcali_icerik_de_denetlenir():
    with izin(DEMO):
        m = [{"role": "user", "content": [{"type": "text", "text": f"no {TCKN}"}]}]
        with pytest.raises(GuvenlikEngeli):
            kontrol(m)


# --------------------------------------------- yanlış alarm yok (kapı açık kalsın)

def test_sistem_istemleri_kapidan_gecer():
    """Kendi istemlerimiz kapıyı tetiklerse kapı kapatılır — bu olmamalı."""
    with izin(DEMO):
        kontrol([{"role": "system", "content": generator.SYSTEM_PROMPT}])
        kontrol([{"role": "system", "content": ESLEYICI_ISTEMI}])


def test_maskelenmis_v3_baglami_kapidan_gecer():
    from tests.test_api_modu import BAGLAM
    with izin(DEMO):
        kontrol(_mesaj(generator._user_prompt(
            "Geçen ay kardiyolojide kaç randevu vardı?", generator.mask_context(BAGLAM))))


# ------------------------------------------------ v3 hattı: bulgu 2026-09-30

def test_v3_hatti_musteri_db_de_api_istese_de_yerelde_kosar(monkeypatch):
    """SORBI_MODE=api tanımlı bir makinede müşteri DB'si → üretim YEREL, not dolu."""
    from app import pipeline
    from app.akis.baglam import OturumBaglami

    kullanilan = {}

    def sahte_generate(q, ctx, mode=None):
        kullanilan["mod"] = mode
        return {"sql": "SELECT 1", "guven": 0.1, "aciklama": "x"}, mode

    class _Idx:
        known_tables = set()
        known_columns = set()

        def retrieve(self, q):
            return "TABLO t", []

    monkeypatch.setattr(config, "MODE", "api")
    monkeypatch.setattr(config, "API_KEY", "anahtar")
    monkeypatch.setattr(pipeline, "get_index", lambda b=None: _Idx())
    monkeypatch.setattr(pipeline.generator, "generate", sahte_generate)
    monkeypatch.setattr(pipeline.audit, "write", lambda *a, **k: None)

    ans = pipeline.ask("kaç hasta var", baglam=OturumBaglami(db_url=MUSTERI, lehce="postgres"))
    assert kullanilan["mod"] == "local"
    assert "ADR-5" in ans.mod_notu


def test_kapi_ayarla_kapatilamaz():
    """Kapıyı devre dışı bırakan bir config bayrağı yok ve olmamalı."""
    kaynak = open(cikis_kapisi.__file__, encoding="utf-8").read()
    assert "config." not in kaynak.split('"""', 2)[2]
