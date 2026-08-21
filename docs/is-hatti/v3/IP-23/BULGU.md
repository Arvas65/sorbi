# İP-23 — Cetvel çürüyordu

**Tarih:** 2026-08-20 · **Durum:** KAPANDI · **Nasıl bulundu:** oturum açılışında
karneyi rutin olarak tekrar koştururken

---

## 1. Belirti

Kod hiç değişmemişken mutasyon karnesi farklı bir sayı verdi:

| | 16 Ağustos | 20 Ağustos |
|---|---|---|
| Yakalanan | 199/240 | 198/239 |
| Gereksiz bayrak | 1 (%1,0) | 2 (%2,0) |

İki koşum arasında tek fark takvimdi.

## 2. Sebep

Test setinin **101 sorusundan 13'ü** zamana bağlı: `date('now')`,
`julianday('now')` kullanıyorlar ("geçen ay", "son 7 gün", "bugün bekleyen").
Demo verisi 2026-08-16'da tohumlandı ve orada bitiyor:

```
randevu.tarih   2025-02-22 .. 2026-08-16
fatura.tarih    2025-02-22 .. 2026-08-19
hasta.kayit     2025-02-22 .. 2026-08-16
yatis.giris     2025-02-22 .. 2026-08-14
```

Gerçek takvim ilerledikçe bu sorular sessizce boşalıyor. 20 Ağustos'ta
**"Bugün bekleyen kaç randevu var?" artık her koşumda 0 dönüyordu** — yani
o soru artık bir şey ölçmüyor, ve `bos_sonuc` kontrolü onu her seferinde
bayraklıyor.

Ayrıca `julianday('now')` günün SAATİNİ de içeriyordu: aynı gün sabah ve akşam
koşulan iki ölçüm bile birbirini tutmayabilirdi.

## 3. Neden ciddi

Kaç puanlık bir sapma olduğunu görmek için referans gününü ileri aldım:

| Referans günü | Gereksiz bayrak |
|---------------|-----------------|
| 2026-08-16 (veri seti günü) | 1 (**%1,0**) |
| 2026-08-20 (bugün) | 2 (%2,0) |
| 2026-12-01 (dört ay sonra) | 8 (**%7,9**) |

Aralık'ta koşulsaydı rapor **sekiz kat gerileme** gösterecekti ve tek sebep
takvimdi. Var olmayan bir hatanın peşine düşerdik.

Aynı sorun `evaluate.py`'yi de vuruyordu: doğruluk yüzdesi de bu 13 sorudan
etkileniyor, yani **iki günde alınmış iki accuracy sayısı karşılaştırılamaz**
durumdaydı — ve bunu hiçbir yerde yazmıyorduk.

## 4. Çözüm

- `config.BUGUN` / `SORBI_BUGUN` — ölçümlerin "bugün"ü. Boşsa gerçek tarih;
  **bozuk bir değerde sessizce bugüne düşmez, hata verir.**
- `eval/tarih_sabitle.py` — çalıştırma anında SQL'deki `'now'` argümanlarını
  referans güne çevirir. Yalnız fonksiyon argümanı konumundakiler; `WHERE
  durum = 'now'` gibi bir veri değeri korunur.
- Her iki koşucu da **varsayılan olarak** `2026-08-16`'ya sabitleniyor — kimsenin
  bayrak hatırlaması gerekmiyor. Unutulan bir bayrak, sessizce kayan bir cetvel
  demektir.
- Gold ve üretilen SQL **aynı** güne sabitleniyor. Soru ön işlemesi (G-07) de
  aynı günü kullanıyor: SQL'i sabitleyip istemi sabitlememek, modele Eylül'ü
  gösterip sorguyu Ağustos'ta koşturmak olurdu.
- Referans günü kanıt damgasına yazılıyor ve `karsilastirilamaz()` farklı güne
  sabitlenmiş iki koşumu **karşılaştırmayı reddediyor** — İP-23 öncesi koşumlar
  dahil, çünkü onlarda referans günü kayıtlı değil.

## 5. Kanıt

```
aynı gün, iki koşum        -> çıktılar birebir aynı
referans 2026-08-16        -> 199/239 yakalama, 1 gereksiz bayrak
referans 2026-08-20        -> 198/238, 2
referans 2026-12-01        -> 190/229, 8
```

Sayı artık referans gününün fonksiyonu; duvar saatinin değil.

**14 yeni test** (`tests/test_tarih_sabitle.py` + `test_eval_runner.py`).
Toplam **313 test**, ruff temiz, kapsam %75.

