# Gecikme Raporu — 2026-08-22

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **21.73 sn** |
| p95 | **32.76 sn** |
| Hedef (p95) | 10 sn — KARŞILANMADI |

## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-22` |
| olcum_gunu | `2026-07-23` |
| commit | `ffe5db3` |
| model | `qwen2.5-coder:7b-instruct` |
| mod | `local` |
| db_url | `sqlite:///C:\Users\Arvas\SorBı\demo\hospital.db` |
| python | `3.13.12` |
| platform | `Windows AMD64` |
| temperature | `0.0` |
| seed | `42` |
| num_ctx | `8192` |
| ornek_degerler | `True` |

## En yavaş 5 soru

| Süre (sn) | Aşama | Soru |
|-----------|-------|------|
| 41.70 | `sonuc_farkli` | Her işlem kaç muayenede uygulanmış? |
| 41.27 | `sonuc_farkli` | MR çektiren kaç farklı hasta var? |
| 38.79 | `sonuc_farkli` | Kadın hastaların ortalama yaşı kaç? |
| 37.91 | `dogrulama_reddi` | Hipertansiyon tanısı konan hastalar hangi şehirlerden? |
| 32.93 | `esit` | Geçen ay en çok muayene yapan 5 doktor kim? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
