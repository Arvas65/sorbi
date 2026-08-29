"""BULGU-19 testleri — karne geçmişi denetimi.

Bu testlerin varlık sebebi: düzeltilen kontrolün bir daha sessizce ölmemesi.
Önceki iki denemede (2026-08-22 ölü kod, 2026-08-24 "gerçek kontrole
çevrildi") kontrolün kendisinin testi yoktu.
"""
from __future__ import annotations

from eval import karne_gecmisi as kg

GERCEK = """\
KARNE_OZET gun=2026-07-23 gold=3 alarm=0 mutant=3 yakalanan=3 zbos=0
KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=239 yakalanan=199 zbos=0
KARNE_OZET gun=2026-07-23 gold=3 alarm=0 mutant=3 yakalanan=3 zbos=0
KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 yakalanan=245 zbos=0
KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 yakalanan=245 zbos=0
"""


def yaz(tmp_path, metin):
    p = tmp_path / "KARNE-GECMIS.log"
    p.write_text(metin, encoding="utf-8")
    return str(p)


def test_ayristirma():
    k = kg.ayristir("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 "
                    "yakalanan=245 zbos=0")
    assert k == {"gun": "2026-07-23", "gold": 101, "alarm": 1,
                 "mutant": 306, "yakalanan": 245, "zbos": 0}


def test_alakasiz_satir_atlanir():
    assert kg.ayristir("TEST_OZET gecen=460") is None
    assert kg.ayristir("") is None


def test_duman_kosumu_tam_kosumla_kiyaslanmaz(tmp_path):
    """gold=3 duman koşumları, gold=101 tam koşumun paydası olamaz.

    Naif bir 'son iki satır' karşılaştırması 245 -> 3 düşüşü görür ve her
    duman koşumundan sonra sahte alarm üretirdi.
    """
    son, onceki = kg.son_iki(kg.kayitlar(yaz(tmp_path, GERCEK)))
    assert son["gold"] == 101 and onceki["gold"] == 101
    assert kg.durum(son, onceki)[0] == "ayni"


def test_gercek_dusus_yakalanir(tmp_path):
    metin = GERCEK + ("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 "
                      "yakalanan=240 zbos=0\n")
    son, onceki = kg.son_iki(kg.kayitlar(yaz(tmp_path, metin)))
    kod, aciklama = kg.durum(son, onceki)
    assert kod == "DUSUS"
    assert "245 -> 240" in aciklama


def test_artis_uyari_degildir(tmp_path):
    metin = GERCEK + ("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 "
                      "yakalanan=260 zbos=0\n")
    son, onceki = kg.son_iki(kg.kayitlar(yaz(tmp_path, metin)))
    assert kg.durum(son, onceki)[0] == "arti"


def test_havuz_buyuyunce_kiyas_yok(tmp_path):
    """239 -> 306 geçişi bir gerileme değil, kıyasın kaybıdır. Geçmişte bu
    geçiş gerçekten yaşandı (2026-08-28)."""
    metin = GERCEK + ("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=400 "
                      "yakalanan=250 zbos=0\n")
    son, onceki = kg.son_iki(kg.kayitlar(yaz(tmp_path, metin)))
    kod, aciklama = kg.durum(son, onceki)
    assert kod == "kiyas_yok"
    assert "306 -> 400" in aciklama


def test_ilk_kosum_uyari_degildir(tmp_path):
    tek = "KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 yakalanan=245 zbos=0\n"
    son, onceki = kg.son_iki(kg.kayitlar(yaz(tmp_path, tek)))
    assert onceki is None
    assert kg.durum(son, onceki)[0] == "ilk"


def test_dosya_yoksa_cokmez(tmp_path):
    son, onceki = kg.son_iki(kg.kayitlar(str(tmp_path / "yok.log")))
    assert kg.durum(son, onceki)[0] == "okunamadi"


def test_bozuk_satir_cokertmez(tmp_path):
    metin = GERCEK + "KARNE_OZET gold=abc mutant=xyz\n"
    kayit = kg.kayitlar(yaz(tmp_path, metin))
    assert len(kayit) == 5          # bozuk satır sessizce atlanır, hat durmaz


def test_cikis_kodu_yalniz_gercek_gerilemede_kirmizi(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kg.sys, "argv", ["karne_gecmisi.py", yaz(tmp_path, GERCEK)])
    assert kg.main() == 0
    assert "durum=ayni" in capsys.readouterr().out

    metin = GERCEK + ("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=306 "
                      "yakalanan=240 zbos=0\n")
    monkeypatch.setattr(kg.sys, "argv", ["karne_gecmisi.py", yaz(tmp_path, metin)])
    assert kg.main() == 1
