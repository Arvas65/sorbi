"""API modu — gizlilik ve kota davranışı (Gemini uyumluluk katmanı).

Bu testlerin ikisi de bir vaadi koruyor:
1. "Veri makineden çıkmaz" bir docstring değil, çalıştırılabilir bir kural olmalı
2. Kota aşımı, modelin beceriksizliği gibi ölçülmemeli
"""
import pytest

from app import config, generator

# ------------------------------------------------------------------ gizlilik

BAGLAM = """TABLO doktor
KOLONLAR: doktor_id (INTEGER), ad (TEXT), unvan (TEXT)
ILISKILER: doktor.bolum_id -> bolum.bolum_id
DEĞERLER (bu kolonlarda GEÇEN TEK değerler bunlardır, filtrede aynen kullan):
  unvan = Prof. Dr. | Doç. Dr. | Uzm. Dr.
  ad = Kardiyoloji | Nöroloji

TABLO hasta
KOLONLAR: hasta_id (INTEGER), sehir (TEXT)
DEĞERLER (bu kolonlarda GEÇEN TEK değerler bunlardır, filtrede aynen kullan):
  sehir = İstanbul | Ankara | Bursa"""


def test_deger_bloklari_baglamdan_dusuruluyor():
    temiz = generator.mask_context(BAGLAM)
    for deger in ("Prof. Dr.", "Kardiyoloji", "İstanbul", "Bursa"):
        assert deger not in temiz, f"{deger!r} dış servise gidiyor"


def test_sema_metaverisi_korunuyor():
    """Tablo ve kolon adları metaveridir, veri değil — gitmeye devam etmeli."""
    temiz = generator.mask_context(BAGLAM)
    for parca in ("TABLO doktor", "KOLONLAR", "unvan (TEXT)", "ILISKILER", "TABLO hasta"):
        assert parca in temiz


def test_deger_blogu_yoksa_baglam_bozulmaz():
    sade = "TABLO bolum\nKOLONLAR: bolum_id (INTEGER), ad (TEXT)"
    assert generator.mask_context(sade) == sade


def test_bos_baglam_cokmez():
    assert generator.mask_context("") == ""
    assert generator.mask_context(None) is None


def test_api_cagrisinda_deger_gitmiyor(monkeypatch):
    """Uçtan uca: generate_api'nin gerçekten gönderdiği metni yakala."""
    gonderilen = {}

    def sahte(messages, deneme=4):
        gonderilen["metin"] = "\n".join(m["content"] for m in messages)
        return '{"sql": "SELECT 1", "guven": 1.0}'

    monkeypatch.setattr(generator, "_api_chat", sahte)
    generator.generate_api("Profesör unvanlı doktorlar kimler?", BAGLAM)
    for deger in ("Prof. Dr.", "İstanbul", "Kardiyoloji"):
        assert deger not in gonderilen["metin"]
    assert "TABLO doktor" in gonderilen["metin"]


def test_ornek_degerler_acikken_bile_gitmiyor(monkeypatch):
    """Vaadi koruyan şey bir ayarın hatırlanması OLMAMALI."""
    monkeypatch.setattr(config, "ORNEK_DEGERLER", True)
    assert "Prof. Dr." not in generator.mask_context(BAGLAM)


# ------------------------------------------------------------------ kota

class _Yanit:
    def __init__(self, kod, govde="", basliklar=None):
        self.status_code, self.text = kod, govde
        self.headers = basliklar or {}

    def json(self):
        return {"choices": [{"message": {"content": self.text}}]}


def test_429_sonrasi_yeniden_deneniyor(monkeypatch):
    cagri = {"n": 0}

    def post(*a, **k):
        cagri["n"] += 1
        if cagri["n"] < 3:
            return _Yanit(429, "rate limit")
        return _Yanit(200, '{"sql": "SELECT 1", "guven": 1.0}')

    monkeypatch.setattr(generator.requests, "post", post)
    monkeypatch.setattr(generator.time, "sleep", lambda s: None)
    assert "SELECT 1" in generator._api_chat([{"role": "user", "content": "x"}])
    assert cagri["n"] == 3


def test_kota_tukenirse_ayri_hata_turu(monkeypatch):
    monkeypatch.setattr(generator.requests, "post", lambda *a, **k: _Yanit(429, "quota"))
    monkeypatch.setattr(generator.time, "sleep", lambda s: None)
    with pytest.raises(generator.KotaHatasi):
        generator._api_chat([{"role": "user", "content": "x"}], deneme=2)


def test_kota_hatasi_llmerror_alt_turudur():
    """Var olan yakalama noktaları bozulmasın diye."""
    assert issubclass(generator.KotaHatasi, generator.LlmError)


def test_kota_yerele_duserek_gizlenmiyor(monkeypatch):
    """Düşseydik ölçüm 'api' diye başlayıp sessizce yerel modelle biterdi."""
    monkeypatch.setattr(config, "API_KEY", "x")
    monkeypatch.setattr(generator, "generate_api",
                        lambda *a, **k: (_ for _ in ()).throw(generator.KotaHatasi("kota")))
    monkeypatch.setattr(generator, "generate_local",
                        lambda *a, **k: {"sql": "SELECT 9", "guven": 1.0})
    with pytest.raises(generator.KotaHatasi):
        generator.generate("soru", "bağlam", mode="api")


def test_diger_api_hatasi_yerele_duser(monkeypatch):
    """Kota dışındaki hatalarda son-değer davranışı korunur."""
    monkeypatch.setattr(config, "API_KEY", "x")
    monkeypatch.setattr(generator, "generate_api",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bilinmeyen")))
    monkeypatch.setattr(generator, "generate_local",
                        lambda *a, **k: {"sql": "SELECT 9", "guven": 1.0})
    _s, mod = generator.generate("soru", "bağlam", mode="api")
    assert mod == "local"
