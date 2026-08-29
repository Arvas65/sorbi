# SorBı v4 — SPEC

**Sürüm:** taslak 1.0 · **Tarih:** 2026-08-28 · **Karar sahibi:** İhsan Arvas
**Durum:** ONAYLANDI (İhsan, 2026-08-29) · **Revizyon 1.1** (2026-08-29: A-5'in
anlam modeli yolu `.sorbi/` yerine `anlam/` oldu — gerekçe ADR-9 §2a; İP-46
sırasında İP sınırı bir tık genişledi, aşağıda not edildi)
**Girdi:** INTENT/CLARIFY belgesi (proje `claude/27`) + İhsan'ın dört CLARIFY cevabı
**Sayfa hâli:** https://claude.ai/code/artifact/aea2cf9a-4089-4b3b-af90-201dced8c048

---

## 1. Amaç (Intent)

SorBı bugün yalnız kendi demo şemasında çalışıyor. Yeni bir işletmenin
veritabanında ne tabloların ne kolonların ne anlama geldiğini bilemez, çünkü
**anlam şemada yazmaz.** Bugünkü doğruluk sayısı bu yüzden taşınabilir değil ve
ürün tek bir müşteriye kurulamaz.

**v4 bittiğinde:** daha önce hiç görülmemiş, salt-okunur bir veritabanına
bağlanıp **en fazla yarım saatlik bir etiketleme oturumu** sonunda Türkçe iş
sorularına **pano** üretilebilecek — her sayının arkasındaki tanım ve SQL
görünür, emin olunmayan sayı işaretli, hiçbir veri satırı ne modele gider ne
diske yazılır.

**Bunu şuradan anlayacağız:** ekip dışından biri kendi veritabanını bağlar,
sihirbazı tek oturumda bitirir, üç iş sorusu sorar, üç pano alır. Kanıt: oturum
kaydı, anlam modeli sürümü ve insanın değiştirmeden kabul ettiği öneri oranı.

---

## 2. Kararlar (CLARIFY çıktısı)

| # | Karar | Sonucu |
|---|-------|--------|
| K-1 | **Modül = kalıcı iş alanı ekranı** | SorBı bir "çalışma alanı" kavramına sahip olacak. **Tanım şimdi sabitlenir, inşası v5'te** — v4 veri yapıları bunu sonradan mümkün kılmak zorunda (G-1). |
| K-2 | **Anlam modeli müşterinin makinesinde dosya** | `anlam/<baglanti>.json`, sürümlü, git'lenebilir. Salt-okunurluk bozulmaz; model müşteriye ait olur. |
| K-3 | **Değer sözlükleri insan onaylı** | Onaysız hiçbir değer modele gitmez. Doğruluk ve gizlilik aynı mekanizmayla çözülür (E-1). |
| K-4 | **v4 = anlam katmanı + pano** | Tahmin ve modül ekranı v5'e. Tahmin, anlam katmanı oturmadan *yanlış seriyi* tahmin eder. |
| K-5 | **Model SQL yazmaz; seçim yapar, SQL derlenir** | Taşıyıcı mimari kararı. Yeni ADR-8. |
| K-6 | **Cetvel dört katmana ayrılır** | Birincil cetvel *eşleme* (Katman 3); 101 soruluk set Katman 4'e iner. |
| K-7 | **ADR-5 = B** (yerel varsayılan, API açık seçim) | v4'ün ön koşulu; `config.py`'ye iner (E-6). |
| K-8 | **Turun çıkış koşulu SPEC'te yazılıdır** | v3'ün tek yapısal hatasının kapatılması (§7). |

**Varsayımlar (doğrulanacak):** V-1…V-8, `claude/27` belgesinde yazılı.

---

## 3. Devralınan açık borç

Ciddiyeti değişen maddeler. Sebep tek: artık müşteri veritabanına bağlanıyoruz.

