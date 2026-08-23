# Execution Accuracy Raporu — 2026-08-23

**Gereksinim:** G-11 — 50 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **70.3%**  (71/101)


**Hedef (80%) KARŞILANMADI.**

> ADR-2 koşulu tetiklendi: RAG-only baseline hedefin altında. QLoRA fine-tune 
> kararı yeniden açılmalı ve yeni bir iş paketi olarak planlanmalıdır.

Öz-onarım denemesi yapılan soru sayısı: 0/101

## Sessiz yanlış (B-7)

Yanlış cevabın iki türü vardır ve riskleri aynı değildir. **Yakalanan** hata kullanıcıyı
uyarır. **Sessiz yanlış** hatasız bir tablo döndürür ve yanlış sayı yönetime taşınır —
sistem analizi B7 bunu projenin en büyük riski olarak kaydetmişti.

| Ölçü | Değer |
|------|-------|
| Sessiz yanlış (çalıştı, cevap yanlış) | **30/101** (%29.7) |
| Yakalanan hata (reddedildi / hata verdi) | 0/101 |
| **Yanlışların içinde sessiz olanların payı** | **%100.0** |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

## Önceki ölçümle karşılaştırma

Önceki koşum: `2026-08-22` · model `gemini-3.7-flash` · commit `884f8d9 (+islenmemis degisiklikler)`

| Ölçü | Önceki | Şimdi | Fark |
|------|--------|-------|------|
| Accuracy | %71.3 | **%70.3** | -1.0 puan (gerileme) |
| p50 | 2.3 sn | 2.3 sn | +0.0 sn (gerileme) |
| p95 | 3.8 sn | 4.8 sn | +1.0 sn (gerileme) |
| Sessiz yanlış | 29 | 30 | +1.0 soru (gerileme) |

> Karşılaştırma yalnız test seti ve ölçüm yöntemi aynıysa anlamlıdır.
> Model ya da soru sayısı değiştiyse bu tabloyu tek başına okuma.


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

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
| kolay | 31/35 | %89 |
| orta | 25/39 | %64 |
| zor | 15/27 | %56 |

## JOIN sayısı kırılımı

| JOIN | Doğru / Toplam | Oran |
|------|----------------|------|
| 0 | 41/54 | %76 |
| 1 | 20/29 | %69 |
| 2 | 5/9 | %56 |
| 3 | 2/5 | %40 |
| 4 | 3/4 | %75 |

## Hangi aşamada kaybediliyor

| Aşama | Soru sayısı |
|-------|-------------|
| `esit` | 71 |
| `sonuc_farkli` | 30 |

## Güven kontrolü karnesi (B-7)

Aşağıdaki sayılar cevabın doğruluğunu değil, **uyarı sisteminin**
başarısını ölçer. Değerlendirme evreni yalnız temiz bir tablo dönen
cevaplardır (101 soru) — sessiz yanlışın yaşadığı yer.

| Ölçü | Değer | Yön |
|------|-------|-----|
| Sessiz yanlışların yakalananı | **6/30** (%20) | yükselmeli |
| Doğru cevaba konan gereksiz bayrak | 1/71 (%1) | düşmeli |
| Bayrak isabeti (bayraklının kaçı gerçekten yanlış) | **%86** | yükselmeli |

### Kontrol bazında

İsabeti düşük bir kontrol, koddan silinmeden `SORBI_GUVEN_KAPALI` ile
kapatılır; böylece sonraki ölçüm aynı çizelgeyle karşılaştırılabilir.

| Kontrol | Yanlış cevapta | Doğru cevapta | İsabet |
|---------|----------------|----------------|--------|
| `bos_sonuc_filtreli` | 2 | 0 | %100 |
| `bilinmeyen_deger` | 1 | 0 | %100 |
| `bicim_sayi` _(kapalı)_ | 1 | 0 | %100 |
| `sifir_toplama` | 4 | 0 | %100 |
| `sema_ortusmez` _(kapalı)_ | 1 | 4 | %20 |
| `toplama_uyumsuz` | 0 | 1 | %0 |


Soru bazlı ayrıntı: `eval/results.json`
