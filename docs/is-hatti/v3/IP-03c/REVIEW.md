# İP-03c — REVIEW (triyaj **tamamlandı**)

**Kapsam:** B-7 sessiz yanlış azaltma · **Bulgular:** 2026-08-16
**Triyaj:** İhsan Arvas, 2026-08-23 · **Uygulama:** İP-33

Triyaj sözlüğü: **BLOK** · **DÜZELT** · **SONRA** · **KABUL** (gerekçe zorunlu)

---

## Triyaj kaydı

| # | Bulgu | Nöbet önerisi | **İhsan'ın kararı** | Ne yapıldı |
|---|-------|---------------|---------------------|------------|
| B7R-01 | İki kontrol (`sema_ortusmez`, `bicim_sayi`) varsayılan kapalı | KABUL | **DÜZELT** | `sema_ortusmez` kolon adlarına da bakıyor: açıkken gereksiz bayrak 7 → 3. Takas her koşumda YAN YANA basılıyor; karar bir daha sessizce eskimeyecek. |
| B7R-02 | Karne hayali hatalar üzerinde ölçülüyor | KABUL (kapandı) | — | Ölçüldü: gerçek hatada %20. İş B7R-08'e taşındı. |
| B7R-03 | `where_dus` mutantlarının %43'ü kaçıyor | SONRA | **DÜZELT** | `filtresiz` artık zaman ("geçen ay") ve durum ("geciken" ↔ `GECIKTI`) daraltmasını görüyor. **%59 → %83.** |
| B7R-04 | Türkçe İ kusuru — ölçüm tekrarı isteniyordu | KABUL (kapandı) | — | Tekrar yapıldı: düzeltme 08-16, ölçümler 08-22 ve 08-23. |
| B7R-05 | Güven bayrakları denetim izine yazılmıyor | SONRA | **DÜZELT** | `denetim.guven_kodlari` eklendi (yerinde göç), `audit.guven_karnesi()` ile saha sayımı. Saha karnesi artık tahmin değil, sayım. |
| B7R-06 | `bilinen_degerler` kolon adıyla anahtarlanıyor | KABUL | **DÜZELT** | `tablo.kolon` anahtarı eklendi + takma ad çözümlemesi. `bolum.ad = 'EKG'` artık yakalanıyor; yanlış alarm artmadı. |
| B7R-07 | API modunda `bilinmeyen_deger` susuyordu | ÇÖZÜLDÜ | — | Onaylandı. |
| B7R-08 | `atlanan_kolon` sayısı temsil etmiyor olabilir | SONRA | **DÜZELT** | Havuza dört gerçekçi hata ailesi eklendi (`deger_takasi`, `karsilastirma`, `distinct_dus`, `join_ici_disi`): 239 → **306 mutant**. |

---

## Ölçülen etki

Karne yolculuğu — **ortadaki düşüş bir gerileme değil, bir düzeltmedir:**

```
başlangıç      199/239   %83,3    kolay havuz · 1 gereksiz bayrak
B7R-03/06      212/239   %88,7    aynı havuz  · 1 gereksiz bayrak
havuz büyüdü   222/306   %72,5    DÜRÜST havuz — sayı düştü, doğruluk arttı
yeni kontrol   245/306   %80,1    1 gereksiz bayrak
```

%83'ün bir kısmı havuzun kolaylığından geliyordu; BULGU-04'ün söylediği tam
olarak buydu. Yeni aileler eklenince yakalama düştü, sonra **yakalayarak**
(havuzu kolaylaştırarak değil) geri çıktı.

Yeni kontroller ve hedefledikleri aile:

| Kontrol | Aile | Önce | Sonra |
|---------|------|------|-------|
| `deger_uyumsuz` | soru X değerini istiyor, sorgu Y ile filtreliyor | %21 | **%74** |
| `distinct_eksik` | "kaç FARKLI" sorusuna `COUNT(*)` | %0 | **%36** |
| `deger_uyumsuz` (yön) | "üzerinde" deniyor, `<` yazılmış | %14 | %19 |

**Gereksiz bayrak baştan sona 1/101 (%1,0)** — hiçbir düzeltme yanlış alarmla
ödenmedi.

## Kapanış

BLOK ve DÜZELT etiketli maddelerin tamamı kapatıldı. Ayrıntı: `../IP-33/VERIFY.md`.
