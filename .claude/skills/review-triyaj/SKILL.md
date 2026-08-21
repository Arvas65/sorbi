---
name: review-triyaj
description: Bir iş paketi bitip Review kapısına geldiğinde kullan. İhsan'ın triyaj edeceği bulgu listesini üretir. "review", "triyaj", "bulgular", "İP bitti", "gözden geçir" durumlarında devreye girer. Kapı İhsan'ındır; bu skill karar vermez, karar verilebilir hâle getirir.
---

# Review kapısı — triyaj listesi hazırlama

Review kapısı **İhsan'ındır.** Bu skill'in işi karar vermek değil,
kararı verilebilir hâle getirmek.

## Triyaj sözlüğü

| Etiket | Anlamı |
|--------|--------|
| **BLOK** | Ship'i durdurur |
| **DÜZELT** | Bu iş paketinde çözülür |
| **SONRA** | Backlog'a düşer, numarası verilir |
| **KABUL** | Bilerek yaşıyoruz — **yazılı gerekçe olmadan verilmez** |

## Listenin biçimi

Her bulgu için: numara, ne olduğu, **önerin**, boş bir triyaj kutusu.
Önerini yazmadan bulgu sunma — İhsan'ı boş bir tabloyla baş başa bırakmak
triyajı ona iki kez yaptırmaktır.

```
| # | Bulgu | Önerim | Senin triyajın |
|---|-------|--------|----------------|
| X-01 | ... | KABUL — gerekçe | ☐ |
```

## Listeye ne girer

- Karar gerektiren her şey: takas yapılmış, varsayım alınmış, risk kalmış
- **Kendi hatalarım** — ayrı bir bölümde, gizlemeden. Testin ya da ölçümün
  yakaladığı kusurlar buraya yazılır; hangi mekanizmanın yakaladığı dahil.
- **Ölçülmeyen, dolayısıyla iddia edilmeyen** şeyler. Bir başlık altında
  açıkça: "şunu ölçmedik, o yüzden şunu söylemiyoruz."

## Listeye ne girmez

- Yapılmış ve doğrulanmış rutin iş (o TEST/VERIFY belgesine gider)
- Benim kendi başıma çözebileceğim şeyler — onları çöz, sonra yaz

## Belgeler

Bir İP bittiğinde `docs/is-hatti/v3/IP-XX/` altına dört dosya:

| Dosya | İçerik |
|-------|--------|
| `REVIEW.md` | Triyaj listesi (İhsan'ın kapısı) |
| `TEST.md` | Ne koşuldu, hangi sayılar çıktı |
| `VERIFY.md` | İddia → kanıt → kanıt nerede. Ve **doğrulanamayanlar.** |
| `DEVIR.md` | İhsan dönünce okuyacağı tek belge |

`VERIFY.md` bir kabul kapısı listesiyle biter: Ship'ten önce yeşil olması
gerekenler, kutulu.
