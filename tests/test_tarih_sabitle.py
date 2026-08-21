"""Ölçüm 'bugün'ünün sabitlenmesi (İP-23).

Bu testlerin işi, cetvelin takvimle birlikte kaymadığını garanti etmek.
"""
from eval.tarih_sabitle import sabitle, sayac

GUN = "2026-08-16"


def test_date_now_sabitlenir():
    assert sabitle("SELECT date('now')", GUN) == "SELECT date('2026-08-16')"


def test_degistirici_korunur():
    sql = "SELECT * FROM r WHERE tarih >= date('now','start of month','-1 month')"
    assert "date('2026-08-16','start of month','-1 month')" in sabitle(sql, GUN)


def test_julianday_da_sabitlenir():
    assert "julianday('2026-08-16')" in sabitle("SELECT julianday('now') - x FROM t", GUN)


def test_strftime_ikinci_argumani_sabitlenir():
    assert "'2026-08-16'" in sabitle("SELECT strftime('%Y-%m', 'now')", GUN)


def test_veri_degeri_olarak_now_korunur():
    """`WHERE durum = 'now'` bir tarih referansı değil, bir metin değeridir."""
    sql = "SELECT * FROM t WHERE durum = 'now'"
    assert sabitle(sql, GUN) == sql


def test_gun_yoksa_sql_degismez():
    sql = "SELECT date('now')"
    assert sabitle(sql, None) == sql


def test_bos_sql_cokmez():
    assert sabitle("", GUN) == ""
    assert sabitle(None, GUN) is None


def test_now_yoksa_sql_aynen_doner():
    sql = "SELECT COUNT(*) FROM doktor"
    assert sabitle(sql, GUN) == sql


def test_sayac_kac_yer_oldugunu_soyler():
    assert sayac("SELECT date('now'), julianday('now')") == 2
    assert sayac("SELECT 1") == 0


def test_test_setindeki_zamana_bagli_sorular_sabitleniyor():
    """13 gold sorgu zamana bağlı; hepsi sabitlenebilmeli."""
    import json
    import os
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yol = os.path.join(kok, "eval", "test_set_tr.jsonl")
    with open(yol, encoding="utf-8") as f:
        gold = [json.loads(s)["gold_sql"] for s in f if s.strip()]
    zamana_bagli = [g for g in gold if sayac(g)]
    assert len(zamana_bagli) == 13
    assert all("'now'" not in sabitle(g, GUN) for g in zamana_bagli)


def test_ortam_degiskeni_yoksa_veriden_turetilir(monkeypatch):
    """Kimse ortam değişkeni vermezse bile ölçüm sabitlenmiş olmalı —
    ve sabit bir yıla değil, VERİNİN kendi son gününe."""
    from app import config as cfg
    from eval import tarih_sabitle as ts
    monkeypatch.setattr(cfg, "BUGUN", "")
    assert ts.olcum_gunu() == ts.veri_gunu()


def test_ortam_degiskeni_varsayilani_ezer(monkeypatch):
    from app import config as cfg
    from eval import tarih_sabitle as ts
    monkeypatch.setattr(cfg, "BUGUN", "2026-01-05")
    assert ts.olcum_gunu() == "2026-01-05"


def test_bozuk_referans_gunu_sessizce_gecmez(monkeypatch):
    """Yazım hatası olan bir referans tarihin gerçek takvime düşmesi, ölçüm
    hattındaki sessiz yanlış olurdu — patlaması gerekir."""
    import pytest

    from app import config as cfg
    from eval import tarih_sabitle as ts
    monkeypatch.setattr(cfg, "BUGUN", "2026-8-16")
    with pytest.raises(ValueError, match="SORBI_BUGUN"):
        ts.olcum_gunu()


def test_sabitlenen_gold_kurumsunda_now_kalmaz():
    """Cetvelin duvar saatinden bağımsız olmasının tek koşulu bu."""
    import json
    import os
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(kok, "eval", "test_set_tr.jsonl"), encoding="utf-8") as f:
        gold = [json.loads(s)["gold_sql"] for s in f if s.strip()]
    assert all("'now'" not in sabitle(g, GUN).lower() for g in gold)


# --------------------------------------------------- veriden türetilen gün

def test_veri_gunu_demo_veritabanindan_turetilir():
    """Referans gün makineye değil VERİYE ait bir sayıdır."""
    from eval.tarih_sabitle import veri_gunu
    g = veri_gunu()
    assert g and len(g) == 10 and g.count("-") == 2


def test_veri_gunu_her_tablonun_dolu_oldugu_son_gun():
    """Genel maksimum seçilseydi 'bugün bekleyen randevu' boş dönerdi."""
    import sqlite3

    from app import config as cfg
    from eval.tarih_sabitle import veri_gunu
    g = veri_gunu()
    c = sqlite3.connect(cfg.DB_URL.replace("sqlite:///", ""))
    for tablo, kolon in [("randevu", "tarih"), ("fatura", "tarih"),
                         ("yatis", "giris_tarihi")]:
        sorgu = f"SELECT COUNT(*) FROM {tablo} WHERE {kolon} <= ?"  # noqa: S608 - test sabitleri
        n = c.execute(sorgu, (g,)).fetchone()[0]
        assert n > 0, f"{tablo} referans günde boş"
    c.close()


def test_dogum_tarihi_referans_gunu_bozmaz():
    """Nitelik tarihleri (doğum, işe başlama) yıllar öncesine düşer."""
    from eval.tarih_sabitle import veri_gunu
    assert veri_gunu() > "2025-01-01"


def test_veritabani_okunamazsa_yedek_gune_duser(monkeypatch):
    from app import config as cfg
    from eval import tarih_sabitle as ts
    monkeypatch.setattr(cfg, "BUGUN", "")
    monkeypatch.setattr(ts, "_ONBELLEK", {})
    monkeypatch.setattr(cfg, "DB_URL", "sqlite:///yok-boyle-bir-dosya-yok.db")
    assert ts.olcum_gunu() == ts.YEDEK_GUN


def test_elle_verilen_gun_veriden_turetilene_baskin(monkeypatch):
    from app import config as cfg
    from eval import tarih_sabitle as ts
    monkeypatch.setattr(cfg, "BUGUN", "2026-03-03")
    assert ts.olcum_gunu() == "2026-03-03"
