"""Kararlar ile kod arasındaki boşluğu kapatan testler.

ADR-1 rev.2 taban modeli ölçümle qwen2.5-coder:7b olarak belirledi ama
`config.LOCAL_MODEL` günlerce llama3.2:3b'de kaldı. Karar bir belgede
yazılıydı, kodda değildi — ve kimse fark etmedi. Bu test o boşluğu
CI'a taşır: ADR değişirse test de değişmeli, yani karar bilinçli olarak
güncellenmiş olur.
"""
import os
import re

from app import config

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR1 = os.path.join(KOK, "docs", "is-hatti", "v3", "ADR", "ADR-1-taban-model.md")


def test_varsayilan_model_adr1_ile_ayni():
    with open(ADR1, encoding="utf-8") as f:
        metin = f.read()
    karar = re.search(r"##\s*Karar\s*\n+\s*Taban model \*\*`([^`]+)`\*\*", metin)
    assert karar, "ADR-1'de 'Karar' bölümü okunamadı"
    assert config.LOCAL_MODEL == karar.group(1), (
        f"ADR-1 `{karar.group(1)}` diyor ama config `{config.LOCAL_MODEL}` kullanıyor. "
        "Karar ile kod ayrışmış.")
