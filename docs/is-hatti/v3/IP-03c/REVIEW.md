# İP-03c — REVIEW (triyaj: İhsan)

**Kapsam:** B-7 sessiz yanlış azaltma · **Tarih:** 2026-08-16
**Durum:** Build ve Test bitti, Verify bitti. **Bu belge senin triyaj kapın.**

Triyaj sözlüğü: **BLOK** (ship'i durdurur) · **DÜZELT** (bu İP'te) ·
**SONRA** (backlog) · **KABUL** (gerekçe yazılmadan kabul edilmez).

---

## 0. Bir cümlede ne yapıldı

Sorgu çalıştıktan sonra koşan, modelin kendi güven beyanına hiç bakmayan,
LLM gerektirmeyen sekiz kontrol eklendi; kontrollerin **kendisi** 101 gold +
240 mutasyon üzerinde ölçüldü ve ölçüme göre ikisi varsayılan olarak kapatıldı.

---

## 1. Karar gerektiren bulgular

| # | Bulgu | Önerim | Senin triyajın |
|---|-------|--------|----------------|
| **B7R-01** | `sema_ortusmez` ve `bicim_sayi` varsayılan **kapalı** geliyor. Açıkken yakalama %82,5 / yanlış alarm %6,9; kapalıyken %81,2 / %1,0. | KABUL — gürültü kaçırmadan pahalı | ☐ |
| **B7R-02** | Yakalanan mutasyonların ölçüsü **bizim hayal ettiğimiz** hatalar üzerinde. Gerçek model hatalarındaki karne ancak Ollama'lı koşumda çıkar. | SONRA — bir sonraki 101'lik koşumda otomatik raporlanacak | ☐ |
| **B7R-03** | `where_dus` mutasyonlarının %43'ü hâlâ kaçıyor (31/54). Filtresiz sorgunun yanlış olduğunu ancak sorudaki daraltma işaretinden anlıyoruz; "Kadın hastaların sayısı" gibi sıfatla daraltılan sorularda işaret yok. | SONRA — İP-03d, soru→kolon eşleme gerektirir | ☐ |
| **B7R-04** | `preprocess.keywords` Türkçe **İ** ile başlayan her kelimenin ilk harfini yutuyordu (`İşlemlerin` → `şlem`). Düzeltildi. **RAG anahtar-kelime yolunu da etkiliyor**, yani doğruluk ölçümü bu düzeltmeden sonra tekrarlanmalı. | DÜZELT edildi; **ölçüm tekrarı gerekli** | ☐ |
| **B7R-05** | Güven bayrakları denetim izine (`audit`) yazılmıyor. Bugün yalnız kullanıcıya gösteriliyor. | SONRA — G-17 ile birlikte, İP-09 | ☐ |
| **B7R-06** | `bilinen_degerler` kolon **adıyla** anahtarlanıyor, `tablo.kolon` ile değil. Aynı adlı iki kolonun değerleri birleşiyor. Yanlış alarmı düşürür, kaçırmayı artırır. | KABUL — takas bilinçli, alternatifi takma ad çözümlemesi | ☐ |
| **B7R-08** | `atlanan_kolon` kontrolü (soruda adı geçen kolona sorgu hiç dokunmuyor) mutasyon karnesinde 5/0 çıktı ama mutasyonlar bu hata sınıfını **az temsil ediyor** — model bütün WHERE'i düşürmez, kavramı atlar. Yani sayı gerçek değerini göstermiyor olabilir. Varsayılan **açık**. | KABUL — ama gerçek koşumda izlenmeli | ☐ |
| **B7R-07** | `SORBI_ORNEK_DEGER=0` (API modu zorunluluğu) olduğunda `bilinen_degerler` boş kalır ve `bilinmeyen_deger` kontrolü **tümden susar**. API modunda B-7'nin en isabetli kontrolü yok. | **ÇÖZÜLDÜ** — kısıt yanlış katmandaydı. Örnekleme artık her zaman yapılıyor (yerel), `ORNEK_DEGERLER` yalnız İSTEME yazmayı kapatıyor. Veri hiçbir koşulda dışarı çıkmıyor, kontrol artık API modunda da çalışıyor. | ☐ onayla |

---

## 2. Kendi hatalarımız (bu turda yakalanan)

Testler ve mutasyon karnesi, yazdığım kodda **beş** kusur buldu:

1. `_TOPLAMA` sözlük sırası yanlıştı: "Ortalama yatış süresi **kaç** gün?"
   COUNT sanılıp AVG kullanan doğru sorguya bayrak konuyordu.
2. Terim sözlüğü eşleşmesi terimin kendisini şema tarafına yazmıyordu:
   `ciro` sözlükte tanımlıyken "ciro ne kadar" örtüşmez sayılıyordu.
3. `light_stem` asimetrisi (`randevusuna`→`randevus`, `randevu`→`randev`)
   doğrudan yanlış alarma dönüşüyordu — 12 gereksiz bayrağın 12'si.
4. `keywords` İ harfi kusuru (B7R-04).
5. `hangisi` tekil olmasına rağmen liste beklentisi kuruyordu.

Hiçbiri gözle bulunmadı; hepsi ölçümle bulundu.

---

## 3. Ölçülmeyen, dolayısıyla iddia edilmeyen

- Kullanıcının uyarıya **ne yaptığı**. Uyarı okunuyor mu, güveni artırıyor mu,
  yoksa gürültü olarak mı algılanıyor — bunu ölçmedik, ölçmeden iddia etmiyoruz.
- Gecikmeye etkisi. Kontroller LLM'siz ve tek geçişli; ölçülen ek maliyet
  soru başına 1 ms'in altında ama bu p95'e etkisi **ölçülmedi** demektir değil,
  ihmal edilebilir demektir. Gerçek koşumda görülecek.
