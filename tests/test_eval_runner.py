"""Eval koşucusunun LLM'siz testleri (v3 SPEC A-1).

Koşucu artık üreticiyi dışarıdan alıyor; bu sayede gerçek bir LLM servisi olmadan
"doğru cevap", "yanlış cevap", "öz-onarım", "halüsinasyon" ve "üretim hatası"
yollarının hepsi test edilebiliyor. Önceden bu mümkün değildi: `evaluate.py`
generator'ı `globals()` ile modüle enjekte ediyordu.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config  # noqa: E402
from app.schema_rag import ContextIndex  # noqa: E402
from eval import evaluate  # noqa: E402

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "demo", "hospital.db")


# --------------------------------------------------------------- sahte üreticiler

class SahteUretici:
    """Sırayla verilen cevapları döndürür. generate ilkini, repair sonrakini verir."""

    def __init__(self, *cevaplar, patlat=None):
        self.cevaplar = list(cevaplar)
        self.patlat = patlat
        self.cagri = {"generate": 0, "repair": 0}

    def _sonraki(self):
        if self.cevaplar:
            return self.cevaplar.pop(0)
        return {"sql": "", "guven": 0.0, "aciklama": "cevap kalmadı"}

    def generate(self, question, context, mode=None):
        self.cagri["generate"] += 1
        if self.patlat == "generate":
            raise RuntimeError("model servisine ulaşılamadı")
        return self._sonraki(), "sahte"

    def repair(self, question, context, bad_sql, error, mode=None):
        self.cagri["repair"] += 1
        if self.patlat == "repair":
            raise RuntimeError("onarım sırasında patladı")
        return self._sonraki(), "sahte"


def _cevap(sql, guven=0.9):
    return {"sql": sql, "guven": guven, "aciklama": ""}


@pytest.fixture(scope="module")
def idx():
    if not os.path.exists(DB):
        pytest.skip("demo/hospital.db yok — önce: python demo/seed_data.py")
    config.DB_URL = f"sqlite:///{DB}"
    return ContextIndex(config.DB_URL)


@pytest.fixture(scope="module")
def items():
    return evaluate.yukle_testset(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "eval", "test_set_tr.jsonl"))


# --------------------------------------------------------------- run_one yolları

def test_gold_sql_ile_ayni_sonuc_dogru_sayilir(idx, items):
    """Üretici gold SQL'in aynısını verirse sonuç kümeleri eşit olmalı."""
    item = items[0]
    uretici = SahteUretici(_cevap(item["gold_sql"]))
    rec = evaluate.run_one(item, idx, "local", uretici)
    assert rec["dogru"] is True
    assert rec["asama"] == "esit"
    assert uretici.cagri["repair"] == 0
    assert "sure_s" in rec


def test_farkli_sonuc_yanlis_sayilir(idx, items):
    """items[0] = 'Hastanede kaç doktor çalışıyor?' — hasta sayısı farklı bir cevaptır."""
    uretici = SahteUretici(_cevap("SELECT COUNT(*) FROM hasta"))
    rec = evaluate.run_one(items[0], idx, "local", uretici)
    assert rec["dogru"] is False
    assert rec["asama"] == "sonuc_farkli"


def test_olmayan_tablo_dogrulamada_reddedilir_ve_onarim_denenir(idx, items):
    """Halüsinasyon: ilk cevap uydurma tablo, onarım doğrusunu verir → doğru sayılır."""
    item = items[0]
    uretici = SahteUretici(_cevap("SELECT * FROM uydurma_tablo"), _cevap(item["gold_sql"]))
    rec = evaluate.run_one(item, idx, "local", uretici)
    assert uretici.cagri["repair"] == 1
    assert rec["onarim"] is True
    assert rec["dogru"] is True


def test_onarim_da_basarisizsa_dogrulama_reddi(idx, items):
    uretici = SahteUretici(_cevap("SELECT * FROM uydurma_tablo"),
                           _cevap("SELECT * FROM hala_uydurma"))
    rec = evaluate.run_one(items[0], idx, "local", uretici)
    assert rec["dogru"] is False
    assert rec["asama"].startswith("dogrulama_reddi")


