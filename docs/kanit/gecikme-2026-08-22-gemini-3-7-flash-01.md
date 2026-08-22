# Gecikme Raporu — 2026-08-22

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.26 sn** |
| p95 | **3.76 sn** |
| Hedef (p95) | 10 sn — KARŞILANDI |

## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-22` |
| olcum_gunu | `2026-07-23` |
| commit | `884f8d9 (+islenmemis degisiklikler)` |
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
| 7.94 | `esit` | Son 7 günde kaç randevu var? |
| 5.09 | `sonuc_farkli` | Röntgen çekilen muayenelerin tanıları nelerdir? |
| 3.98 | `esit` | En genç 5 hasta kim? |
| 3.90 | `sonuc_farkli` | Endoskopi yapılan muayenelerin toplam fatura tutarı nedir? |
| 3.76 | `sonuc_farkli` | Bu yıl kesilen faturaların toplam tutarı nedir? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
