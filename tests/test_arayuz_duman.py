"""Arayüz duman testi — ürün, kullanıcının kullandığı yerden sınanır (BULGU-46).

BULGU-46: 2026-08-29'dan 09-30'a kadar ana sayfa ilk sorudan sonra çöküyordu
(denetim izine eklenen sekizinci kolon, arayüzde yedi kolon adı). 693 testin
hiçbiri yakalamadı, çünkü hiçbiri arayüzü çalıştırmıyordu.

LLM taklit edilir (test setinin altın SQL'ini döndürür); gerisi gerçektir:
doğrulama, yürütme, B-7, denetim izi ve Streamlit'in kendisi. Denetim izi ve
kullanıcı deposu geçici dizindedir; depoya hiçbir şey yazılmaz.
"""
import json
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from app import audit, auth, config, generator

KOK = pathlib.Path(__file__).resolve().parent.parent
ALTIN = {json.loads(s)["soru"]: json.loads(s)["gold_sql"]
         for s in (KOK / "eval" / "test_set_tr.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()}
SORU = "Hastanede kaç doktor çalışıyor?"


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setattr(config, "MODE", "local")
    monkeypatch.setattr(auth, "kullanicilar", lambda: {"duman": {"rol": "yonetici"}})

    def sahte(q, ctx, mode=None):
        sql = ALTIN.get(q.split("\n[TARIH")[0])
        return {"sql": sql or "SELECT 1", "guven": 0.9, "aciklama": "taklit"}, "local"
    monkeypatch.setattr(generator, "generate", sahte)
    monkeypatch.setattr(generator, "repair", lambda q, c, *a, **k: sahte(q, c))


def _ac(yol):
    at = AppTest.from_file(str(KOK / yol), default_timeout=60)
    at.session_state["kullanici"] = "duman"
    at.session_state["rol"] = "yonetici"
    at.run()
    return at


def _hatalar(at):
    return [str(e.value)[:300] for e in at.exception]


@pytest.mark.parametrize("yol", ["ui/streamlit_app.py", "ui/pages/1_Dashboard.py",
                                 "ui/pages/2_Baglanti.py", "ui/pages/3_Kullanicilar.py"])
def test_sayfa_acilir(ortam, yol):
    assert not _hatalar(_ac(yol))


def test_soru_sor_cevap_al_ve_sayfa_yeniden_cizilir(ortam):
    """Kullanıcının asıl işi. Üçüncü adım BULGU-46'nın tam ifadesi."""
    at = _ac("ui/streamlit_app.py")
    at.text_input[0].input(SORU)
    next(b for b in at.button if b.label == "Sor").click()
    at.run()
    assert not _hatalar(at)
    assert len(at.dataframe) + len(at.table) > 0, "sonuç tablosu gösterilmedi"
    assert any("SELECT" in c.value.upper() for c in at.code), "üretilen SQL gösterilmedi (G-02)"

    at.run()                                  # kayıt artık var: geçmiş sekmesi dolu çizilir
    assert not _hatalar(at)


def test_denetim_kolon_adlari_kayitla_ayni_uzunlukta(ortam):
    audit.write("duman", "soru", "SELECT 1", "BASARILI", 1, "local", 0.1)
    (satir,) = audit.recent(1)
    assert len(satir) == len(audit.KAYIT_KOLONLARI)
