# ADR-5 (TASLAK) — Çıkarım nerede koşacak: yerel mi, API mi

**Durum:** **TASLAK — karar verilmedi.** Ship kapısıdır, karar İhsan'ındır.
**Hazırlayan:** bulut nöbeti, 2026-08-22 · **Güncelleyen:** İP-33, 2026-08-23
**İş paketi:** İP-32 · **İlgili:** ADR-1 rev.2 · G-11, G-12, G-13, G-16

> Bu dosya bir karar değil, kararın **önüne konan malzemedir.** Nöbet ölçer ve
> seçenekleri yazar; hangisinin seçileceğini yazmaz. § 6 boş bırakıldı.

---

## 1. Neden şimdi

| | yerel `qwen2.5-coder:7b-instruct` | API `gemini-3.7-flash` |
|---|---|---|
| Doğruluk | %56,4 (57/101) · GA %46,7–65,7 | %71,3 → %70,3 (iki koşum) · GA %60,8–79,2 |
| p50 / p95 | 21,7 / **32,8 sn** | 2,30 / 3,80 → 4,80 sn |
| Koşum tarihi | 2026-08-22 gece | 2026-08-22 **ve** 2026-08-23 gece |

Yerel modda G-12 (p95 ≤ 10 sn) **üç kat aşılıyor.** ADR-1 rev.2 sebebini zaten
yazmıştı: 7B model 6 GB karta sığmıyor, %18'i CPU'da koşuyor. Mesele ayar
değil, donanım. Yerelde G-12'ye giden yol ya daha küçük model (ADR-1 rev.1'e
dönmek, %38 doğruluk) ya yeni donanımdır.

**İki api koşumu vardır, bir tane değil.** İkisi eşli karşılaştırıldı:
**7 soru yön değiştirdi** (4 doğru→yanlış, 3 yanlış→doğru), **McNemar exact
p = 1,000.** Aralarında ölçülebilir bir doğruluk farkı yoktur; ikisi birlikte
api modunun tabanıdır (~%70,8, Wilson %95 GA yaklaşık %61–79).

## 2. Bu kararın gerçekte ne olduğu

**Bir hız iyileştirmesi değil.** ADR-1 rev.2, "Reddedilen seçenekler"
tablosunda şunu yazıyor:

> | Doğrudan API modeline geçmek | G-16/G-13 (veri dışarı çıkmaz) ürünün ana vaadi |

API modunu kalıcı yapmak, o reddi geri almaktır. Ürünün hastane müşterisine
verdiği sözü değiştirir. Bu yüzden Plan/Review kapısı değil, **Ship kapısıdır.**

## 3. Önkoşullar

Bunlar görüş değil, önkoşul. Hiçbiri kapanmadan seçeneklerden biri seçilirse
karar ölçüye değil izlenime dayanmış olur.

| # | Önkoşul | Durum (İP-33 sonrası, 2026-08-23) |
|---|---------|-----------------------------------|
| Ö-1 | İP-30 (`mask_context`) depoya itilmiş olmalı | ✅ **KAPANDI** — `c452c1c` |
| Ö-2 | Bağlam gizliliği testi yeşil olmalı | ✅ **KAPANDI** — `tests/test_api_modu.py` |
| Ö-3 | İP-31 kota koruması depoda olmalı | ✅ **KAPANDI** — `f7c2b85` |
| Ö-4 | Gemini koşumu tekrarlanmış olmalı | ✅ **KAPANDI** — 08-22 + 08-23 |
| Ö-5 | Aynı gün, aynı cetvel, eşli McNemar | ✅ **KAPANDI** — p = 1,000 |
| Ö-6 | Gemini'nin ücret/kota/erişim şartları **yazılı** olmalı | ❌ **AÇIK** — İhsan yazacak |
| Ö-7 | api koşumları tekrarlanabilir olmalı | ❌ **KAPANAMAZ** — aşağıya bak |

### Ö-6 — neden hâlâ açık ve neden nöbet kapatamaz