| Madde | v3 | v4 |
|---|---|---|
| G-14 zaman aşımı (B-2) | Yüksek | **BLOK** — yabancı DB'de sınırsız sorgu kabul edilemez |
| G-14 salt-okunurluk (B-3) | Yüksek | **BLOK** — ana vaat temenniyle korunamaz |
| Durum yalıtımı (C-1) | BLOK | **BLOK** — artık yanlış DB değil **yanlış anlam** demek |
| Ö-1 / Ö-2 | ADR-5 önkoşulu | E-1'in içine alınır, kanaryayla kapanır |
| BULGU-15 (admin parolası) | Açık | SPEC dışı — İhsan'ın işi, v4'ü beklemez |
| BULGU-18 (cetvel fazla kolon) | Açık | F-4 içinde kapanır |

---

## 4. Kapsam

### A · Anlam katmanı

> **İP sınırı notu (Build, 2026-08-29).** A-1 ile B-1 arasındaki sınır bir tık
> kaydı: `Secim`in VERİ TİPİ İP-46'ya alındı, çünkü `portlar.py` ona tip olarak
> ihtiyaç duyuyor ve döngüsel bir bağımlılık doğardı. Derleyici (B-2) ve 40
> altın çift İP-47'de kaldı — kapsam değil, sıralama değişti.

**A-1 · Anlam modeli şeması ve sürümleme.** `anlam.py` bir `AnlamModeli` veri
sınıfı tanımlar: tablolar (tür, tane, olay tarihi, geçerlilik, ilişkiler),
ölçüler (ifade, birim, toplama, kaynak), boyutlar (kolon, gösterim, sözlük),
maskeli kolonlar. Her onay sürümü artırır.
*Kabul:* `dogrula()` eksik zorunlu alanı **adıyla** reddeder (tane, olay tarihi,
geçerlilik zorunlu); JSON şeması depoda; `tests/test_anlam_semasi.py` geçerli +
6 geçersiz model üzerinde. Kapalı devre: fırlatmaz, `gecersiz` listesi döndürür.

**A-2 · Şemadan ön-doldurma.** Bağlantı kurulunca model **doldurulmuş hâlde**
önerilir: FK'lerden ilişkiler; ad kalıplarından olay/varlık; tarih kolonu
adayları sıralı; `iptal · silindi · durum · aktif · test` kalıplarından
geçerlilik adayı; sayısal kolonlardan ölçü adayları.
*Kabul:* Hiçbir öneri "kesin" işaretlenmez. `tests/test_on_doldurma.py` iki altın
şemada (hastane SQLite + satış). FK'siz şemada ilişki önerisi ad benzerliğinden
gelir ve **"düşük güven" damgalıdır.**

