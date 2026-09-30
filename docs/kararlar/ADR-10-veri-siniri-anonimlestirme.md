# ADR-10 — Veri sınırı ve anonimleştirme: ne, nereye, hangi koşulda çıkar

**Durum:** **KABUL** (İhsan Arvas, 2026-09-30). Hazırlayan: Claude (güvenlik yöneticisi rolü).
**İlgili:** ADR-5 (B), ADR-8, ADR-9 · CLAUDE.md § 3.3 · SPEC E-1, E-2, E-6 · `docs/guvenlik/GUVENLIK.md`

## 1. Soru

SorBI yerel bir LLM ile çalışmadığında bir metin makineden çıkar. **Hangi veri, hangi
sınıra kadar, hangi koşulla çıkabilir; çıkarken neye dönüşür?**

## 2. Bağlam — Türkiye'de bu sorunun cevabını belirleyen dört kural

1. **Yabancı LLM API'si = yurt dışına aktarım, üstelik sürekli.** 7499 sonrası KVKK md. 9:
   yeterlilik kararı (bugün yok) ya da uygun güvence — pratikte **standart sözleşme**,
   imzadan itibaren **5 iş günü** içinde Kurul'a bildirim. Arızi hâller (tek seferlik
   açık rıza dahil) sürekli aktarıma dayanak olamaz.
2. **Sağlık verisi özel niteliklidir** (KVKK md. 6) ve Kurul'un 2018/10 kararındaki
   "yeterli önlemleri" ister: şifreli saklama, anahtarların ayrı tutulması, işlem kaydı,
   uzaktan erişimde iki faktörlü doğrulama, VPN/sFTP ile aktarım, periyodik yetki gözden
   geçirme. Yurt dışına aktarımı yine md. 9'a tabidir (Kişisel Sağlık Verileri Hk. Yön.).
3. **Kamu kurumu verisi** (2019/12 Genelge): kurumun kendi sistemi ya da kurum
   kontrolündeki yerli sağlayıcı dışında bulutta saklanmaz.
4. **Takma adlandırma anonimleştirme değildir.** Anahtar bizde durdukça veri bizim için
   kişisel veri olmaya devam eder. Takma adlandırma bir *en aza indirme* tedbiridir, bir
   *aktarım izni* değildir.

## 3. Karar

### 3.1 Veri sınıfları

| Sınıf | Ne | Örnek |
|---|---|---|
| **S0** | Sentetik / kamuya açık | demo veritabanları, SorBI'nin kendi istemleri |
| **S1** | Yapı metaverisi | ölçü/boyut adları ve gösterimleri, tablo/kolon adları |
| **S2** | Kişisel veri | soruda geçen ad, TCKN, telefon, IBAN; sözlükteki gerçek değerler |
| **S3** | Özel nitelikli kişisel veri | hastane veritabanının değerleri; sağlık bilgisiyle birlikte geçen kimlik |
| **S4** | Sır | API anahtarı, parola, bağlantı dizesi |

### 3.2 Sınırlar ve izin matrisi

| Sınır | S0 | S1 | S2 | S3 | S4 |
|---|---|---|---|---|---|
| **B0** — aynı makine (yerel LLM, DB, önbellek) | ✔ | ✔ | ✔ | ✔ | yalnız sır deposu |
| **B1** — müşterinin yurt içi, kendi kontrolündeki LLM sunucusu | ✔ | ✔ | ✔ takma adlı | ✔ takma adlı, **müşteri onayı + sözleşme** | ✘ |
| **B2** — yurt dışı LLM API'si | ✔ | ✔ | **yalnız takma adlı** | **✘ hiçbir koşulda** | ✘ |

Ve iki kilit:

- **B2 bugün yalnız sentetik demo veritabanında açıktır** (ADR-5 B, İP-45 — kodda). Bir
  müşteri veritabanı için B2'yi açmak **ADR-5 D** demektir; o gün standart sözleşme +
  5 iş günü bildirimi + veri işleme sözleşmesi (DPA) + bu ADR'nin S2 kuralı birlikte
  gelir. **Sağlık ve kamu müşterisi için B2 açılmaz** — bu, sözleşmeyle değil mimariyle
  kapalıdır.
- **S3 makineden ancak B1'e ve takma adlı çıkar.** Hastane pilotunun varsayılanı B0'dır.

### 3.3 Anonimleştirme yöntemi: izin listesi + geri dönüşlü yerel takma ad

B2'ye giden tek serbest metin **kullanıcının sorusudur** (sözlük zaten S1'e indirgenmiş
hâlde gider — İP-53a). Soru şu hattan geçer:

