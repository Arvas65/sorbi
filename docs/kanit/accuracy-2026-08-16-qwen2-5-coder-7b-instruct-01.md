# Execution Accuracy Raporu — 2026-08-16

**Gereksinim:** G-11 — 50 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **62.4%**  (63/101)

**Hedef (80%) KARŞILANMADI.**

> ADR-2 koşulu tetiklendi: RAG-only baseline hedefin altında. QLoRA fine-tune 
> kararı yeniden açılmalı ve yeni bir iş paketi olarak planlanmalıdır.

Öz-onarım denemesi yapılan soru sayısı: 6/101

## Sessiz yanlış (B-7)

Yanlış cevabın iki türü vardır ve riskleri aynı değildir. **Yakalanan** hata kullanıcıyı
uyarır. **Sessiz yanlış** hatasız bir tablo döndürür ve yanlış sayı yönetime taşınır —
sistem analizi B7 bunu projenin en büyük riski olarak kaydetmişti.

| Ölçü | Değer |
|------|-------|
| Sessiz yanlış (çalıştı, cevap yanlış) | **36/101** (%35.6) |
| Yakalanan hata (reddedildi / hata verdi) | 2/101 |
| **Yanlışların içinde sessiz olanların payı** | **%94.7** |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

## Önceki ölçümle karşılaştırma

> **Karşılaştırma yapılmadı.** Önceki koşum 50 soruluk, bu koşum 101 soruluk bir setle yapıldı. Test seti değiştiğinde yüzdeler aynı şeyi ölçmez.
>
> Aynı seti kullanan iki koşum arasında karşılaştırma otomatik döner.


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

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
| kolay | 24/35 | %69 |
| orta | 26/39 | %67 |
| zor | 13/27 | %48 |

## JOIN sayısı kırılımı

| JOIN | Doğru / Toplam | Oran |
|------|----------------|------|
| 0 | 37/54 | %69 |
| 1 | 15/29 | %52 |
| 2 | 6/9 | %67 |
| 3 | 2/5 | %40 |
| 4 | 3/4 | %75 |

## Hangi aşamada kaybediliyor

| Aşama | Soru sayısı |
|-------|-------------|
| `esit` | 63 |
| `sonuc_farkli` | 36 |
| `dogrulama_reddi` | 1 |
| `calisma_hatasi` | 1 |

Soru bazlı ayrıntı: `eval/results.json`
