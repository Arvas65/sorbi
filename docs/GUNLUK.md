# Oturum günlüğü

Her oturum en üste üç satır ekler: ne yapıldı · ne ölçüldü · ne açık.
2026-08-11 … 09-07 arası 1.455 satırlık eski günlük arşivde
(`ip-46-cekirdek` dalı, `docs/is-hatti/GUNLUK.md`).

## 2026-09-30 (gece) — Kapılar geçildi, Faz B onaylandı

**Yapıldı:** master `9c27629 → 4579208` hızlı-ileri sarıldı (İhsan'ın Ship kararı). ADR-5 **KABUL, B**
— `config.py`'ye ve bir teste kilitlendi. BULGU-27 DÜZELT: karne satırına `makine=` damgası.
BULGU-18 SONRA (İP-56). **Açık:** Faz B — İP-45, İP-53a (Claude), İP-43 (İhsan).

## 2026-09-30 (akşam) — BULGU-15 kapandı

**Yapıldı:** İhsan admin parolasını döndürdü; public geçmişteki hash değersiz. **Açık:** toparla PR merge · ADR-5 § 6 · BULGU-18/27 · Faz B Plan onayı.

## 2026-09-30 — Toparlama (Faz A)

**Yapıldı:** master (07-25'te donmuştu) v4 çekirdek dalına taşındı. Gece ölçüm
hattı (7 `.bat`, 3 eval aracı, 33 test) emekli; `docs/` 21 bin satırdan
plan + kararlar + tasarım + kanıt özüne indi. `46-yama` (BULGU-35) uygulandı,
`42` ve `48` uygulanmadı (emekli hatta aitti). ADR'ler `docs/kararlar/`'da
toplandı, ADR-5 güncel taslakla değişti. FDE planı yazıldı (`docs/PLAN.md`).
**Ölçüldü:** ruff temiz · pytest **666** yeşil (693 − 33 hat testi + 6 kota) ·
gold 101/101 · karne `gold=101 alarm=1 mutant=306 yakalanan=245 zbos=0`, öncekiyle aynı.
**Açık:** ADR-5 § 6 · BULGU-18/27
triyaj · Faz B Plan kapısı. Yeni: BULGU-39 (çekirdek ürüne bağlı değil),
BULGU-40 (API anahtarı düz metin).