def test_yazma_sorgusu_reddedilir(idx, items):
    """G-18: eval yolundan da SELECT dışı sorgu geçemez."""
    uretici = SahteUretici(_cevap("DELETE FROM hasta"), _cevap("DROP TABLE hasta"))
    rec = evaluate.run_one(items[0], idx, "local", uretici)
    assert rec["dogru"] is False
    assert rec["asama"].startswith("dogrulama_reddi")


def test_uretim_patlarsa_kosucu_cokmez(idx, items):
    uretici = SahteUretici(patlat="generate")
    rec = evaluate.run_one(items[0], idx, "local", uretici)
    assert rec["dogru"] is False
    assert rec["asama"].startswith("uretim_hatasi")
    assert "sure_s" in rec       # süre her yolda kaydedilmeli (G-12 ölçümü için)


def test_onarim_patlarsa_kosucu_cokmez(idx, items):
    uretici = SahteUretici(_cevap("SELECT * FROM uydurma_tablo"), patlat="repair")
    rec = evaluate.run_one(items[0], idx, "local", uretici)
    assert rec["asama"].startswith("onarim_hatasi")


# --------------------------------------------------------------- özet ve rapor

def test_ozetle_accuracy_ve_gecikme_hesaplar():
    results = [
        {"dogru": True, "zorluk": "kolay", "join": 0, "sure_s": 1.0, "asama": "esit", "onarim": False},
        {"dogru": True, "zorluk": "kolay", "join": 1, "sure_s": 2.0, "asama": "esit", "onarim": True},
        {"dogru": False, "zorluk": "zor", "join": 2, "sure_s": 9.0, "asama": "sonuc_farkli", "onarim": False},
        {"dogru": False, "zorluk": "zor", "join": 2, "sure_s": 30.0,
         "asama": "calisma_hatasi: ZAMAN_ASIMI", "onarim": False},
    ]
    o = evaluate.ozetle(results)
    assert o["n"] == 4
    assert o["dogru"] == 2
    assert o["accuracy"] == 0.5
    assert o["onarim_sayisi"] == 1
    assert o["p50_s"] == pytest.approx(5.5)
    assert o["p95_s"] == 30.0
    assert o["kirilim"]["zorluk"]["kolay"] == {"dogru": 2, "toplam": 2}
    assert o["kirilim"]["zorluk"]["zor"] == {"dogru": 0, "toplam": 2}
    assert o["asama_dagilimi"]["calisma_hatasi"] == 1
    assert len(o["en_yavas_5"]) == 4
    assert o["en_yavas_5"][0]["sure_s"] == 30.0


def test_rapor_yazilir_ve_damga_icerir(tmp_path):
    results = [{"dogru": True, "zorluk": "kolay", "join": 0, "sure_s": 1.0,
                "asama": "esit", "soru": "kaç doktor var", "onarim": False}]
    o = evaluate.ozetle(results)
    damga = {"tarih": "2026-08-11", "commit": "abc1234", "model": "llama3.2:3b",
             "mod": "local", "db_url": "sqlite:///x", "python": "3.11.0", "platform": "Linux x86_64"}
    acc, gec = evaluate.rapor_yaz(o, damga, str(tmp_path))
    metin = open(acc, encoding="utf-8").read()
    assert "100.0%" in metin
    assert "abc1234" in metin and "llama3.2:3b" in metin      # damga zorunlu
    assert "KARŞILANDI" in metin
    metin_g = open(gec, encoding="utf-8").read()
    assert "p50" in metin_g and "p95" in metin_g


def test_hedef_altinda_kalinca_adr2_uyarisi_yazilir(tmp_path):
    results = [{"dogru": False, "zorluk": "zor", "join": 2, "sure_s": 3.0,
                "asama": "sonuc_farkli", "soru": "x", "onarim": False}]
    o = evaluate.ozetle(results)
    damga = {"tarih": "2026-08-11", "commit": "abc1234", "model": "m",
             "mod": "local", "db_url": "d", "python": "3.11.0", "platform": "Linux"}
    acc, _ = evaluate.rapor_yaz(o, damga, str(tmp_path))
    metin = open(acc, encoding="utf-8").read()
    assert "KARŞILANMADI" in metin
    assert "ADR-2" in metin       # hedef altındaysa karar tetikleyicisi görünür olmalı


