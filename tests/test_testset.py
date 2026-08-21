"""Test setinin kendisinin testleri (İP-04).

Test seti ölçümün cetvelidir. Cetvel bozuksa ölçüm anlamsızdır — bu yüzden
setin kendisi de test altında.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTSET = os.path.join(KOK, "eval", "test_set_tr.jsonl")


@pytest.fixture(scope="module")
def items():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def test_asgari_buyukluk(items):
    """n=50'de %68'in standart hatası ±6,6 puan; %80 hedefinden uzaklık 1,8σ —
    yani "hedefin altında mıyız" sorusu cevaplanamıyordu. n=100'de 2,6σ olur."""
    assert len(items) >= 100, f"set küçüldü: {len(items)}"


def test_id_ve_soru_benzersiz(items):
    assert len({i["id"] for i in items}) == len(items), "id çakışması"
    assert len({i["soru"].lower().strip() for i in items}) == len(items), "soru tekrarı"


def test_alanlar_tam(items):
    for i in items:
        assert {"id", "soru", "gold_sql", "zorluk", "join"} <= set(i), i.get("id")
        assert i["zorluk"] in ("kolay", "orta", "zor")
        assert isinstance(i["join"], int) and i["join"] >= 0
        assert i["soru"].strip() and i["gold_sql"].strip()


def test_zorluk_dagilimi_dengeli(items):
    """Tek bir zorluk sınıfı sette baskın olmamalı; olursa toplam sayı
    o sınıfın performansını ölçer, ürünün performansını değil."""
    for zorluk in ("kolay", "orta", "zor"):
        pay = sum(1 for i in items if i["zorluk"] == zorluk) / len(items)
        assert 0.15 <= pay <= 0.55, f"{zorluk} payı {pay:.0%}"


def test_cok_joinli_sorular_yeterli(items):
    """Ürünün vaadi çok tablolu sorular. 2+ JOIN gerektiren soru sayısı,
    o bölgede anlamlı ölçüm yapmaya yetmeli."""
    assert sum(1 for i in items if i["join"] >= 2) >= 15


def test_gold_sql_select_ile_basliyor(items):
    for i in items:
        assert i["gold_sql"].lstrip().upper().startswith(("SELECT", "WITH")), i["id"]