## 6. Ders

Ölçüm hattının kendisi de çürüyebilir ve çürürken hata vermez — tıpkı
kovaladığımız sessiz yanlış gibi. B-7'yi ürün için yazdık; bu, aynı hastalığın
ölçüm aracındaki hâliydi.

Kalan risk: veri seti yenilenirse `VARSAYILAN_GUN` sabiti de güncellenmeli.
Unutulursa görünür olsun diye referans günü hem koşum başlığına hem kanıt
damgasına yazılıyor.


---

# EK — 2026-08-21: düzeltmenin kendisi eksikti

İhsan'ın makinesinde ilk temiz koşum alındı ve **iki bulgu daha** çıktı.
İkisi de İP-23'ün ilk sürümünün kendi kusuruydu.

## EK-1. Referans gün SABİT'ti, oysa VERİYE ait bir sayı

İlk düzeltme referans günü `VARSAYILAN_GUN = "2026-08-16"` diye kodladı.
O tarih **benim** demo veritabanımdan geliyordu. İhsan'ın kopyası başka bir
günde tohumlanmıştı; aynı sabit onun makinesinde üç soruyu boşa düşürdü:

| | benim kopyam | İhsan'ın kopyası |
|---|---|---|
| gereksiz bayrak | 1 (%1,0) | **4 (%4,0)** |
| mutant | 239 | 236 |

Üç yanlış alarmın üçü de zamana bağlı soruydu (24, 88, 89) ve `sifir_toplama`
onları haklı olarak bayrakladı — çünkü cevapları gerçekten sıfırdı. Kontrol
doğru çalışıyordu; **cetvel yanlıştı.**

Yani ilk düzeltme hatayı kaldırmadı, taşıdı: takvimden makineye.

**Şimdiki hâli:** `veri_gunu()` referans günü veritabanından türetiyor —
*her canlı tablonun hâlâ kaydı olduğu son gün*. Genel maksimum değil, çünkü
tablolar farklı günlerde bitiyor (fatura 19'unda, randevu 16'sında, yatış
14'ünde); maksimumu seçmek "bugün bekleyen randevu"yu boşa düşürürdü.
Doğum ve işe başlama gibi nitelik tarihleri eleniyor.

Benim kopyamda türetilen gün: **2026-08-14**, ve 13 zamana bağlı sorunun
tamamı dolu dönüyor.

**Ayrıca koşum artık kendi kendini denetliyor:** zamana bağlı sorulardan
kaçının boş döndüğü sayılıyor ve sıfırdan farklıysa uyarı basıyor. Bu kontrol
olsaydı İhsan'ın koşumu sebebi kendisi söylerdi.

## EK-2. `kontrol.bat` sabit sayı bekliyordu — aynı hata

Betiğe beklenen karne sayılarını gömmüştüm. Aynı gerekçeyle yanlış: o sayılar
benim verime aitti. Artık karne **kendi geçmişiyle** karşılaştırılıyor
(`docs/kanit/KARNE-GECMIS.log`, ekle-only) ve betik yalnız makineden bağımsız
olanları denetliyor (test sayısı, 101 soru, `zbos=0`).

## EK-3. Bonus bulgu: ADR kâğıtta kalmış

`--doctor` çıktısı `Model: llama3.2:3b` dedi. Oysa **ADR-1 rev.2 taban modeli
`qwen2.5-coder:7b-instruct` olarak belirlemişti** — ölçümle, McNemar
p = 2,8×10⁻⁴ ile. Karar 16 Ağustos'ta yazıldı, `config.LOCAL_MODEL`'e hiç
inmedi.

Tam ölçüm bu hâliyle alınsaydı ~%38 çıkacaktı ve %62'lik tabana göre
**24 puanlık hayali bir gerileme** raporlanacaktı. Günlerce yanlış yerde
hata aranırdı.

Düzeltildi; ve `tests/test_adr_uyumu.py` ADR-1'in "Karar" bölümünü okuyup
`config.LOCAL_MODEL` ile karşılaştırıyor. ADR değişirse test kırılır, yani
karar bilinçli olarak koda inmek zorunda.

## Ders

Üçü de aynı aileden: **bir yerde yazılı olan şeyin başka bir yerde geçerli
olduğunu varsaymak.** Sabit bir tarih başka bir veritabanında geçerli değil;
bir ADR'de yazan model `config.py`'de geçerli değil; benim makinemde ölçülen
sayı senin makinende geçerli değil.

Çare her seferinde aynı: varsayımı çalıştırılabilir bir kontrole çevir.
