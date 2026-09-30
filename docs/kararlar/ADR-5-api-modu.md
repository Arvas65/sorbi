# ADR-5 (TASLAK) — Çıkarım nerede koşacak: yerel mi, API mi

**Durum:** **TASLAK — karar verilmedi.** Ship kapısıdır, karar İhsan'ındır.
**Hazırlayan:** bulut nöbeti, 2026-08-22 · **Güncelleyen:** bulut nöbeti, 2026-08-30 ·
**Depoya taşındı:** toparlama, 2026-09-30 (proje belgesindeki güncel taslak; depodaki
kopya 08-23'te donmuştu)
**İş paketi:** İP-32 · **İlgili:** ADR-1 rev.2 · G-11, G-12, G-13, G-16 · CLAUDE.md § 3

> Bu dosya bir karar değil, kararın **önüne konan malzemedir.**

> **2026-09-30 notu — "ilk müşteri kim" sorusu cevaplandı.** § 6'nın sonundaki karşı
> argüman kararı ilk müşterinin kimliğine bağlıyordu. İhsan'ın kararı: önce
> **kurgusal bir dış müşteri** (gizlilik vaadi olmayan sentetik şirket) ile kabul
> demosu, sonra izin alınırsa **hastane pilotu**. Bu sıra B'yi güçlendirir: demoda
> API, hastanede yerel. İkisi de aynı kodla.

---

## 1. Neden şimdi

| | yerel `qwen2.5-coder:7b-instruct` | API `gemini-3.7-flash` |
|---|---|---|
| Doğruluk | %56,4–62,4 · tek koşum GA %46,7–65,7 | **%69,3 – %72,3** (altı koşum) |
| p50 / p95 | 21,7 / **32,8 sn** | 2,2–2,8 / **3,7–5,0 sn** |
| Koşum sayısı | 2 (08-16, 08-22) | 6 (08-22 … 09-06) |

Yerel modda G-12 (p95 ≤ 10 sn) **üç kat aşılıyor**; sebep donanım (7B model 6 GB
karta sığmıyor, %18'i CPU'da koşuyor), ayar değil.

Tekrarlar **aynı 101 soruya** ait olduğu için güven aralığı tekrarla daralmaz; tek
koşumun Wilson %95 GA'sı ~%61–79. **G-11 (%80) hiçbir koşumda karşılanmadı.**
Ardışık koşumlar arasında McNemar hep p ≈ 1,000.

## 2. Bu kararın gerçekte ne olduğu

**Bir hız iyileştirmesi değil.** ADR-1 rev.2 "doğrudan API modeline geçmek"
seçeneğini G-13/G-16 (veri dışarı çıkmaz) gerekçesiyle reddetti. API modunu
kalıcı yapmak o reddi geri almaktır. Bu yüzden **Ship kapısıdır.**

Karşılığında G-11 gelmiyor. Karar "doğruluk mu gizlilik mi" değil,
"**hız mı gizlilik mi**".

## 3. Önkoşullar

| # | Önkoşul | Durum |
|---|---------|-------|
| Ö-1 | `mask_context` depoda | ✅ `app/generator.py`, `c452c1c` |
| Ö-2 | API gizlilik testi yeşil | ✅ `tests/test_api_modu.py` |
| Ö-3 | Kota koruması depoda | ✅ `f7c2b85` |
| Ö-4 | Gemini koşumu tekrarlanmış | ✅ altı koşum |
| Ö-5 | Eşli McNemar | ✅ ardışık çiftlerde p ≈ 1,000 |
| **Ö-6** | Gemini ücret/kota/erişim şartları **yazılı** | ❌ **açık — İhsan'ın işi** |
| **Ö-7** | API koşumları tekrarlanabilir | ❌ **kapanmaz** — uç nokta `seed`i HTTP 400 ile reddediyor |

**Ö-7 bir engel değil, bir fiyat etiketidir:** gürültü bandı 3 puan, sd 1,13 puan.
Regresyon eşiği ~5 puana çekilir ya da n≥3 koşumun soru bazlı oy çokluğu alınır.

## 4. Seçenekler

**A — API varsayılan.** Doğruluk ~9–14 puan yüksek, gecikme 6–8 kat düşük, kurulum
kolay. Ama G-13/G-16 vaadi düşer, hastanede DPA/KVKK gerekir, model sürümü haber
verilmeden değişebilir — ve G-11 yine karşılanmaz.

**B — Yerel varsayılan, API açıkça seçilir (çift mod).** Kod zaten bunu yapıyor;
karar onu resmîleştirir. Vaat bozulmaz; demoda API, sahada yerel. Maliyet: iki
modu da ölçmek ve bakmak.

**C — Yerel kalır, G-12 revize edilir.** Tek mod, ama ürün yavaş kalır; hedefi
gerekçesiz ölçüme uydurmak bu projenin kaçındığı hata.

**D — Katmanlı: açık çekirdek yerel, kurumsal katman API (DPA ile).** Çift lisansla
uyumlu, en çok iş. **B'nin üstüne inşa edilir**; B'den D'ye geçiş yeniden yazım
gerektirmez.

## 5. Ölçüm sınırları

- API tabanı ile yerel taban karşılaştırılamaz (farklı model, farklı mod).
- G-12 API modunda ölçülmüyor; geçerli tek G-12 sayısı yerelin p95'i: 21,2–32,8 sn.
- **Güvenilirlik API ile kötüleşti:** yerelde yanlışların %95,5'i sessizdi, Gemini'de
  altı koşumun altısında **%100**. Ürünün asıl açığı mod-bağımsızdır: B-7'nin saha
  sayısı ~%21, mutasyon karnesi ~%80 — aralıklar kesişmiyor.

## 6. Karar

**Boş.** İhsan doldurur.

```
Seçilen:            A / B / C / D / başka
Gerekçe:
Koda inecek yer:    app/config.py  (ADR koda inmezse karar değildir)
G-12'ye ne olacak:
Regresyon eşiği:    (API seçilirse 3 puan → ? ; ölçülen sd 1,13 puan)
Geri alma koşulu:
```

**Öneri (bağlayıcı değil): B.** API G-11'i vermiyor; B'nin bugünkü maliyeti
`config.py`'de bir satır; B, D'yi kapatmaz. 2026-09-30'daki müşteri sırası
(önce kurgusal dış müşteri, sonra hastane) tam olarak B'nin tarif ettiği
kullanım.