Ücret, kota ve erişim şartları bir ölçüm sorusu değil, bir **sözleşme**
sorusudur. Nöbetin ölçebileceği bir tarafı yok: fiyat listesi, ücretsiz
katmanın sınırları, model sürümünün haber verilmeden değişip değişmeyeceği,
ve veri işleyen sözleşmesinin (DPA/KVKK) mümkün olup olmadığı. Hastane
müşterisi için sonuncusu belirleyicidir.

### Ö-7 — belirlenim: bu sağlayıcıda mümkün değil (ölçüldü)

**Bulunduğunda (BULGU-08):** `generate_api` isteği yalnız `temperature`
taşıyordu; `seed` hiç gönderilmiyordu. Damga ise her koşumda `seed=42`,
`num_ctx=8192` yazıyor, **uygulanmamış bir kontrolü uygulanmış gösteriyordu.**
`config.py`'nin kendi yorumu şunu diyor:

> *"A/B karşılaştırması yapabilmek için üretim önce TEKRARLANABİLİR olmalı."*

api modunda o önkoşul hiç sağlanmıyordu ve damga sağlanıyormuş gibi
gösteriyordu. 7 soruluk oynama bunun ölçülmüş sonucudur, sürprizi değil.

**İP-33'te yapılan:** `seed` artık gerçekten gönderiliyor
(`generator.API_BELIRLENIM_ALANLARI`), damga metni **koddan türetiliyor** —
isteğin alan listesi değişirse damga kendiliğinden düzelir. `num_ctx`
OpenAI-uyumlu sözleşmede yok; damga artık onu iddia etmiyor.

**Sonra ölçülen (BULGU-17, aynı gün öğleden sonra):** `seed` eklenip
`doctor` koşulduğunda uç nokta isteği **tümden reddetti:**

```
HTTP 400  Invalid JSON payload received.
          Unknown name "seed": Cannot find field.
```

Gemini'nin OpenAI uyumluluk katmanında `seed` diye bir alan **yok.** Yani
api modunda belirlenim "doğrulanmamış" değil — **bu sağlayıcıda mümkün
değil.** Bu bir ayar meselesi ya da bizim ihmalimiz değil; sağlayıcının
sözleşmesinde olmayan bir şey.

Kod bunu bir kez öğrenip hatırlıyor (`generator._seed_kabul`) ve damga artık
şunu yazıyor: *"seed UYGULANAMIYOR — uç nokta bu alanı tanımıyor."*

**Ö-7 bu uç noktada kapanamaz.** Kapanmasının üç yolu var ve üçü de bir
KARAR gerektiriyor:

1. `seed` destekleyen bir sağlayıcıya geçmek (OpenAI, vLLM, birlikte
   barındırılan bir uç nokta) — ADR-5'in kendisini yeniden açar
2. Tekrarlanabilirliği tek koşumdan değil, **aynı gece n≥3 koşumun soru
   bazlı oy çokluğundan** almak — ölçüm maliyeti üçe katlanır
3. Ö-7'yi bir önkoşul olmaktan çıkarıp **kabul edilen bir maliyet** olarak
   yazmak — gerekçesiyle birlikte, § 6'da

Seçenek A ve B'nin "aleyhine" sütunu bu maddeyle ağırlaşıyor: api modunda
cetvel her koşumda oynuyor ve bunu düzeltmenin bir ayarı yok.

Ölçüm hattına bedeli vardı ve İP-33'te düzeltildi: SPEC A-4'ün "3 puandan
fazla düşerse CI kırmızı" kapısı bu gürültü tabanının **altındaydı** (saf
gürültüde ateşleme olasılığı ≈ %45). Kapı artık eşli McNemar kararına bağlı.
Ama bu, api modunun **tekrarlayan ölçüm maliyetini** ortadan kaldırmaz.

## 4. Seçenekler