# --------------------------------------------------------------- CLI

def test_gold_only_llm_olmadan_kosar(tmp_path, capsys):
    """CI'ın koştuğu yol: hiçbir LLM içe aktarılmadan test seti sağlığı ölçülür."""
    if not os.path.exists(DB):
        pytest.skip("demo/hospital.db yok")
    kod = evaluate.main(["--db", DB, "--gold-only"])
    cikti = capsys.readouterr().out
    assert kod == 0
    assert "GOLD SQL SAĞLIĞI" in cikti


def test_eksik_bagimlilikta_anlasilir_mesaj(capsys, monkeypatch, tmp_path):
    """Ham traceback yerine ne yapılacağını söyleyen mesaj (Nielsen 9).

    Saha kaydı: `python eval/evaluate.py --doctor` sanal ortam etkin değilken
    çıplak ModuleNotFoundError veriyordu.
    """
    monkeypatch.setattr(evaluate, "KOK", str(tmp_path))
    (tmp_path / ".venv").mkdir()                       # venv var...
    monkeypatch.setattr(sys, "prefix", "/usr")         # ...ama etkin değil
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    with pytest.raises(SystemExit) as cikis:
        evaluate._bagimlilik_hatasi(ModuleNotFoundError("No module named 'sqlalchemy'",
                                                        name="sqlalchemy"))
    assert cikis.value.code == 2
    hata = capsys.readouterr().err
    assert "sqlalchemy" in hata
    assert "etkin değil" in hata                       # teşhis
    assert "activate" in hata                          # ne yapmalı
    assert "requirements" in hata                      # kurulum yolu
    assert "Traceback" not in hata


def test_testset_yuklenir_ve_alanlari_tam(items):
    assert len(items) >= 50
    for it in items:
        assert {"id", "soru", "gold_sql", "zorluk", "join"} <= set(it)
        assert json.dumps(it)  # serileştirilebilir olmalı


# --------------------------------------------------- B-7: sessiz yanlış metriği

def _r(dogru, asama, sure=1.0, zorluk="kolay", join=0):
    return {"dogru": dogru, "asama": asama, "sure_s": sure, "zorluk": zorluk,
            "join": join, "onarim": False, "soru": "x"}


def test_sessiz_yanlis_ayri_olculuyor():
    """Yakalanan hata ile sessiz yanlış aynı şey değildir — riskleri farklıdır."""
    o = evaluate.ozetle([
        _r(True, "esit"),
        _r(False, "sonuc_farkli"),                       # sessiz
        _r(False, "sonuc_farkli"),                       # sessiz
        _r(False, "dogrulama_reddi: olmayan kolon"),     # yakalandı
        _r(False, "calisma_hatasi: ZAMAN_ASIMI"),        # yakalandı
    ])
    assert o["sessiz_yanlis"] == 2
    assert o["yakalanan_hata"] == 2
    assert o["sessiz_yanlis_orani"] == pytest.approx(0.4)
    assert o["yanlislarda_sessiz_pay"] == pytest.approx(0.5)


def test_hicbir_yanlis_yoksa_sessiz_pay_sifir():
    o = evaluate.ozetle([_r(True, "esit"), _r(True, "esit")])
    assert o["sessiz_yanlis"] == 0
    assert o["yanlislarda_sessiz_pay"] == 0.0     # sıfıra bölme olmamalı


def test_baseline_dagilimi_yeniden_uretiliyor():
    """2026-08-16 ölçümü: 15 doğru, 22 sessiz yanlış, 13 yakalanan."""
    kayitlar = ([_r(True, "esit")] * 15 + [_r(False, "sonuc_farkli")] * 22
                + [_r(False, "dogrulama_reddi: x")] * 12 + [_r(False, "calisma_hatasi: x")])
    o = evaluate.ozetle(kayitlar)
    assert o["accuracy"] == pytest.approx(0.30)
    assert o["sessiz_yanlis"] == 22
    assert o["yakalanan_hata"] == 13
    assert o["yanlislarda_sessiz_pay"] == pytest.approx(22 / 35)


