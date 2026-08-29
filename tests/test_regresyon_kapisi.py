"""BULGU-09/10: regresyon kapısı ham puan farkına değil eşli karara bağlı.

Ölçülen olgu (2026-08-22 ↔ 2026-08-23, aynı kod, aynı ayarlar, api modu):
**7 soru yön değiştirdi**, McNemar p = 1,000, net fark −1 soru. SPEC A-4'ün
"3 puandan fazla düşerse CI kırmızı" kuralı bu gürültü tabanının altındaydı:
saf gürültüde |net| ≥ 3 soru çıkma olasılığı yaklaşık **%45**.

Bir kapı hiçbir şey olmadan ateşlemeye başladığında kapatılır. Bu dosya yeni
kuralın iki yönünü de kilitliyor: gürültü kapıyı AÇAMAZ, gerçek gerileme AÇAR.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.evaluate import (  # noqa: E402
    _mcnemar_p,
    onceki_olcum,
    regresyon_karari,
    regresyon_satiri,
)


def _onceki(dogrular: dict) -> dict:
    return {"sorular": {str(k): v for k, v in dogrular.items()}}


def _sonuclar(dogrular: dict) -> list:
    return [{"id": k, "dogru": v} for k, v in dogrular.items()]


# --------------------------------------------------------------- McNemar

def test_mcnemar_simetrik_degisim_anlamsiz():
    """4 bozuldu, 3 düzeldi — net −1. Bu bir fark değildir."""
    assert _mcnemar_p(4, 3) == 1.0


def test_mcnemar_hic_degisim_yoksa_bir():
    assert _mcnemar_p(0, 0) == 1.0


def test_mcnemar_tek_yonlu_degisim_anlamli():
    """10 bozuldu, 0 düzeldi — yazı-tura ile açıklanamaz."""
    assert _mcnemar_p(10, 0) < 0.01


def test_mcnemar_bilinen_deger():
    """b=8, c=1: iki yönlü tam olasılık = 2 * (C(9,0)+C(9,1)) / 2^9."""
    assert abs(_mcnemar_p(8, 1) - 2 * (1 + 9) / 512) < 1e-12


# --------------------------------------------------- kapının kendisi

def test_olculen_gurultu_kapiyi_acmiyor():
    """08-22 ↔ 08-23 koşumlarının gerçek şekli: 4 bozuldu, 3 düzeldi."""
    eski = {i: True for i in range(1, 73)}
    eski.update({i: False for i in range(73, 102)})
    eski[100] = True                     # 08-22'de doğruydu
    eski[85] = False                     # 08-22'de yanlıştı
    yeni = dict(eski)
    for i in (28, 39, 40, 100):          # doğru → yanlış
        yeni[i] = False
    for i in (11, 36, 85):               # yanlış → doğru
        yeni[i] = True
    for i in (11, 36):
        eski[i] = False
    k = regresyon_karari(_onceki(eski), _sonuclar(yeni))
    assert k["bozulan"] == 4 and k["duzelen"] == 3
    assert k["karar"] == "FARK_YOK"
    assert k["p"] == 1.0


def test_gercek_gerileme_kapiyi_aciyor():
    eski = {i: True for i in range(1, 102)}
    yeni = dict(eski)
    for i in range(1, 13):               # 12 soru bozuldu, hiçbiri düzelmedi
        yeni[i] = False
    k = regresyon_karari(_onceki(eski), _sonuclar(yeni))
    assert k["karar"] == "REGRESYON"
    assert k["bozulan"] == 12 and k["duzelen"] == 0


def test_gercek_iyilesme_regresyon_sayilmaz():
    eski = {i: False for i in range(1, 102)}
    yeni = dict(eski)
    for i in range(1, 13):
        yeni[i] = True
    k = regresyon_karari(_onceki(eski), _sonuclar(yeni))
    assert k["karar"] == "IYILESME"


def test_net_fark_kucukse_p_kucuk_olsa_bile_acilmaz():
    """İkinci emniyet: 2 soruluk bir fark için CI kırmızıya dönmez."""
    eski = {i: True for i in range(1, 102)}
    yeni = dict(eski)
    yeni[1] = yeni[2] = False
    k = regresyon_karari(_onceki(eski), _sonuclar(yeni))
    assert k["bozulan"] == 2 and k["duzelen"] == 0
    assert k["karar"] == "FARK_YOK"


def test_onceki_soru_verisi_yoksa_karar_verilmez():
    """Eşli karar eşli veri ister. Veri yoksa hüküm de yok — susmak doğru."""
    assert regresyon_karari({"accuracy": 0.7}, _sonuclar({1: True})) is None
    assert regresyon_karari(None, _sonuclar({1: True})) is None


def test_eslesmeyen_sorular_karara_girmiyor():
    """Test seti değiştiyse yalnız ortak sorular karşılaştırılır."""
    k = regresyon_karari(_onceki({1: True, 2: True}),
                         _sonuclar({2: False, 3: False, 4: False}))
    assert k["eslesen"] == 1 and k["bozulan"] == 1


def test_satir_metni_dayanagi_tasiyor():
    k = regresyon_karari(_onceki({i: True for i in range(1, 10)}),
                         _sonuclar({i: (i > 3) for i in range(1, 10)}))
    metin = regresyon_satiri(k)
    assert "McNemar p" in metin and "bozuldu" in metin and "düzeldi" in metin


# ------------------------------------------------ soru bazlı veri taşınıyor mu

def test_onceki_olcum_soru_bazli_veriyi_okuyor(tmp_path):
    """BULGU-05'in diğer yüzü: eşli karar ancak soru bazlı veri saklanırsa
    yapılabilir. `onceki_olcum` bunu `results` alanından çıkarır."""
    import json
    yol = tmp_path / "results.json"
    yol.write_text(json.dumps({
        "damga": {"tarih": "2026-08-22", "olcum_gunu": "2026-08-16"},
        "ozet": {"accuracy": 0.71, "n": 101},
        "results": [{"id": 1, "dogru": True}, {"id": 2, "dogru": False}],
    }), encoding="utf-8")
    o = onceki_olcum(str(yol))
    assert o["sorular"] == {"1": True, "2": False}
