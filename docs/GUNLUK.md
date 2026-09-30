# Oturum günlüğü

Her oturum en üste üç satır ekler: ne yapıldı · ne ölçüldü · ne açık.
2026-08-11 … 09-07 arası 1.455 satırlık eski günlük arşivde
(`ip-46-cekirdek` dalı, `docs/is-hatti/GUNLUK.md`).

## 2026-09-30 (gece, geç) — Güvenlik turu G1

**Yapıldı:** Türkiye çerçevesi kaynaktan doğrulandı (KVKK md. 6/9 + 7499, Kurul 2018/10 ve
2019/10, Sağlık Verileri Yön., 2019/12, 7545, Üretken YZ Rehberi) → `docs/guvenlik/GUVENLIK.md`,
ADR-10 (öneri). Kodda: anonimleştirici (izin listesi, geri dönüşlü), Türkiye'ye özgü
doğrulamalı algılayıcılar, **çıkış kapısı** (`_api_chat`, varsayılan kapalı). **BULGU-43**
(v3 kilidi atlıyordu) kapandı. `urllib3` 2.8.0, `oauthlib` 4.0.0. CI'a pip-audit + gitleaks.
**Ölçüldü:** pytest 781 · gold 101/101 · karne değişmedi · gitleaks ağaç + 34 commit temiz ·
pip-audit: chromadb 4 açık KABUL (gerekçeli, bekçili).
**Açık:** ADR-10 onayı · BULGU-42 (diskte düz metin) · BULGU-44 (gömme modeli) · G2.

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
