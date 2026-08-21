# Gecikme Raporu — 2026-08-16

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **14.45 sn** |
| p95 | **21.17 sn** |
| Hedef (p95) | 10 sn — KARŞILANMADI |

## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-16` |
| commit | `ffe5db3` |
| model | `qwen2.5-coder:7b-instruct` |
| mod | `local` |
| db_url | `sqlite:///C:\Users\Arvas\SorBı\demo\hospital.db` |
| python | `3.13.12` |
| platform | `Windows AMD64` |
| temperature | `0.0` |
| seed | `42` |
| num_ctx | `4096` |
| ornek_degerler | `True` |

## En yavaş 5 soru

| Süre (sn) | Aşama | Soru |
|-----------|-------|------|
| 31.62 | `esit` | Hastanede kaç doktor çalışıyor? |
| 24.56 | `sonuc_farkli` | Randevusuna gelmeme oranı en yüksek 5 doktor kim? |
| 23.97 | `sonuc_farkli` | Kadın hastaların ortalama yaşı kaç? |
| 22.79 | `sonuc_farkli` | Her işlem kaç muayenede uygulanmış? |
| 21.46 | `dogrulama_reddi` | Hipertansiyon tanısı konan hastalar hangi şehirlerden? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
