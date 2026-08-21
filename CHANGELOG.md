# Değişiklik Günlüğü

Bu dosyanın biçimi [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) esaslıdır ve
sürümleme [Semantic Versioning](https://semver.org/lang/tr/) izler.

Her sürüm, iş hattının Ship kapısından (`docs/is-hatti/00-IS-HATTI.md` § 9) geçerek çıkar.

---

## [Yayınlanmamış]

### Eklendi
- `pyproject.toml`: proje metaverisi, ruff yapılandırması, pytest ve kapsam ayarları
- Katmanlı ve **pinlenmiş** bağımlılıklar (`requirements/`): `core` · `rag` · `ui` · `dev` · `drivers`.
  Tek sürüm kaynağı `all.txt`; katmanlar ona kısıtlanır, çelişen pin oluşamaz.
  Aynı commit iki kez kurulduğunda aynı sürümler gelir.
- GitHub Actions CI: ruff → pytest (Python 3.10/3.11/3.13) → `--gold-only` eval → Docker derlemesi.
  Hiçbir adım gerçek bir LLM servisi gerektirmez.
- `docs/is-hatti/`: iş hattı operasyon modeli, v3 SPEC ve PLAN, backlog

### Değiştirildi
- İçe aktarım sırası, kullanılmayan içe aktarımlar ve belirsiz değişken adları düzeltildi
  (ruff otomatik düzeltmesi + elle; **davranış değişikliği yok**)
- `app/schema_rag.py`: koleksiyon adı üreten MD5 çağrısı `usedforsecurity=False` ile
  işaretlendi — güvenlik amaçlı olmadığı artık kodda yazıyor
- `Dockerfile`: pinlenmiş kilit dosyalarını kullanıyor

### Düzeltildi (belge)
- **README'nin "QLoRA fine-tune" bölümü kaldırıldı.** Anlattığı `training/` klasörü ve
  içindeki iki script depoda hiç bulunmuyordu. Klasör yapısı listesinden de çıkarıldı.
  QLoRA kararı ADR-2'ye bağlıdır ve baseline ölçümü (İP-03) sonrası yeniden açılacaktır.
- **Karşılığı olmayan güvenlik iddiaları işaretlendi.** README, kişisel veri işaretli
  kolonların maskelendiğini (G-16) ve denetim izinin değiştirilemez olduğunu (G-17)
  söylüyordu; ikisi de kodda uygulanmamıştı. İlgili satırlar, gerçekte ne olduğunu
  söyleyecek biçimde düzeltildi ve hangi iş paketinin kapatacağı yazıldı.
- Test sayısı düzeltildi: belgelerde 75 yazıyordu, gerçek sayı 88.

### Eklendi (İP-03 / A-1)
- `eval/evaluate.py` yeniden yapılandırıldı: üretici artık `globals()` ile modüle
  enjekte edilmiyor, `run_one(..., gen_mod)` ile dışarıdan veriliyor. Koşucu artık
  hiçbir LLM servisi olmadan test edilebiliyor.
- `--doctor`: ölçüm öncesi ortam kontrolü. Ollama erişimi, model varlığı ve **gerçek bir
  üretim denemesi** yapar; Windows/Vulkan çökmesini yakalar ve çözümü satır satır yazar.
- `--limit N`: ilk N soruyla hızlı deneme.
- Gecikme ölçümü (G-12) hattın içine alındı: p50, p95, en yavaş 5 soru.
- `docs/kanit/accuracy-<tarih>.md` ve `gecikme-<tarih>.md` otomatik üretiliyor;
  her rapor commit hash, model adı, platform ve tarih damgası taşıyor.
  Accuracy %80'in altındaysa rapor ADR-2 tetiklendiğini kendisi yazıyor.
- `tests/test_eval_runner.py`: 12 test — hiçbiri LLM gerektirmiyor.

### Düzeltildi (İP-03 / A-1)
- **Eksik bağımlılıkta ham yığın izi yerine anlaşılır mesaj.** `eval/evaluate.py`
  artık hangi Python'un kullanıldığını, sanal ortamın etkin olup olmadığını ve
  tam olarak hangi komutların çalıştırılacağını yazıyor. Saha kaydı: `--doctor`
  sanal ortam etkin değilken çıplak `ModuleNotFoundError` veriyordu — ürünün
  kendi hata mesajı ilkesi (Nielsen 9) giriş noktalarında uygulanmıyormuş.
- Soru süresi yalnız başarılı sorularda kaydediliyordu; artık her yolda kaydediliyor.
  Bu haliyle G-12 ölçümü başarısız soruları hiç görmeyecekti.
- `pyproject.toml`'daki F821 geçici lint istisnası kaldırıldı — gerekçesi ortadan kalktı.

### Eklendi (İP-03b — 2026-08-16 baseline'ı sonrası)
- **JOIN yolları belgesi.** Yabancı anahtar grafiğinden, seçilen tablo çiftleri için
  en kısa birleştirme yolu ve (varsa) bir adım uzun alternatifi otomatik üretilip
  bağlama ekleniyor. Yoldaki **ara tabloların şeması** da bağlama giriyor — model yolu
  görüp kolonlarını görememesin diye. Yollar yalnız seçilen tablolar için üretiliyor,
  böylece 200 tablolu kurumsal şemada bağlam patlamıyor.
- Belirsiz ilişkilerde alternatif yol sunuluyor: `bolum <-> hasta` hem yatış hem randevu
  zinciriyle kurulabilir; yalnız en kısa yolu yazmak modeli sessizce yanlış zincire iterdi.
- **İstem sertleştirildi.** Kolon adlarını harfi harfine koruma (İngilizceye çevirme),
  JOIN yollarını aynen kullanma, hesaplanan değerleri kolon sanmama kuralları +
  iki few-shot örnek. Her kural ölçümde gözlenen bir hata türüne karşılık geliyor.
- `tests/test_join_paths.py`: 13 test, hiçbiri LLM gerektirmiyor. Ölçümde reddedilen
  dört yol hatası (`muayene.hasta_id`, `fatura.bolum_id`, `doktor.muayene_id`,
  `fatura.islem_id`) artık doğrudan test altında.

### Düzeltildi (İP-03b, saha kaydı 2026-08-16)
- **Bağlam bütçesi.** JOIN yolları eklendikten sonra soru başına süre 20-30 sn'den
  70-115 sn'ye çıktı. Ölçüldü: 9 tablo → 36 çift → 41 yol satırı → 5102 karakter,
  bağlamın geri kalanı 2068 karakter. Yani yol bölümü, şema+terimlerin 2,5 katıydı.
  Artık en fazla 12 yol yazılıyor ve **soruyla alakalı çiftler önce** geliyor
  (soru kökleri ile tablo adları eşleştirilerek sıralanıyor). Bağlam ~%50 küçüldü.
- **Vektör arama gerçekten filtreliyor.** `retrieve()` Chroma'dan `k + terim_sayısı`
  sonuç istiyordu; koleksiyonda tablo ve terim belgeleri karışık durduğu için bu,
  21 belgenin 19'unu geri getiriyordu — "en ilgili 6 tablo" seçimi hiç çalışmıyormuş.
  Sonuçlar artık türe göre ayrılıp ayrı ayrı kırpılıyor.

### Düzeltildi — ölçüm belirlenimci hale getirildi (yöntem hatası, 2026-08-16)
- **`temperature=0` + sabit `seed`.** Üretim `temperature=0.1` ve rastgele tohumla
  koşuyordu; aynı istem koşumdan koşuma farklı SQL üretebiliyordu. 50 soruluk bir
  sette ölçümün standart hatası **±7 puan**; yani aynı gün yapılan dört ölçümün
  (%30 → %36 → %44 → %42) ardışık farklarının hiçbiri gürültüden ayırt edilemez
  (0,2σ – 0,8σ). Değişiklikleri karşılaştırabilmek için üretim önce
  **tekrarlanabilir** olmalı.
- Ölçüm damgasına `temperature`, `seed`, `num_ctx` ve `ornek_degerler` eklendi —
  karşılaştırmayı geçersiz kılabilecek her ayar raporda görünür.

### Eklendi — kategorik kolonların gerçek değerleri (saha kaydı 2026-08-16, 3. ölçüm)
- **Düşük kardinaliteli metin kolonlarının değerleri artık bağlama giriyor.**
  0 JOIN'li soruların yarısı yanlıştı ve sebep şemayı değil **değerleri** bilmemekti:
  model `unvan = 'Profesör'` yazıyordu, kolonda `Prof. Dr.` vardı; `durum = 'İPTAL'`
  yazıyordu, kolonda `IPTAL` vardı. İkincisi Türkçeye özgü bir tuzak — noktalı İ ile
  noktasız I farklı harflerdir ve sorgu **hata vermeden 0 satır döndürür**.
- **Gizlilik sınırı üç katmanlı:**
  (a) `masked_columns` (G-16) listesindekiler asla örneklenmez;
  (b) bir tabloda hem `ad` hem `soyad` varsa o bir kişi tablosudur, ikisi de atlanır
      (`doktor.ad` böyle elendi; `bolum.ad` ve `islem.ad` kalır — sorular onlara ihtiyaç duyuyor);
  (c) `tckn`, `telefon`, `eposta`, `adres`, `iban` gibi desenler kolon adından elenir.
  Ayrıca yalnız ≤20 farklı değeri ve ≤40 karakter uzunluğu olan metin kolonları alınır.
- `SORBI_ORNEK_DEGER=0` ile tümden kapatılabilir — **API modunda kapatılmalıdır**,
  çünkü bu değerler gerçek veridir ve dış servise gider.
- 8 yeni test: faydayı (IPTAL, Prof. Dr.) ve gizlilik sınırını birlikte koruyor.

### Düzeltildi — doğrulama katmanı geçerli SQL'i reddediyordu (saha kaydı 2026-08-16, 2. ölçüm)
- **Takma ad yanlış pozitifi.** Reddedilen 10 sorgunun **9'u** aslında geçerliydi:
  `ORDER BY ciro`, `ORDER BY randevu_sayisi`, `HAVING adet > 5` gibi ifadelerdeki
  adlar tablo kolonu değil, sorgunun kendi tanımladığı SELECT takma adlarıydı.
  Kolon halüsinasyonu kontrolü bunları "şemada yok" diye reddediyordu.
  Yani **accuracy'yi kendi doğrulama katmanımız bastırıyormuş** — üstelik istem
  sertleştirmesi modele "hesapla ve adlandır" dedikçe yanlış pozitif sıklaştı.
- CTE adları ve türetilmiş tablo (`FROM (SELECT ...) x`) adları artık şemada aranmıyor.
- 10 yeni test: beş geçerli kalıp (ORDER BY/HAVING takma adı, CTE, türetilmiş tablo)
  geçmeli, beş gerçek halüsinasyon (`gender`, `sex`, yanlış tablodan kolon, olmayan
  tablo, takma adın yanına gizlenmiş uydurma kolon) hâlâ reddedilmeli.

### Düzeltildi — doğrulama katmanı artık istisna fırlatmıyor (saha kaydı 2026-08-16)
- **`validate_and_transpile` sözleşmesi: hiçbir girdi için istisna fırlatmaz.**
  Model, istemdeki terim sözlüğünün bir parçasını SQL alanına kopyaladı; `sqlglot`
  kapanmamış tırnak yüzünden `TokenError` verdi. Kodda yalnız `ParseError`
  yakalanıyordu — 50 soruluk ölçüm 30. soruda çöktü ve 29 sorunun sonucu kayboldu.
  Bu katman bir **güvenlik kapısıdır** ve girdisi güvenilmeyen model çıktısıdır;
  fırlatan bir kapı çağıranın hata yoluna bağımlıdır, kapanan kapı her koşulda kapanır.
  Beklenmeyen her hata artık `ok=False` olarak dönüyor — açık değil kapalı tarafa düşüyor.
- `generator._parse`: SELECT/WITH ile başlamayan çıktı erken reddediliyor; istemin
  bir parçasının doğrulama katmanına çöp olarak gitmesi engellendi.
- `eval/evaluate.py`: tek sorunun beklenmeyen hatası artık koşumu düşürmüyor,
  o soru `kosucu_hatasi` olarak işaretlenip devam ediliyor.
- 13 yeni test: boş girdi, kapanmamış tırnak, ikili çöp, istemin kendisi, 200 açık
  parantez — hepsi çökme yerine açıklamalı red dönüyor.

### Eklendi (İP-03c — B-7'nin ilk adımı)
- **Sessiz yanlış ayrı metrik olarak raporlanıyor.** Yanlış cevabın iki türü artık
  ayrı sayılıyor: *yakalanan* (reddedildi / hata verdi, kullanıcı uyarılır) ve
  *sessiz yanlış* (hatasız tablo döndü, sayı yanlış). Asıl izlenen sayı
  "yanlışların içinde sessiz olanların payı" — doğruluk yükselse bile bu pay
  yüksek kalıyorsa ürün güvenilir değildir.
- **Önceki ölçümle otomatik karşılaştırma.** Rapor, bir önceki `results.json`'ı
  üzerine yazmadan önce okuyup accuracy / p50 / p95 / sessiz yanlış farkını
  tabloya yazıyor. "Bu değişiklik işe yaradı mı" sorusunun cevabı raporun içinde.
  Test seti ya da model değiştiyse tabloyu tek başına okumamak gerektiği uyarısı ekli.

### Değiştirildi
- `discover_schema()` artık üçüncü değer olarak yabancı anahtar kenarlarını döndürüyor.

### Bilinen açıklar (kapatılmadı — kayıt altına alındı)
Ayrıntı için `docs/is-hatti/BACKLOG.md`:
- G-16 kolon maskelemesi uygulanmıyor (İP-06)
- Sorgu zaman aşımı ve salt-okunurluk yalnız SQLite'ta zorlanıyor (İP-07)
- Bağlantı değişikliği süreç genelinde etkili — çok kullanıcılıda veritabanı sızıntısı (İP-10)
- **G-11 ölçüldü: %30,0** (15/50), G-12: p50 23,8 sn / p95 46,3 sn — ikisi de hedefin altında
- **Yanlış cevapların %65'i sessiz** (çalışıyor ama yanlış). Yeni gereksinim B-7 açıldı (İP-03c)
- G-16 maskeleme, G-14 zaman aşımı, durum yalıtımı hâlâ açık (İP-06/07/10)

---

## [2.3.0] — 2026-07-25

### Eklendi
- Kimlik doğrulama: giriş kapısı, ilk kurulum sihirbazı, PBKDF2-SHA256 şifre saklama,
  `yonetici` / `analist` rolleri, kullanıcı yönetimi sayfası
- Denetim izi artık oturum açan gerçek kimliğe bağlı
- `Dockerfile` + `docker-compose.yml`: tek komutla uygulama + Ollama, kalıcı veriler named volume'da

## [2.2.0] — 2026-07-25

### Eklendi
- Bağlantı Yöneticisi: SQLite / PostgreSQL / MySQL / SQL Server arayüzden seçilebiliyor,
  bağlantı testi, şifresiz profil kaydetme
- Bağlantı değişince RAG indeksi yeniden kuruluyor; Chroma koleksiyonu bağlantıya bağlı adlandırılıyor
- İkinci demo şema: `demo/seed_satis.py`

## [2.1.0] — 2026-07-25

### Eklendi
- Hizmet Analizi dashboard'u: filtre şeridi, KPI şeridi, bölüm bazlı grafik,
  bölüm × ay ısı haritası, doktor özet tablosu
- Her görselin altında "SQL göster" (G-02 dashboard'a taşındı)
- Yönetici Önerisi: KPI özeti yerel LLM'e gider, LLM yoksa kural tabanlı eşik önerileri

### Değiştirildi
- Isı haritasından matplotlib bağımlılığı kaldırıldı
- LLM hataları için anlaşılır mesajlar (Ollama kapalı, zaman aşımı, HTTP hatası)

## [1.0.0] — 2026-07-25

İlk sürüm. Sistem analizi dosyasındaki MVP uygulama sırasının 1–9. adımları.

### Eklendi
- Uçtan uca pipeline: ön işleme (G-07/09) → RAG bağlamı (G-05/06) → üretim (G-01) →
  doğrulama (G-10/18) → salt-okunur yürütme (G-14) → denetim izi (G-17)
- Türkçe göreli tarih çözümleme, hafif kök indirgeme
- sqlglot tabanlı doğrulama: SELECT-only, tablo ve kolon halüsinasyonu yakalama, lehçe çevirisi
- Streamlit arayüzü: SQL her zaman görünür, sonuç grafiği, CSV indirme, şema tarayıcı
- 50 soruluk Türkçe test seti + execution accuracy koşucusu + `--gold-only` bütünlük modu
- Demo hastane şeması ve sentetik veri üreteci

[Yayınlanmamış]: https://github.com/Arvas65/sorbi/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/Arvas65/sorbi/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Arvas65/sorbi/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Arvas65/sorbi/compare/v1.0.0...v2.1.0
[1.0.0]: https://github.com/Arvas65/sorbi/releases/tag/v1.0.0
