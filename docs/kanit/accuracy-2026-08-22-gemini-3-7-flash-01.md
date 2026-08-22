# Execution Accuracy Raporu — 2026-08-22

**Gereksinim:** G-11 — 50 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **71.3%**  (72/101)


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
| Sessiz yanlış (çalıştı, cevap yanlış) | **29/101** (%28.7) |
| Yakalanan hata (reddedildi / hata verdi) | 0/101 |
| **Yanlışların içinde sessiz olanların payı** | **%100.0** |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

## Önceki ölçümle karşılaştırma

> **Karşılaştırma yapılmadı.** Önceki koşum `model=qwen2.5-coder:7b-instruct`, bu koşum `model=gemini-3.7-flash` ile yapıldı (farklı model). Üretim ayarı değiştiğinde yüzdeler aynı şeyi ölçmez.
>
> Aynı cetveli kullanan iki koşum arasında karşılaştırma otomatik döner.


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

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
| kolay | 30/35 | %86 |
| orta | 27/39 | %69 |
| zor | 15/27 | %56 |

## JOIN sayısı kırılımı

| JOIN | Doğru / Toplam | Oran |
|------|----------------|------|
| 0 | 41/54 | %76 |
| 1 | 20/29 | %69 |
| 2 | 4/9 | %44 |
| 3 | 4/5 | %80 |
| 4 | 3/4 | %75 |

## Hangi aşamada kaybediliyor

| Aşama | Soru sayısı |
|-------|-------------|
| `esit` | 72 |
| `sonuc_farkli` | 29 |

## Güven kontrolü karnesi (B-7)

Aşağıdaki sayılar cevabın doğruluğunu değil, **uyarı sisteminin**
başarısını ölçer. Değerlendirme evreni yalnız temiz bir tablo dönen
cevaplardır (101 soru) — sessiz yanlışın yaşadığı yer.

| Ölçü | Değer | Yön |
|------|-------|-----|
| Sessiz yanlışların yakalananı | **5/29** (%17) | yükselmeli |
| Doğru cevaba konan gereksiz bayrak | 2/72 (%3) | düşmeli |
| Bayrak isabeti (bayraklının kaçı gerçekten yanlış) | **%71** | yükselmeli |

### Kontrol bazında

İsabeti düşük bir kontrol, koddan silinmeden `SORBI_GUVEN_KAPALI` ile
kapatılır; böylece sonraki ölçüm aynı çizelgeyle karşılaştırılabilir.

| Kontrol | Yanlış cevapta | Doğru cevapta | İsabet |
|---------|----------------|----------------|--------|
| `bos_sonuc_filtreli` | 2 | 0 | %100 |
| `bicim_sayi` _(kapalı)_ | 1 | 0 | %100 |
| `sifir_toplama` | 2 | 0 | %100 |
| `bilinmeyen_deger` | 1 | 1 | %50 |
| `toplama_uyumsuz` | 0 | 1 | %0 |
| `sema_ortusmez` _(kapalı)_ | 0 | 5 | %0 |


Soru bazlı ayrıntı: `eval/results.json`