def test_onceki_olcum_okunuyor_ve_rapora_giriyor(tmp_path):
    onceki_json = tmp_path / "results.json"
    onceki_json.write_text(json.dumps({
        "damga": {"tarih": "2026-08-16", "model": "llama3.2:3b", "commit": "abc1234"},
        "ozet": {"accuracy": 0.30, "n": 50, "p50_s": 23.8, "p95_s": 46.3, "sessiz_yanlis": 22},
    }), encoding="utf-8")
    onceki = evaluate.onceki_olcum(str(onceki_json))
    assert onceki and onceki["accuracy"] == 0.30

    o = evaluate.ozetle([_r(True, "esit")] * 30 + [_r(False, "sonuc_farkli")] * 20)
    damga = {"tarih": "2026-08-17", "commit": "def5678", "model": "llama3.2:3b",
             "mod": "local", "db_url": "d", "python": "3.13", "platform": "Windows"}
    acc, _ = evaluate.rapor_yaz(o, damga, str(tmp_path), onceki)
    metin = open(acc, encoding="utf-8").read()
    assert "Önceki ölçümle karşılaştırma" in metin
    assert "%30.0" in metin and "%60.0" in metin
    assert "iyileşme" in metin
    assert "Sessiz yanlış" in metin


def test_onceki_olcum_yoksa_karsilastirma_bolumu_cikmaz(tmp_path):
    assert evaluate.onceki_olcum(str(tmp_path / "yok.json")) is None
    o = evaluate.ozetle([_r(True, "esit")])
    damga = {"tarih": "2026-08-17", "commit": "x", "model": "m", "mod": "local",
             "db_url": "d", "python": "3.13", "platform": "L"}
    acc, _ = evaluate.rapor_yaz(o, damga, str(tmp_path), None)
    assert "Önceki ölçümle karşılaştırma" not in open(acc, encoding="utf-8").read()


def test_farkli_soru_sayisinda_karsilastirma_yapilmaz(tmp_path):
    """Test seti 50'den 101'e çıktı. Yüzdeleri karşılaştırmak, set büyütmesini
    bir gerileme gibi gösterirdi — cetvel değişince karşılaştırma susmalı."""
    onceki = {"accuracy": 0.68, "n": 50, "p50_s": 14.8, "p95_s": 21.7,
              "sessiz_yanlis": 14, "damga": {"tarih": "2026-08-16", "model": "m", "commit": "c"}}
    o = evaluate.ozetle([_r(True, "esit")] * 60 + [_r(False, "sonuc_farkli")] * 41)
    damga = {"tarih": "2026-08-17", "commit": "x", "model": "m", "mod": "local",
             "db_url": "d", "python": "3.13", "platform": "W"}
    acc, _ = evaluate.rapor_yaz(o, damga, str(tmp_path), onceki)
    metin = open(acc, encoding="utf-8").read()
    assert "Karşılaştırma yapılmadı" in metin
    assert "iyileşme" not in metin and "gerileme" not in metin


# ------------------------------------------------------- güven kontrolü karnesi

def _rb(dogru, asama, bayraklar=()):
    r = _r(dogru, asama)
    r["bayraklar"] = list(bayraklar)
    return r


def test_guven_karnesi_yakalama_ve_yanlis_alarmi_ayirir():
    """İki sayı ters yönde çeker; ikisi de aynı raporda durmalı."""
    o = evaluate.ozetle([
        _rb(False, "sonuc_farkli", ["bos_sonuc"]),        # yakalanan sessiz yanlış
        _rb(False, "sonuc_farkli", []),                   # kaçırılan
        _rb(True, "esit", ["filtresiz"]),                 # gereksiz bayrak
        _rb(True, "esit", []),                            # temiz
        _rb(False, "dogrulama_reddi: x", []),             # evrene GİRMEZ
    ])
    g = o["guven"]
    assert g["evren"] == 4                                # reddedilen sayılmaz
    assert g["yakalanan"] == 1 and g["sessiz_yanlis"] == 2
    assert g["yakalama_orani"] == pytest.approx(0.5)
    assert g["yanlis_alarm"] == 1 and g["dogru_cevap"] == 2
    assert g["yanlis_alarm_orani"] == pytest.approx(0.5)
    assert g["isabet"] == pytest.approx(0.5)