**A-3 · Etiketleme sihirbazı — tablo başına beş soru.** (1) olay mı varlık mı ·
(2) bir satır neyi temsil ediyor · (3) "ne zaman oldu"nun tarih kolonu · (4)
hangi satırlar sayılmamalı · (5) hangi kolonlar ölçü, hangileri boyut. Her
adımda A-2'nin önerisi ön-seçili.
*Kabul:* 20 tablolu demo şemada oturum **tek seferde** bitirilebilir. "Atla"
mümkün; **etiketlenmemiş tablo sorguya girmez ve bu kullanıcıya yazılır**
(Değişmez #6). Çıktı insan okunabilir JSON + Türkçe açıklama (V-3).

**A-4 · Değer sözlüğü onayı (K-3).** Kardinalitesi eşiğin altındaki metin
kolonlarının değerleri sihirbazda **insana** gösterilir; insan onaylar.
*Kabul:* Onaylanmamış hiçbir değer `boyutlar[].sozluk` içinde bulunmaz; E-1
kanaryası kapsar. Eşik yapılandırmadan okunur, sabit kodlanmaz.

**A-5 · Dosya, sürüm geçmişi ve şema kayması.** Model
`anlam/<baglanti>.json`; önceki sürümler `anlam/gecmis/`. Kaynak şema
değişirse sihirbaz **yalnız farkı** sorar.
*Kabul:* Kolon eklenip sihirbaz açıldığında yalnız o kolonun soruları görünür;
`tests/test_anlam_dosyasi.py` sürüm artışını, geçmişi ve fark tespitini
doğrular. Silinen kolona dayanan ölçü **bozuk** işaretlenir; o ölçüyü kullanan
seçim reddedilir.

### B · Seçim ve derleyici

**B-1 · Seçim nesnesi.** `Secim`: ölçüler, boyutlar, filtreler, zaman (tane +
aralık), sıralama, limit. Anlam modelinde olmayan adla kurulamaz.
*Kabul:* Bilinmeyen adda istisna fırlatılmaz; `gecersiz` dolar, hat durur.
`to_json()/from_json()` vardır ve model sürümünü taşır (G-1 ön koşulu).

**B-2 · Derleyici — `derleyici.py`.** `Secim` + `AnlamModeli` → SQL. Otomatik ve
zorunlu: geçerlilik filtresi eklenir (eksen 8, unutulamaz) · doğru olay tarihi
kullanılır (eksen 7, seçilemez) · JOIN yolu modelin ilişkilerinden gelir
(uydurulamaz) · toplama kuralı uygulanır, **ortalamanın ortalaması reddedilir** ·
sqlglot ile lehçeye çevrilir (ADR-4) · derlenen SQL **yine de** `validator.py`'den
geçer.
*Kabul:* En az **40 altın çift** (`Secim` → beklenen SQL), LLM'siz, CI'da
saniyeler. Her çift yukarıdaki altı maddeden en az birini sınar. Fan-out üreten
seçim reddedilir ve nedeni yazılır (R-3).

**B-3 · Karşılanamayan soru → ölçü önerisi.** `Secim` kurulamıyorsa sistem eksik
olanı **adlandırır** ve bir ölçü/boyut önerisi üretir; insan onaylarsa model
sürüm atlar.
*Kabul:* Reddedilirse soru **"ifade edilemedi"** olarak kapanır — tahmine dayalı
cevap üretilmez. Oran ölçülür ve kanıta yazılır (R-2 göstergesi).

**B-4 · Serbest SQL kaçış kapısı (V-6).** v3'ün yolu korunur, varsayılan kapalı.
*Kabul:* Açıldığında sonuç "anlam modeli dışı — düşük güven" damgalı; denetim
izine ayrı tür olarak yazılır; kapalıyken erişilemediğini gösteren test var.

### C · Eşleme — LLM'ye kalan tek iş

**C-1 · Soru → Seçim eşleyici.** İstem yalnız anlam modelinin **sözlüğünü**
içerir: ölçü adları, boyut adları, onaylı değer sözlükleri, zaman taneleri. Şema
metni, örnek satır, SQL örneği yok. Modelden SQL istenmez.
*Kabul:* Çıktı `Secim` JSON şemasına uyar; uymazsa **bir** düzeltme turu, sonra
red. İstem gövdesinin anlık görüntü testi, ham şema metni ya da veri değeri
bulunmadığını doğrular.

**C-2 · Netleştirme turu — G-03'ün gerçek hâli.** v3'te sistem soru sormuyordu ve
kullanıcı netleştirse bile cevabı kullanmıyordu. Artık en fazla bir tur soru
sorulur ve cevap seçime bağlanır.
*Kabul:* Belirsiz soruda seçenekler sorulur; cevap `Secim`'e girer; testi var.

**C-3 · Zaman tanesi çözümü.** `preprocess.resolve_dates` çıktısı
`Secim.zaman`'a bağlanır.
*Kabul:* Referans günü **sabit kodlanmaz** (İP-23 dersi); ölçümde
`tarih_sabitle.py` üzerinden gelir. Çözülen aralık kullanıcıya *varsayım* olarak
gösterilir.

### D · Pano

**D-1 · Deterministik grafik seçimi.** Grafik tipi sonucun şeklinden türetilir
(`claude/26` §04 tablosu koda iner). Model grafik tipi söylemez.
*Kabul:* `tests/test_pano_secimi.py` tablodaki her satır için bir vaka. Bir
erişim testi, grafik tipinin hiçbir kod yolunda LLM çıktısından okunmadığını
zorlar.

**D-2 · Filtre şeridi anlam modelinden türetilir.** Düşük kardinalite → çoklu
seçim, tarih → aralık. Sabit kodlanmış filtre yok.
*Kabul:* İki farklı şemada filtre şeridi **kod değişmeden** farklı çıkar.

**D-3 · Eksik parça görünür (V-5).** Reddedilen parça olmadan pano kurulur,
eksikliği yazılır.
*Kabul:* Sessiz boş kart üretilemez; kasten bozulmuş planla test koşar.

**D-4 · Güven bayrakları panoya taşınır.** `guven.degerlendir` çıktısı kart
düzeyine iner.
*Kabul:* Mesaj kullanıcıya, kod denetim izine (B7R-05 kalıbı korunur).

**D-5 · Her sayının arkası görünür — G-02'nin panoya taşınması.** Kart başına:
kullanılan ölçü tanımı, uygulanan geçerlilik filtresi, derlenen SQL.
*Kabul:* Hata durumunda da gösterilir (Değişmez #2). Tanım anlam modelinden
okunur, yeniden yazılmaz.

### E · Sınırlar ve güvenlik

**E-1 · Sınır 1 — veri modele hiç gitmez.** Geçen: tablo/kolon adları, tipler,
ilişkiler, anlam modeli, **onaylı** değer sözlükleri. Geçmeyen: hiçbir veri
satırı, hiçbir örneklenmiş değer.
*Kabul — kanarya testi:* Demo DB'ye eşsiz dize ekilir (`ZQX-KANARYA-7731`); tam
oturum koşturulur (etiketleme + üç pano); **giden tüm istek gövdelerinde**
aranır. Bulunursa kırmızı. Ayrıca gövde anlık görüntü testi. Ö-1 ve Ö-2 burada
kapanır.

**E-2 · Sınır 2 — veri hiçbir yere yazılmaz.** Sonuç satırları yalnız bellek içi
önbellekte: anahtar (bağlantı + SQL özeti + model sürümü), TTL'li, oturum
sonunda boşalır. Denetim izine soru, seçim, model sürümü, derlenen SQL, **satır
sayısı**, süre, bayraklar girer.
*Kabul:* Aynı kanarya **diskte** aranır: denetim izi, log, önbellek klasörü,
geçici dosyalar. Bulunursa kırmızı. Önbelleğin oturum sonunda boşaldığı ayrıca
sınanır.

**E-3 · G-14 her lehçede gerçek olur. — BLOK** Postgres `statement_timeout`,
MySQL `max_execution_time`, MSSQL sorgu zaman aşımı; oturum düzeyinde salt-okunur
işlem; bağlantı testinde **yazma denemesi**.
*Kabul:* Docker Postgres'te `pg_sleep(60)` 30 sn içinde `ZAMAN_ASIMI`. Yazabilen
hesapla bağlanınca kırmızı uyarı + "riskli" işaret + denetim kaydı. MSSQL
sınanamazsa **"doğrulanmadı" damgalanır** — sessizce geçilmez.

**E-4 · Durum yalıtımı. — BLOK** Süreç genelindeki `config.DB_URL` mutasyonu ve
`pipeline._index` tekili kaldırılır; bağlantı **ve anlam modeli** oturum bağlamı
nesnesiyle taşınır.
*Kabul:* İki bağlantı + iki anlam modeliyle eşzamanlı çağrı testi: her cevap
kendi veritabanından **ve kendi anlamından** gelir.

**E-5 · G-16 maskeleme anlam modeline taşınır (V-7).** Maskeli kolona dokunan
seçim **derleme anında** reddedilir.
*Kabul:* Maskeli kolonu isteyen seçim SQL'e hiç dönüşmez; gerekçe kullanıcıya
yazılır. `SELECT *` yoluyla ulaşma denemesi de reddedilir (BULGU-18 §2, #61).

**E-6 · ADR-5 kararı koda iner (K-7).** Yerel varsayılan; API modu açıkça
seçilir ve **müşteri bağlantısında kapalıdır.**
*Kabul:* `config.py` varsayılanı yerel; demo dışı bağlantıda API modunun
açılamadığını gösteren test. ADR-5'in karar bölümü doldurulur (gerekçe + geri
alma koşulu).

**E-7 · Denetim izi genişler.** Kayda soru, `Secim`, model sürümü, derlenen SQL,
satır sayısı, süre, bayraklar girer. Hash zinciri (v3 B-5) bu turda kapsam dışı.
*Kabul:* Bir sorunun tüm aşamaları tek korelasyon kimliğiyle izlenir; kayıtta
hiçbir veri satırı yok.

### F · Cetvel

**F-1 · Katman 1 — derleyici cetveli.** *Kabul:* ≥ 40 altın çift, LLM'siz, her
PR'da, saniyeler. Kırmızıysa birleştirme yok.

**F-2 · Katman 2 — etiketleme cetveli.** Önerilen alanların kaçının
**değiştirilmeden** kabul edildiği sayılır. Ürünün ticari değerinin ölçüsü.
*Kabul:* Oturum sonunda oran `docs/kanit/etiketleme-<tarih>.md`'ye yazılır: şema
adı, tablo sayısı, alan sayısı, kabul oranı, süre. Ekle-only (Değişmez #5).

**F-3 · Katman 3 — eşleme cetveli (yeni birincil ölçü).** Türkçe soru → doğru
ölçü / boyut / filtre / zaman tanesi seçildi mi? **Bileşen bileşen** puanlanır.
*Kabul:* ≥ 60 soru × 2 şema; rapor her bileşen için ayrı oran verir ("ölçü %92,
tane %71, tarih %88"). Şemadan bağımsızlığı, ikinci şemada kod değişmeden
koşarak gösterilir.

**F-4 · Katman 4 — eski set korunur + BULGU-18 kapanır.** *Kabul:* 101 soruluk
set birincil olmaktan çıkar ama koşmaya devam eder; `dogru` yanına
`dogru_toleransli` eklenir, rapor **iki sayıyı birden** yazar. 08-16'dan bu yana
karşılaştırılabilirlik korunur.

**F-5 · Kanıt damgası model sürümünü taşır (V-4).** *Kabul:* Farklı anlam modeli
sürümleriyle alınmış iki ölçüm `karsilastirilamaz()` tarafından reddedilir;
testi var. Kural skill'de değil **kodda** (§7 dersi).

**F-6 · Koşum kadansı haftalığa iner.** *Kabul:* 03:00 `schtasks` görevi
kapatılır; haftalık elle tetiklenen koşum kurulur; `kontrol.bat` açılışta son
koşumun kaç gün önce olduğunu **bağırır**.

### G · Modül — v5, ama engellenmez

**G-1 · İleri uyum (K-1).** Modül ekranı v4'te yapılmaz, ama v4 veri yapıları
onu sonradan mümkün kılmak zorundadır: `Secim` ve pano planı adlandırılabilir,
serileştirilebilir, anlam modeli sürümüne bağlıdır.
*Kabul:* `Secim.to_json()/from_json()` gidiş-dönüş testi; sürüm uyumsuzluğunda
açık ve okunabilir hata. Saklama arayüzü yoktur — veri yapısı hazırdır.

### H · Taşınabilirlik ve kabul

**H-1 · İkinci lehçe: gerçek Postgres (V-1).** *Kabul:* Docker Compose ile ayağa
kalkar; A-2, B-2, E-3 orada da koşar. ADR-4 ilk kez gerçekten sınanır.

**H-2 · İkinci şema: satış.** *Kabul:* `demo/seed_satis.py` üzerinde etiketleme +
pano uçtan uca; hastane şemasına özgü hiçbir kod yolu kalmadığı gösterilir.

**H-3 · Kabul demosu. — ÇIKIŞ KOŞULU** *Kabul:* Ekip dışından biri **tanımadığı**
bir veritabanını bağlar · sihirbazı **≤ 30 dakikada** bitirir · üç iş sorusu
sorar · **üç kullanılabilir pano** alır · **hiçbir elle düzeltme yapılmaz.**
Oturum kaydedilir; kanıt damgası anlam modeli sürümünü taşır.

---

## 5. Kapsam dışı — bilinçli olarak yapılmayacaklar

| Ne | Gerekçe | Ne zaman açılır |
|---|---|---|
| **Tahmin (forecasting)** | Anlam katmanı oturmadan yanlış seriyi tahmin eder; kendi cetvelini gerektirir | v5 — tasarımı `claude/27` §06'da hazır |
| **Modül ekranı / çalışma alanı** | Tanımı sabitlendi (K-1), inşası ayrı bir üründür; G-1 kapıyı açık tutuyor | v5 |
| **Çoklu olay tablosu (multi-fact)** | Fan-out ve chasm tuzakları derleyiciyi katlar. v4 kapsamı: **tek olay tablosu + ona bağlı boyutlar** | v5 — R-3 |
| **FastAPI çekirdeği (v3 C-2)** | Anlam katmanı zaten arayüzden bağımsız bir kütüphane; HTTP katmanı kabul demosuna hiçbir şey katmıyor | Entegrasyon talebi gelince |
| **G-17 hash zinciri (v3 B-5)** | Kabul kriterinde yeri yok; E-7 içeriği genişletiyor, imzalamıyor | v5 / kurumsal katman |
| **QLoRA fine-tune (ADR-2)** | Anlam katmanı, fine-tune'un çözeceği hataların çoğunu *imkânsız* kılıyor — gerekçe zayıfladı | F-3 eşleme tarafında darboğaz gösterirse |
| **React yeniden yazımı** (V-2) | Doğruluk kanıtlanmadan arayüz yatırımı erken | v5 sonrası, talep gelirse |
| **Çok kiracılı SaaS · İngilizce soru · zamanlanmış rapor** | v3'te de kapsam dışıydı; karar değişmedi | Kurumsal katman |

---

## 6. Etkilenen kapılar, ADR'ler, riskler

### G-kapıları

| Kapı | v4'teki durumu |
|---|---|
| G-02 | Panoya taşınır (D-5) — kart başına tanım + SQL |
| G-03 | **İlk kez gerçekten uygulanır** (C-2) |
| G-11 | Birincil ölçü değişir: Katman 3 eşleme (F-3). %80 eşiği **yeni birime taşınmaz** — yeni taban ölçülür, hedef sonra konur |
| G-12 | Pano bütçesi olarak yeniden tanımlanır: ilk KPI ≤ 5 sn, tam pano ≤ 20 sn (`claude/26` §05); gerekçesi ADR'ye yazılır |
| G-13 · G-16 | Sınır 1 / Sınır 2 ve E-5 ile kodda zorlanır, kanaryayla sınanır |
| G-14 | E-3 — **BLOK** |
| G-18 | Korunur; derlenen SQL de validator'dan geçer |

### ADR'ler

- **ADR-1 rev.2** korunur · **ADR-4** ilk kez gerçekten sınanır (H-1)
- **ADR-5** karara bağlanır: **B**, koda iner (E-6)
- **ADR-2** (QLoRA) gerekçesi zayıflar
- **YENİ ADR-8** — anlam katmanı: model SQL yazmaz, seçim yapar (K-5)
- **YENİ ADR-9** — anlam modelinin saklanma yeri ve sürümlenmesi (K-2)

### Riskler

| # | Risk | Etki | Azaltma |
|---|---|---|---|
| R-1 | Etiketleme yükü yarım saati aşar | Kabul demosu düşer | F-2 bunu **ölçüyor**. Aşarsa ön-doldurma iyileştirilir ya da kapsam "ilk N tablo"ya daraltılır — kabul kriteri düşürülmez, kapsam daralır |
| R-2 | Anlam modelinin ifade gücü yetmez | Ürün kullanışsız hissettirir | B-3 öneri döngüsü + B-4 kaçış kapısı; oran ölçülür ve kanıta yazılır |
| R-3 | Derleyici karmaşıklığı patlar (fan-out, chasm trap) | Sessiz yanlış **derleyicide** doğar — en kötü yer | v4 kapsamı tek olay tablosu (§5). Çoklu olay üreten seçim **reddedilir**, sessizce yanlış birleştirilmez |
| R-4 | Gerçek Postgres/MSSQL ortamı yok | E-3 doğrulanamaz | Postgres Docker; MSSQL sınanamazsa "doğrulanmadı" damgası |
| R-5 | Qlik görüşmesi takvimi sıkışır | Kapsam baskısı | H-3 tek şemayla alınabilir ve **"kısmi" damgalanır**. Kabul kriterinin metni değişmez — "hedefi ölçüme uydurma" hatası tekrarlanmaz |
| R-6 | İnsan etiketlemeyi yanlış yapar (yanlış tane/geçerlilik) | Tüm cevaplar tutarlı biçimde yanlış — **en tehlikeli sessiz yanlış** | Sihirbaz her cevap için satır sayısı gösterir ("bu filtreyle 12.480 satır kalıyor, 1.204 satır düşüyor"); insan sağlamayı gözle yapar. Tasarım gereği |

### Geri alma

Her İP kendi dalında; master'a yalnız Ship kararıyla girer. Anlam katmanı bir
yapılandırma anahtarıyla kapatılabilir ve sistem v3'ün serbest-SQL yoluna döner
(B-4 zaten o yol) — pilot kurulumda sorun çıkarsa sürüm geri alınmadan
kapatılabilir.

---

## 7. Çıkış koşulu (K-8)

v4, aşağıdaki beşi **aynı oturumda** gerçekleştiği gün biter. Biri eksikse
bitmez; hepsi varsa uzatılmaz.

1. Ekip dışından biri, **tanımadığı** bir veritabanını salt-okunur bağlar
2. Etiketleme sihirbazını **≤ 30 dakikada** bitirir
3. Üç Türkçe iş sorusu sorar
4. **Üç kullanılabilir pano** alır — elle düzeltme yok
5. Kanarya testi yeşil: hiçbir veri ne dışarı gitti ne diske yazıldı

**Bu SPEC'in tamamlanma tanımı:** her gereksinimin kabul kriteri var ✔ · kapsam
dışı bölümü boş değil ✔ · her kriter bir testle ya da ölçümle doğrulanabilir ✔ ·
çıkış koşulu yazılı ✔

---

## 8. Sıradaki adım

```
INTENT ✔   CLARIFY ✔   SPEC ◀ buradayız — düzeltme bekleniyor
  →  PLAN  →  [KAPI 1 — ONAY, İhsan]  →  BUILD
  →  BAĞIMSIZ REVIEW  →  [KAPI 2 — TRİYAJ, İhsan]  →  TEST  →  VERIFY
  →  [KAPI 3 — SHIP, İhsan]
```

SPEC düzeltilip onaylanınca **PLAN** gelir: adım listesi, bağımlılıklar, her
adımın yazarı (İhsan / Claude), dokunulacak dosyalar, geri alma yolu, tahmini
süre. PLAN **Kapı 1**'dir — onay olmadan tek satır kod yazılmaz.
