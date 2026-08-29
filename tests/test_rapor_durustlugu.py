"""Raporun kendi hakkında söylediği şeyler doğru mu.

Bu dosyadaki her test bir kanıt dosyasında gerçekten görülmüş bir yanlış
ifadeyi kilitler. Sayıların doğru olması yetmez; sayının yanına yazılan
HÜKÜM de ölçülmüş olmalıdır (CLAUDE.md § 3.4: "ölçülmemiş şey iddia edilmez").
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config  # noqa: E402
from eval.evaluate import _damga, _fark_satiri, g12_kapsam_disi, rapor_yaz  # noqa: E402

# --- 1. Yuvarlama yalanı (2026-08-23 kanıtı) -------------------------------
# accuracy-2026-08-23 raporu p50 için "+0.0 sn (gerileme)" yazdı. 2,26 -> 2,29
# farkı basılan hassasiyette sıfırdır; sıfır hakkında "gerileme" denemez.

def test_yuvarlamada_sifirlanan_fark_hukum_almaz():
    assert _fark_satiri(2.29, 2.26, "sn", yukselmesi_iyi=False) == "değişmedi"


def test_gercek_fark_hala_etiketlenir():
    s = _fark_satiri(4.81, 3.76, "sn", yukselmesi_iyi=False)
    assert "gerileme" in s and "+1.0" in s
    s = _fark_satiri(70.3, 56.4)
    assert "iyileşme" in s


# --- 2. G-12 kapsamı (BULGU-03) -------------------------------------------
# G-12 yerel çıkarım modunu tanımlar. api modunda ölçülen süre dış servisin
# altyapısıdır; sayı raporlanır, hüküm verilmez.

def test_g12_yerel_modda_hukum_verir():
    assert g12_kapsam_disi({"mod": "local"}) is None


def test_g12_api_modda_kapsam_disi():
    sebep = g12_kapsam_disi({"mod": "api"})
    assert sebep is not None and "yerel" in sebep


def test_gecikme_raporu_api_modda_karsilandi_yazmaz(tmp_path):
    ozet = _ornek_ozet(p50=2.29, p95=4.81, en_yavas=[12.36, 6.33, 5.67])
    damga = _damga_ile(mod="api", model="gemini-3.7-flash")
    _, gec = rapor_yaz(ozet, damga, str(tmp_path))
    metin = open(gec, encoding="utf-8").read()
    assert "KAPSAM DIŞI" in metin
    assert "KARŞILANDI" not in metin          # ne olumlu ne olumsuz hüküm
    assert "2.29" in metin and "4.81" in metin  # sayılar yerinde duruyor


def test_gecikme_raporu_yerel_modda_hukum_verir(tmp_path):
    ozet = _ornek_ozet(p50=21.7, p95=32.8, en_yavas=[40.0])
    damga = _damga_ile(mod="local", model="qwen2.5-coder:7b-instruct")
    _, gec = rapor_yaz(ozet, damga, str(tmp_path))
    metin = open(gec, encoding="utf-8").read()
    assert "KARŞILANMADI" in metin and "KAPSAM DIŞI" not in metin


def test_hedefi_asan_tek_soru_gizlenmez(tmp_path):
    """p95 hedefin altında ama bir soru 12,4 sn — "en geç" metni ihlal."""
    ozet = _ornek_ozet(p50=2.29, p95=4.81, en_yavas=[12.36, 6.33])
    damga = _damga_ile(mod="local")
    _, gec = rapor_yaz(ozet, damga, str(tmp_path))
    metin = open(gec, encoding="utf-8").read()
    assert "12.36" in metin and "en geç" in metin


# --- 3. Damga uygulanmamış ayarı uygulanmış gibi göstermez ----------------
# Eskiden `generate_api` isteği yalnız `temperature` taşıyordu ama damga her
# koşumda `seed=42, num_ctx=8192` yazıyordu (BULGU-08). Artık `seed` gerçekten
# gönderiliyor VE damga metni koddan türetiliyor: isteğin alan listesi
# değişirse damga kendiliğinden düzelir.

def test_damga_metni_koddan_tureniyor():
    """Damga metni elle yazılmaz; üreticinin GÖZLENEN durumundan gelir."""
    from app import generator
    assert _damga("api")["belirlenim"] == generator.belirlenim_durumu()


def test_api_istegi_seed_gonderiyor(monkeypatch):
    from app import generator
    monkeypatch.setattr(generator, "_seed_kabul", None)
    monkeypatch.setattr(config, "API_SEED_GONDER", None)
    govde = generator._api_govdesi([{"role": "user", "content": "x"}])
    assert govde["seed"] == config.SEED
    assert set(generator.API_BELIRLENIM_ALANLARI) <= set(govde)


def test_uc_nokta_reddettiyse_seed_bir_daha_gonderilmiyor(monkeypatch):
    """BULGU-17: Gemini'nin OpenAI katmanı `seed`'i tanımıyor —
    `HTTP 400 Unknown name "seed"`. Her soruda bir kayıp istek yapmanın
    anlamı yok; ret bir kez öğrenilir ve oturum boyunca hatırlanır."""
    from app import generator
    monkeypatch.setattr(generator, "_seed_kabul", False)
    monkeypatch.setattr(config, "API_SEED_GONDER", None)
    assert "seed" not in generator._api_govdesi([{"role": "user", "content": "x"}])


def test_seed_reddi_dar_taniniyor():
    """Her 400'ü seed'e yormak, gerçek bir istem hatasını sessizce yutardı."""
    from app import generator
    assert generator._seed_reddi_mi('Unknown name "seed": Cannot find field.')
    assert not generator._seed_reddi_mi("Invalid model name")
    assert not generator._seed_reddi_mi("context length exceeded")


def test_api_damgasi_belirlenim_iddia_etmiyor(monkeypatch):
    """Göndermek uygulanmış olmak değildir; damga hüküm vermemeli."""
    from app import generator
    monkeypatch.setattr(generator, "_seed_kabul", True)
    monkeypatch.setattr(config, "API_SEED_GONDER", None)
    assert "doğrulanmadı" in _damga("api")["belirlenim"]


def test_uc_nokta_tanimiyorsa_damga_bunu_yaziyor(monkeypatch):
    """ADR-5 Ö-7 için asıl cümle bu: belirlenim doğrulanmamış DEĞİL,
    bu uç noktada MÜMKÜN DEĞİL."""
    from app import generator
    monkeypatch.setattr(generator, "_seed_kabul", False)
    monkeypatch.setattr(config, "API_SEED_GONDER", None)
    metin = _damga("api")["belirlenim"]
    assert "UYGULANAMIYOR" in metin and "mümkün değil" in metin


def test_damga_yerel_modda_gercek_degerleri_yaziyor():
    d = _damga("local")
    assert f"seed={config.SEED}" in d["belirlenim"]
    assert f"num_ctx={config.NUM_CTX}" in d["belirlenim"]


# --- 4. Rapor başlığı gerçek soru sayısını yazar --------------------------
# Başlık "50 soruluk" diye sabitti; ölçüm 101 soruluk koşuyordu.

def test_baslik_gercek_soru_sayisini_yazar(tmp_path):
    ozet = _ornek_ozet()
    damga = _damga_ile(mod="api")
    acc, _ = rapor_yaz(ozet, damga, str(tmp_path))
    metin = open(acc, encoding="utf-8").read()
    assert re.search(r"G-11 — 101 soruluk", metin)
    assert "50 soruluk" not in metin


# --- yardımcı --------------------------------------------------------------

def _damga_ile(mod="api", model="m"):
    d = _damga(mod)
    d["model"] = model
    return d


def _ornek_ozet(p50=2.29, p95=4.81, en_yavas=None):
    en_yavas = en_yavas or [3.0]
    return {
        "n": 101, "dogru": 71, "accuracy": 71 / 101,
        "p50_s": p50, "p95_s": p95,
        "sessiz_yanlis": 30, "sessiz_yanlis_orani": 30 / 101,
        "yanlislarda_sessiz_pay": 1.0,
        "yakalanan_hata": 0, "reddedilen": 0, "onarim_sayisi": 0,
        "mod_dagilimi": {},
        "kirilim": {"zorluk": {"kolay": {"dogru": 31, "toplam": 35}},
                    "join": {0: {"dogru": 41, "toplam": 54}}},
        "asama_dagilimi": {"esit": 71, "sonuc_farkli": 30},
        "guven": {},
        "en_yavas_5": [{"sure_s": s, "asama": "esit", "soru": f"soru {i}"}
                       for i, s in enumerate(en_yavas)],
    }