def test_kapali_kontrol_karneye_girmez(monkeypatch):
    """Üretimde kapalı bir kontrolün bayrağı manşet sayıyı şişirmemeli."""
    monkeypatch.setattr(evaluate.config, "GUVEN_KAPALI", {"sema_ortusmez"})
    o = evaluate.ozetle([
        _rb(False, "sonuc_farkli", ["sema_ortusmez"]),
        _rb(True, "esit", ["sema_ortusmez"]),
    ])
    g = o["guven"]
    assert g["yakalanan"] == 0 and g["yanlis_alarm"] == 0
    assert g["kodlar"]["sema_ortusmez"]["kapali"] is True


def test_guven_karnesi_bos_evrende_cokmez():
    o = evaluate.ozetle([_r(False, "dogrulama_reddi: x")])
    assert o["guven"]["evren"] == 0
    assert o["guven"]["yakalama_orani"] == 0.0


# ------------------------------------------------- İP-23: referans günü koruması

def test_farkli_referans_gununde_karsilastirma_reddedilir():
    """13 soru zamana bağlı; farklı güne sabitlenmiş iki koşum farklı cetveldir."""
    onceki = {"accuracy": 0.62, "n": 101, "olcum_gunu": "2026-08-16"}
    ozet = {"accuracy": 0.70, "n": 101}
    engel = evaluate.karsilastirilamaz(onceki, ozet, {"olcum_gunu": "2026-09-01"})
    assert engel and "2026-08-16" in engel and "2026-09-01" in engel


def test_ayni_referans_gununde_karsilastirma_yapilir():
    onceki = {"accuracy": 0.62, "n": 101, "olcum_gunu": "2026-08-16"}
    ozet = {"accuracy": 0.70, "n": 101}
    assert evaluate.karsilastirilamaz(onceki, ozet, {"olcum_gunu": "2026-08-16"}) is None


def test_ip23_oncesi_kosumla_karsilastirma_reddedilir():
    """Referans günü kayıtlı olmayan koşum gerçek takvimle alınmıştır."""
    onceki = {"accuracy": 0.62, "n": 101}          # damgada olcum_gunu yok
    ozet = {"accuracy": 0.70, "n": 101}
    engel = evaluate.karsilastirilamaz(onceki, ozet, {"olcum_gunu": "2026-08-16"})
    assert engel and "kayıtlı değil" in engel


def test_soru_sayisi_farkiysa_gun_ayni_olsa_da_reddedilir():
    onceki = {"accuracy": 0.68, "n": 50, "olcum_gunu": "2026-08-16"}
    ozet = {"accuracy": 0.62, "n": 101}
    engel = evaluate.karsilastirilamaz(onceki, ozet, {"olcum_gunu": "2026-08-16"})
    assert engel and "50" in engel


def test_damga_olcum_gununu_tasir():
    """Damga koşumun gerçek gününü DE sorguların gördüğü günü DE taşımalı."""
    from eval.tarih_sabitle import olcum_gunu
    d = evaluate._damga("local")
    assert d["olcum_gunu"] == olcum_gunu()
    assert len(d["olcum_gunu"]) == 10


def test_uretim_ayari_degisince_karsilastirma_reddedilir():
    """Kural `olcum-al` skill'inde yazılıydı ama kod yalnız n ve günü denetliyordu.

    2026-08-22 koşumunda num_ctx 4096'dan 8192'ye çıkmıştı; referans günü de
    değişmeseydi 6 puanlık fark gerçek bir gerileme gibi raporlanacaktı.
    """
    ortak = {"olcum_gunu": "2026-07-23", "model": "qwen2.5-coder:7b-instruct",
             "temperature": 0.0, "seed": 42, "num_ctx": 4096, "ornek_degerler": True}
    onceki = {"accuracy": 0.62, "n": 101, "olcum_gunu": "2026-07-23", "damga": ortak}
    ozet = {"accuracy": 0.56, "n": 101}
    yeni_damga = {**ortak, "num_ctx": 8192}
    engel = evaluate.karsilastirilamaz(onceki, ozet, yeni_damga)
    assert engel and "num_ctx" in engel


