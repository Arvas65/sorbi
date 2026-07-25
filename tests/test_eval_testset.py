"""Eval test setinin bütünlük kontrolü (G-11 önkoşulu).

LLM gerektirmez: her gold_sql'in (1) doğrulayıcıdan geçtiğini ve
(2) demo veritabanında hatasız çalıştığını doğrular. Test setinin kendisi
bozuksa execution accuracy ölçümü anlamsız olur — bu yüzden ayrı test.
"""
import json
import os

import pytest

from app import executor
from app.validator import validate_and_transpile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(HERE, "demo", "hospital.db")
TESTSET = os.path.join(HERE, "eval", "test_set_tr.jsonl")

pytestmark = pytest.mark.skipif(not os.path.exists(DB),
                                reason="demo/hospital.db yok — önce demo/seed_data.py çalıştırın")


def _items():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_testset_alanlari_tam():
    items = _items()
    assert len(items) >= 30
    for it in items:
        assert {"id", "soru", "gold_sql", "zorluk", "join"} <= set(it)


@pytest.mark.parametrize("item", _items(), ids=lambda it: f"soru-{it['id']}")
def test_gold_sql_gecerli_ve_calisiyor(item):
    v = validate_and_transpile(item["gold_sql"])
    assert v.ok, f"gold_sql doğrulanamadı: {v.error}"
    r = executor.run(v.sql, db_url=f"sqlite:///{DB}")
    assert r.status == "BASARILI", f"gold_sql çalışmadı: {r.error}"