### A — API varsayılan olur
Yerel mod opsiyonel kalır.
**Lehine:** doğruluk ~14 puan yüksek; donanım gereksinimi düşer, kurulum
kolaylaşır; G-12 rahatça karşılanır (yerel modda ölçülmek şartıyla — § 5).
**Aleyhine:** G-13/G-16 vaadi düşer; hastane müşterisinde DPA/KVKK gerekir;
kota ve fiyat dış bağımlılık olur; **model sürümü haber verilmeden
değişebilir** — bu artık bir risk değil, ölçülmüş bir olgudur: cetvel aynı
model adıyla, aynı ayarlarla, iki gece arasında 7 soruda oynadı.

### B — Yerel varsayılan kalır, API açıkça seçilir (çift mod)
Bugünkü kod zaten bunu yapıyor; karar onu **resmîleştirmek** olur.
**Lehine:** vaat bozulmaz; hız isteyen kullanıcı API'yi seçer; demoda API,
sahada yerel.
**Aleyhine:** iki mod da ölçülmek ve bakılmak zorunda — ölçüm maliyeti ikiye
katlanır (Ö-7 ile api tarafında daha da artar); G-12 yerelde hâlâ
karşılanmaz, yani hedef ya kalır ya değişir.

### C — Yerel kalır, G-12 hedefi revize edilir
**Lehine:** vaat bozulmaz; tek mod; ADR-1 rev.2'nin "hedefin korunması ayrı
bir karar gerektirir" notunun doğrudan cevabı.
**Aleyhine:** ürün yavaş kalır; İhsan'ı yoran şey aynen sürer; hedefi ölçüme
uydurmak, ölçümü hedefe uydurmanın aynasıdır — gerekçesi yazılmazsa bu
projenin kaçındığı hatanın ta kendisi olur.

### D — Katmanlı: açık çekirdek yerel, kurumsal katman API (DPA ile)
**Lehine:** çift lisans yapısıyla uyumlu; vaat açık çekirdekte korunur.
**Aleyhine:** en çok iş; iki dağıtım hattı, iki ölçüm hattı.

## 5. Nöbetin ölçüm notu (öneri değil, sınır)

- **%70,3 ile %56,4 karşılaştırılamaz.** Farklı model, farklı mod.
- **G-11 hedefi %80 aralığın dışında — API modu da G-11'i karşılamıyor.**
- **p95 3,76 / 4,81 sn G-12'yi karşılamaz, ölçmez bile.** G-12 ve v3 SPEC A-3
  hedefi *yerel çıkarım modu* içindir. Gecikme raporu iki gece "KARŞILANDI"
  yazdı; bu bir kapsam hatasıydı (BULGU-03) ve düzeltildi — api modunda rapor
  artık "KAPSAM DIŞI" yazıyor ve hüküm vermiyor. Ayrıca gereksinim "**en geç**
  10 sn" der ve 08-23'te bir soru **12,4 sn** sürdü. **G-12 hâlâ
  ölçülmemiştir.** Geçerli tek sayı yerelin p95'i: 21,2–32,8 sn.
- **Güvenilirlik API ile iyileşmedi, kötüleşti.** Yerel qwen'de yanlışların
  %95,5'i sessizdi; Gemini'de **%100** — iki gece de 0/101 soru reddedildi ya
  da patladı. Daha hızlı ve daha doğru bir model, hatalarını **tamamen
  görünmez** yapıyor.
- **B-7'nin saha sayısı %20'dir** (GA %9,5–37,3), mutasyon karnesindeki
  %80 değil; aralıklar kesişmiyor. Karar hangi yöne verilirse verilsin bu
  böyle. İP-33'ten sonra saha sayısı artık tahmin edilmiyor, denetim izinden
  sayılıyor (`audit.guven_karnesi()`).

## 6. Karar

**Boş.** İhsan doldurur.

```
Seçilen:            A / B / C / D / başka
Gerekçe:
Koda inecek yer:    app/config.py  (ADR koda inmezse karar değildir)
Geri alma koşulu:
```
