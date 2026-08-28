# Execution Accuracy Raporu — 2026-08-27

**Gereksinim:** G-11 — 101 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu.

## Sonuç

## **69.3%**  (70/101)


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
| Sessiz yanlış (çalıştı, cevap yanlış) | **31/101** (%30.7) |
| Reddedilen (cevap kullanıcıya hiç ulaşmadı) | 0/101 |

> "Reddedilen" ile aşağıdaki güven karnesinin "yakalanan"ı **ayrı şeylerdir**:
> burada hat cevabı vermiyor, orada cevap veriliyor ve yanına uyarı konuyor.
> (BULGU-06 — aynı raporda iki tanım aynı adı taşıyordu.)
| **Yanlışların içinde sessiz olanların payı** | **%100.0** |
| Cevabı gerçekten üreten mod | `api` 101/101 — damgayla tutarlı |

Son satır asıl izlenecek sayıdır: doğruluk yükselse bile bu pay yüksek kalıyorsa
ürün güvenilir değildir.

## Önceki ölçümle karşılaştırma

Önceki koşum: `2026-08-23` · model `gemini-3.7-flash` · commit `259f50a (+islenmemis degisiklikler)`

| Ölçü | Önceki | Şimdi | Fark |
|------|--------|-------|------|
| Accuracy | %70.3 | **%69.3** | -1.0 puan (gerileme) |
| p50 | 2.3 sn | 2.2 sn | değişmedi |
| p95 | 4.8 sn | 3.7 sn | -1.1 sn (iyileşme) |
| Sessiz yanlış | 30 | 31 | +1.0 soru (gerileme) |

> Karşılaştırma yalnız test seti ve ölçüm yöntemi aynıysa anlamlıdır.
> Model ya da soru sayısı değiştiyse bu tabloyu tek başına okuma.

### Regresyon kapısı (SPEC A-4)

**FARK YOK — 101 eşleşen soru, 3 bozuldu, 2 düzeldi (net -1), McNemar p = 1.000; ölçülebilir bir doğruluk farkı yok.**

Kural: `bozulan - düzelen >= 3` **ve** `McNemar p < 0.05`. Ham puan farkı tek başına hüküm vermez: aynı kod, aynı ayarlarla alınan iki api koşumu arasında 7 soru yön değiştirmişti (p = 1,000) — saf gürültüde 3 soruluk net fark çıkma olasılığı yaklaşık %45.


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

## Zorluk kırılımı

| Zorluk | Doğru / Toplam | Oran |
|--------|----------------|------|
| kolay | 29/35 | %83 |
| orta | 26/39 | %67 |
| zor | 15/27 | %56 |

## JOIN sayısı kırılımı

| JOIN | Doğru / Toplam | Oran |
|------|----------------|------|
| 0 | 40/54 | %74 |
| 1 | 20/29 | %69 |
| 2 | 5/9 | %56 |
| 3 | 2/5 | %40 |
| 4 | 3/4 | %75 |

## Hangi aşamada kaybediliyor

| Aşama | Soru sayısı |
|-------|-------------|
| `esit` | 70 |
| `sonuc_farkli` | 31 |

## Güven kontrolü karnesi (B-7)

Aşağıdaki sayılar cevabın doğruluğunu değil, **uyarı sisteminin**
başarısını ölçer. Değerlendirme evreni yalnız temiz bir tablo dönen
cevaplardır (101 soru) — sessiz yanlışın yaşadığı yer.

| Ölçü | Değer | Yön |
|------|-------|-----|
| Sessiz yanlışların **bayraklananı** | **7/31** (%23) | yükselmeli |
| Doğru cevaba konan gereksiz bayrak | 1/70 (%1) | düşmeli |
| Bayrak isabeti (bayraklının kaçı gerçekten yanlış) | **%88** | yükselmeli |

### Kontrol bazında

İsabeti düşük bir kontrol, koddan silinmeden `SORBI_GUVEN_KAPALI` ile
kapatılır; böylece sonraki ölçüm aynı çizelgeyle karşılaştırılabilir.

| Kontrol | Yanlış cevapta | Doğru cevapta | İsabet |
|---------|----------------|----------------|--------|
| `bos_sonuc_filtreli` | 2 | 0 | %100 |
| `bilinmeyen_deger` | 1 | 0 | %100 |
| `bicim_sayi` _(kapalı)_ | 1 | 0 | %100 |
| `sifir_toplama` | 5 | 0 | %100 |
| `toplama_uyumsuz` | 0 | 1 | %0 |
| `sema_ortusmez` _(kapalı)_ | 0 | 1 | %0 |


Soru bazlı ayrıntı: `eval/results.json`
