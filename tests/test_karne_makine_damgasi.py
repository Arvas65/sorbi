"""Karne geçmişinde kıyas yalnız aynı makinenin son kaydıyla yapılır (BULGU-27).

Kusur: `_gecmise_yaz` docstring'inde "doğru referans AYNI MAKİNENİN bir önceki
koşumudur" yazıyordu, ama kod günlüğün son satırını alıyordu — kimin yazdığına
bakmadan. Bir bulut oturumunun karnesi araya girince, bir sonraki koşumun
regresyon nöbetçisi yabancı bir satırla kıyas yapıyor ve susuyordu.
Dört kez gerçekleşti (2026-08-28, 08-31, 09-07, 09-30).
"""
import pytest

from eval import guven_olcum


def _karne(yakalanan=245, mutant=306):
    return {"olcum_gunu": "2026-07-23", "gold_sayisi": guven_olcum.TAM_SET,
            "yanlis_alarm": 1, "mutant_sayisi": mutant, "yakalanan": yakalanan,
            "zamana_bagli_bos": []}


@pytest.fixture
def gecmis(tmp_path, monkeypatch):
    yol = tmp_path / "KARNE-GECMIS.log"
    monkeypatch.setattr(guven_olcum, "GECMIS", str(yol))
    return yol


def _makine(monkeypatch, ad):
    monkeypatch.setenv("SORBI_MAKINE", ad)


def test_satir_makine_damgasi_tasir(gecmis, monkeypatch):
    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne())
    assert gecmis.read_text(encoding="utf-8").strip().endswith("makine=ihsan")


def test_yabanci_satir_referans_olmaz(gecmis, monkeypatch, capsys):
    """BULGU-27'nin tam ifadesi: araya giren bulut satırı kıyası bozmamalı."""
    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne())
    _makine(monkeypatch, "bulut")
    guven_olcum._gecmise_yaz(_karne(yakalanan=199, mutant=239))
    capsys.readouterr()

    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne())
    cikti = capsys.readouterr().out
    assert "birebir aynı" in cikti, cikti


def test_ayni_makinede_gerileme_gorunur(gecmis, monkeypatch, capsys):
    """Damga nöbetçiyi körleştirmemeli: aynı makinede fark hâlâ öter."""
    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne())
    _makine(monkeypatch, "bulut")
    guven_olcum._gecmise_yaz(_karne())
    capsys.readouterr()

    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne(yakalanan=230))
    cikti = capsys.readouterr().out
    assert "FARKLI" in cikti and "yakalanan=230" in cikti


def test_damgasiz_eski_satir_referans_olmaz(gecmis, monkeypatch, capsys):
    """Kimin yazdığı bilinmeyen satır hiçbir makinenin tabanı değildir."""
    gecmis.write_text("KARNE_OZET gun=2026-07-23 gold=101 alarm=1 mutant=239 "
                      "yakalanan=199 zbos=0\n", encoding="utf-8")
    _makine(monkeypatch, "ihsan")
    guven_olcum._gecmise_yaz(_karne())
    cikti = capsys.readouterr().out
    assert "taban olacak" in cikti
    assert "1 satır" in cikti          # görmezden gelinen satır sayısı söylenir


def test_makine_adi_depoya_acik_yazilmaz(monkeypatch):
    """Depo herkese açık: ana makine adı değil, özeti yazılır."""
    monkeypatch.delenv("SORBI_MAKINE", raising=False)
    monkeypatch.setattr(guven_olcum.platform, "node", lambda: "ARVAS-LAPTOP")
    kimlik = guven_olcum.makine_kimligi()
    assert "ARVAS" not in kimlik.upper()
    assert len(kimlik) == 8