1. **Algıla.** Türkiye'ye özgü, *doğrulamalı* algılayıcılar: TCKN ve VKN (sağlama hanesi),
   TR IBAN (mod-97), kart numarası (Luhn), telefon, e-posta, plaka, IP, URL, uzun sayı
   dizileri, açık tarihler. Ayrıca **sözlükteki gerçek değerler** (S2/S3) ve **kişi adları**.
2. **Takma adla.** Her bulgu `[KISI_1]`, `[TCKN_1]`, `[DEGER_2]` gibi bir jetonla değişir.
   Eşleme tablosu **yalnız bellekte ve yalnız o istek boyunca** yaşar; diske, denetim
   izine ya da log'a yazılmaz.
3. **Özel adlar için izin listesi.** Büyük harfle başlayan ve izin listesinde olmayan her
   özel ad jetonlanır. İzin listesi: sözlüğün **adları ve gösterimleri** (S1), 81 il adı,
   ay/gün adları, SorBI'nin kendi terimleri. Reddetme listesi değil izin listesi: bir adı
   *güvenli olduğunu kanıtlayamıyorsak* dışarı yollamayız.
4. **Gönder, geri çevir.** LLM jetonu olduğu gibi kopyalar (`"degerler": ["[DEGER_1]"]`);
   jetonlar yerelde gerçek değere döner, sonra `Secim.kur` sözlüğe karşı doğrular.
5. **Çıkış kapısı (kapalı devre).** Dışarı giden **tüm** istek gövdesi, gönderilmeden hemen
   önce aynı algılayıcılardan bir kez daha geçer. Tek bir doğrulanmış bulgu kalmışsa
   istek **gönderilmez** ve kullanıcıya nedeni söylenir. Kapı `generator._api_chat`'in
   içindedir: SorBI'den dışarı giden her LLM çağrısı oradan geçer, v3 yolu dahil.

### 3.4 Kabul edilen artık risk (yazılı)

- **Küçük harfle yazılmış, listede olmayan bir kişi adı** ("ahmet yılmazın randevuları")
  yakalanmayabilir. Azaltma: yaygın Türkçe ad listesi + kesme işaretli özel ad kalıbı.
  Sıfırlanamaz; bu yüzden S3 zaten B2'ye hiç çıkmaz.
- **Bağlamsal yeniden tanıma**: jetonlanmış bir soru, nadir bir kombinasyonla ("tek
  kardiyoloji profesörü") bir kişiyi işaret edebilir. Tek soru, veri kümesi değil; risk
  düşük, sıfır değil. S3 için yine aynı cevap: B2 kapalı.
- **Sağlayıcı tarafında saklama**: B2'ye giden istek sağlayıcının log'larında kalabilir.
  Bu yüzden B2'ye giden içerik takma adlı olmak zorunda; ticari kullanımda sağlayıcının
  "veriyi eğitimde kullanmama ve saklamama" taahhüdü sözleşmeye girer.

## 4. Değerlendirilen seçenekler

| Seçenek | Neden seçilmedi |
|---|---|
| Kara liste (yalnız TCKN/telefon maskele — v3'ün yaptığı) | Ad, değer ve serbest özel ad sızar; bilinmeyeni geçirir |
| Tek yönlü maskeleme (`[MASKE]`) | LLM hangi değeri filtreleyeceğini kaybeder; doğruluk düşer, kullanıcı maskeyi kapatmak ister |
| Yerel NER modeli (spaCy/BERT TR) | Doğru yön, ama bugün bir model bağımlılığı ve ölçülmemiş bir hata oranı demek. Faz D'de izin listesinin **üstüne** eklenir, yerine değil |
| Her şeyi yerelde koş (API hiç yok) | Hastane için zaten bu. Demo ve ticari müşteri için hız farkı 6–8 kat (ADR-5) |

## 5. Koda inecek yerler

- `app/guvenlik/kisisel_veri.py` — algılayıcılar (doğrulamalı)
- `app/guvenlik/anonimlestirici.py` — takma adlama + geri çevirme, istek başına kasa
- `app/guvenlik/cikis_kapisi.py` — `generator._api_chat` başında kapalı devre denetim
- `app/baglanti/esleyici.py` — API modunda anonimleştiriciyi kullanır
- Testler: her algılayıcı için doğru/yanlış pozitif; kanarya (hiçbir S2/S3 değeri giden
  gövdede yok); çıkış kapısının v3 ve v4 istemlerinde **yanlış alarm vermediği**.

## 6. Geri alma

Kapı kapatılamaz (değişmez 3 gibi — bir ayara bağlanmaz). Yanlış pozitif bir algılayıcı,
kapıyı kapatarak değil algılayıcıyı düzelterek giderilir; o düzeltme kendi testiyle gelir.

## 7. Karar

```
Seçilen:            § 3 olduğu gibi
Karar veren:        İhsan Arvas
Tarih:              2026-09-30
```
