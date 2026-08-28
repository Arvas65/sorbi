# Gecikme Raporu — 2026-08-27

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.25 sn** |
| p95 | **3.67 sn** |
| Hedef (p95) | 10 sn — **KAPSAM DIŞI** |

> **G-12 hakkında hüküm verilmedi.** Bu koşum `mod=api` ile alındı. G-12 *yerel çıkarım modu* için tanımlıdır; api modunda ölçülen süre SorBI'nin çıkarımını değil dış servisin altyapısını ve ağ gecikmesini ölçer. Sayılar aşağıda durur, hüküm verilmez.

> Hedefi aşan soru: en az 1 tanesi 10 sn üstünde (en yavaş 12.71 sn). p95 bir vekildir; gereksinimin metni "en geç" der.


## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-27` |
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
| 12.71 | `esit` | Profesörlerin toplam randevu sayısı kaçtır? |
| 5.23 | `sonuc_farkli` | Röntgen çekilen muayenelerin tanıları nelerdir? |
| 4.72 | `sonuc_farkli` | MR çektiren kaç farklı hasta var? |
| 4.26 | `sonuc_farkli` | En çok tamamlanmış randevusu olan 5 doktor kim? |
| 3.99 | `sonuc_farkli` | Her doktorun kaç randevusu var? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
