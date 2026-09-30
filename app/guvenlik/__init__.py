"""Güvenlik katmanı (ADR-10): veri sınırı, anonimleştirme, çıkış kapısı.

Bu paket yalnız stdlib + `app.config` + `app.akis.mod` import eder. Ağ ya da
LLM bağımlılığı yoktur; her şey LLM'siz test edilir.
"""
