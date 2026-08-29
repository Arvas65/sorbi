# Gecikme Raporu — 2026-08-29

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.78 sn** |
| p95 | **4.97 sn** |
| Hedef (p95) | 10 sn — **KAPSAM DIŞI** |

> **G-12 hakkında hüküm verilmedi.** Bu koşum `mod=api` ile alındı. G-12 *yerel çıkarım modu* için tanımlıdır; api modunda ölçülen süre SorBI'nin çıkarımını değil dış servisin altyapısını ve ağ gecikmesini ölçer. Sayılar aşağıda durur, hüküm verilmez.


## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-08-29` |
| olcum_gunu | `2026-07-23` |
| commit | `df0c989 (+islenmemis degisiklikler)` |
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
| 7.28 | `esit` | Profesör unvanlı doktorlar kimler? |
| 5.98 | `esit` | EKG işlemi kaç kez uygulanmış? |
| 5.79 | `sonuc_farkli` | Bu ay kaç fatura kesildi? |
| 5.63 | `sonuc_farkli` | En sık uygulanan işlem hangisi? |
| 5.05 | `sonuc_farkli` | MR çektiren kaç farklı hasta var? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