def test_model_degisince_karsilastirma_reddedilir():
    ortak = {"olcum_gunu": "2026-07-23", "model": "llama3.2:3b", "num_ctx": 8192}
    onceki = {"accuracy": 0.38, "n": 101, "olcum_gunu": "2026-07-23", "damga": ortak}
    ozet = {"accuracy": 0.62, "n": 101}
    engel = evaluate.karsilastirilamaz(
        onceki, ozet, {**ortak, "model": "qwen2.5-coder:7b-instruct"})
    assert engel and "model" in engel


def test_tum_ayarlar_ayniysa_karsilastirma_yapilir():
    ortak = {"olcum_gunu": "2026-07-23", "model": "qwen2.5-coder:7b-instruct",
             "temperature": 0.0, "seed": 42, "num_ctx": 8192, "ornek_degerler": True}
    onceki = {"accuracy": 0.56, "n": 101, "olcum_gunu": "2026-07-23", "damga": ortak}
    assert evaluate.karsilastirilamaz(onceki, {"accuracy": 0.60, "n": 101}, ortak) is None


def test_eski_kosumda_damga_yoksa_ayar_denetimi_engel_olmaz():
    """İP-23 öncesi koşumlar zaten referans günü yüzünden reddediliyor;
    eksik damga ayrı bir engel üretmemeli."""
    onceki = {"accuracy": 0.62, "n": 101, "olcum_gunu": "2026-07-23"}
    ortak = {"olcum_gunu": "2026-07-23", "num_ctx": 8192}
    assert evaluate.karsilastirilamaz(onceki, {"accuracy": 0.6, "n": 101}, ortak) is None


def test_kirli_calisma_agaci_damgada_gorunur(monkeypatch):
    """Commit hash'i koşulan kodu göstermiyorsa damga bunu söylemeli."""
    monkeypatch.setattr(evaluate, "_calisma_agaci_kirli", lambda: True)
    monkeypatch.setattr(evaluate, "_commit_hash", lambda: "abc1234")
    assert "islenmemis" in evaluate._damga("local")["commit"]


def test_temiz_agacta_damga_sade_kalir(monkeypatch):
    monkeypatch.setattr(evaluate, "_calisma_agaci_kirli", lambda: False)
    monkeypatch.setattr(evaluate, "_commit_hash", lambda: "abc1234")
    assert evaluate._damga("local")["commit"] == "abc1234"


# ------------------------------------------------- kota aşımı ayrı sayılır

def test_kota_asimi_dogruluk_kaybi_gibi_sayilmaz():
    """Ücretsiz katmanda 429 alan sorular cevaplanmadı — yanlış cevaplanmadı."""
    o = evaluate.ozetle(
        [_r(True, "esit")] * 30
        + [_r(False, "sonuc_farkli")] * 10
        + [_r(False, "kota_asildi: rate limit")] * 60)
    assert o["kota_asildi"] == 60
    assert o["olculebilen"] == 40
    assert o["accuracy"] == pytest.approx(0.30)              # ham sayı
    assert o["accuracy_olculebilen"] == pytest.approx(0.75)  # ölçülebilen üzerinden


def test_kota_yoksa_iki_sayi_ayni():
    o = evaluate.ozetle([_r(True, "esit")] * 3 + [_r(False, "sonuc_farkli")])
    assert o["kota_asildi"] == 0
    assert o["accuracy"] == o["accuracy_olculebilen"]


def test_kota_uyarisi_raporda_gorunur():
    o = evaluate.ozetle([_r(True, "esit")] * 2 + [_r(False, "kota_asildi: x")] * 2)
    metin = evaluate._kota_uyarisi(o)
    assert "2 soru kota" in metin and "KULLANILAMAZ" in metin


def test_kota_yokken_uyari_basilmaz():
    assert evaluate._kota_uyarisi(evaluate.ozetle([_r(True, "esit")])) == ""
