# Gecikme Raporu — 2026-09-06

**Gereksinim:** G-12 — tek soruya en geç 10 saniyede yanıt (yerel çıkarım modu).

| Ölçü | Değer |
|------|-------|
| p50 | **2.30 sn** |
| p95 | **3.85 sn** |
| Hedef (p95) | 10 sn — **KAPSAM DIŞI** |

> **G-12 hakkında hüküm verilmedi.** Bu koşum `mod=api` ile alındı. G-12 *yerel çıkarım modu* için tanımlıdır; api modunda ölçülen süre SorBI'nin çıkarımını değil dış servisin altyapısını ve ağ gecikmesini ölçer. Sayılar aşağıda durur, hüküm verilmez.


## Ölçüm damgası

| Alan | Değer |
|------|-------|
| tarih | `2026-09-06` |
| olcum_gunu | `2026-07-23` |
| commit | `1d92e6d (+islenmemis degisiklikler)` |
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
| 5.03 | `sonuc_farkli` | Röntgen çekilen muayenelerin tanıları nelerdir? |
| 4.73 | `sonuc_farkli` | Ortopedi bölümüne yatan hasta sayısı kaç? |
| 4.61 | `sonuc_farkli` | Endoskopi yapılan muayenelerin toplam fatura tutarı nedir? |
| 4.04 | `sonuc_farkli` | Kadın hastaların ortalama yaşı kaç? |
| 3.96 | `sonuc_farkli` | Ortalamadan fazla randevusu olan doktorlar kimler? |

> Not: süreler uçtan uca ölçülür (ön işleme + RAG + üretim + doğrulama +
> yürütme). Gold SQL koşumu bu süreye dahildir ve ölçümü bir miktar
> yukarı çeker; üretim kullanımında o adım yoktur.
