# Execution Accuracy Raporu — 2026-08-22

**Gereksinim:** G-11 — 50 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **56.4%**  (57/101)

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
| Sessiz yanlış (çalıştı, cevap yanlış) | **42/101** (%41.6) |
| Yakalanan hata (reddedildi / hata verdi) | 2/101 |
| **Yanlışların içinde sessiz olanların payı** | **%95.5** |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

## Önceki ölçümle karşılaştırma

> **Karşılaştırma yapılmadı.** Önceki koşumda referans günü kayıtlı değil (İP-23 öncesi). O koşum gerçek takvimle alınmıştır ve zamana bağlı 13 soruda bu koşumla aynı şeyi ölçmez.
>
> Aynı cetveli kullanan iki koşum arasında karşılaştırma otomatik döner.


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

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
| kolay | 25/35 | %71 |
| orta | 20/39 | %51 |
| zor | 12/27 | %44 |

## JOIN sayısı kırılımı

| JOIN | Doğru / Toplam | Oran |
|------|----------------|------|
| 0 | 33/54 | %61 |
| 1 | 14/29 | %48 |
| 2 | 5/9 | %56 |
| 3 | 2/5 | %40 |
| 4 | 3/4 | %75 |

## Hangi aşamada kaybediliyor

| Aşama | Soru sayısı |
|-------|-------------|
| `esit` | 57 |
| `sonuc_farkli` | 42 |
| `dogrulama_reddi` | 1 |
| `calisma_hatasi` | 1 |

## Güven kontrolü karnesi (B-7)

Aşağıdaki sayılar cevabın doğruluğunu değil, **uyarı sisteminin**
başarısını ölçer. Değerlendirme evreni yalnız temiz bir tablo dönen
cevaplardır (99 soru) — sessiz yanlışın yaşadığı yer.

| Ölçü | Değer | Yön |
|------|-------|-----|
| Sessiz yanlışların yakalananı | **12/42** (%29) | yükselmeli |
| Doğru cevaba konan gereksiz bayrak | 0/57 (%0) | düşmeli |
| Bayrak isabeti (bayraklının kaçı gerçekten yanlış) | **%100** | yükselmeli |

### Kontrol bazında

İsabeti düşük bir kontrol, koddan silinmeden `SORBI_GUVEN_KAPALI` ile
kapatılır; böylece sonraki ölçüm aynı çizelgeyle karşılaştırılabilir.

| Kontrol | Yanlış cevapta | Doğru cevapta | İsabet |
|---------|----------------|----------------|--------|
| `bos_sonuc_filtreli` | 2 | 0 | %100 |
| `bilinmeyen_deger` | 10 | 0 | %100 |
| `sifir_toplama` | 8 | 0 | %100 |
| `atlanan_kolon` | 3 | 0 | %100 |
| `sema_ortusmez` _(kapalı)_ | 2 | 3 | %40 |


Soru bazlı ayrıntı: `eval/results.json`
