# Gecikme Raporu — 2026-08-28

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.61 sn** |
| p95 | **4.24 sn** |
| Hedef (p95) | 10 sn — **KAPSAM DIŞI** |

> **G-12 hakkında hüküm verilmedi.** Bu koşum `mod=api` ile alındı. G-12 *yerel çıkarım modu* için tanımlıdır; api modunda ölçülen süre SorBI'nin çıkarımını değil dış servisin altyapısını ve ağ gecikmesini ölçer. Sayılar aşağıda durur, hüküm verilmez.


## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-28` |
| olcum_gunu | `2026-07-23` |
| commit | `36d920c (+islenmemis degisiklikler)` |
| model | `gemini-3.7-flash` |
| mod | `api` |
| db_url | `sqlite:///C:\Users\Arvas\SorBı\demo\hospital.db` |
| python | `3.13.12` |
| platform | `Windows AMD64` |
| temperature | `0.0` |
| seed | `42` |
| num_ctx | `8192` |
| ornek_degerler | `True` |
| belirlenim | `seed UYGULANAMIYOR — uç nokta bu alanı tanımıyor (HTTP 400 'Unknown name "seed"'). Bu modda belirlenim mümkün değil.` |

## En yavaş 5 soru

| Süre (sn) | Aşama | Soru |
|-----------|-------|------|
| 6.76 | `esit` | Gastrit tanısı alan kaç farklı hasta var? |
| 5.67 | `sonuc_farkli` | Röntgen çekilen muayenelerin tanıları nelerdir? |
| 5.34 | `esit` | MR çektiren kaç farklı hasta var? |
| 4.42 | `sonuc_farkli` | Endoskopi yapılan muayenelerin toplam fatura tutarı nedir? |
| 4.26 | `sonuc_farkli` | En çok gelir getiren 3 işlem hangisi? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
