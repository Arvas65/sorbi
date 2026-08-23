# Gecikme Raporu — 2026-08-23

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.29 sn** |
| p95 | **4.81 sn** |
| Hedef (p95) | 10 sn — KARŞILANDI |

## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-23` |
| olcum_gunu | `2026-07-23` |
| commit | `259f50a (+islenmemis degisiklikler)` |
| model | `gemini-3.7-flash` |
| mod | `api` |
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
| 12.36 | `esit` | Yıllara göre kaç hasta kaydolmuş? |
| 6.33 | `sonuc_farkli` | En ucuz işlem hangisi? |
| 5.67 | `esit` | Erkek hasta sayısı kaçtır? |
| 5.56 | `esit` | En çok işlem uygulanan 3 muayenenin tanısı nedir? |
| 4.93 | `esit` | Geciken fatura sayısı kaç? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
