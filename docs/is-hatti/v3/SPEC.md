# SorBI v3 — SPEC

**Sürüm:** taslak 1.0 · **Tarih:** 2026-08-11 · **Taban commit:** `ffe5db3` (master)
**Karar sahibi:** İhsan Arvas · **Durum:** onaylandı (2026-08-11) · **Revizyon 1.1** (2026-08-16: A-6 ve B-7 eklendi)

---

## 1. Amaç (Intent)

Bugün SorBI çalışan bir demo. Ne var ki ürünün **iki temel iddiası kanıtsız**:
doğruluk hiç ölçülmedi (G-11 koşulmadı) ve belgelerde söz verilen güvenlik kapılarının
bir kısmı kodda yok (G-16 maskeleme uygulanmıyor, G-14 zaman aşımı yalnız SQLite'ta gerçek).
Bu haliyle bir hastane satın alma komitesinin ilk teknik sorusunda durur.

v3 bittiğinde: **SorBI'nin doğruluk ve güvenlik iddialarının her biri, o commit'te yeniden
üretilebilir bir kanıtla desteklenmiş olacak** — ve pipeline, arayüzden bağımsız çağrılabilir
bir çekirdeğe taşınmış olacak.

Bunu şuradan anlayacağız: `docs/kanit/` klasöründe, tarih + model + commit damgalı bir
accuracy raporu, bir gecikme raporu ve canlı bir Postgres üzerinde koşulmuş bir güvenlik
kapı raporu duruyor olacak; README'deki hiçbir cümlenin arkasında boşluk kalmayacak.

---

## 2. Kararlar (Clarify çıktısı)

| # | Karar | Sonucu |
|---|-------|--------|
| K-1 | Birincil hedef: **kanıt** (doğruluk + güvenlik kapıları) | Yeni son-kullanıcı özelliği yok; efor ölçüm ve sertleştirmeye gider |
| K-2 | Lisans: **çift lisans** — çekirdek açık, kurumsal katman kapalı | Depo ikiye ayrılır; CLA ve ticari lisans metni gerekir |
| K-3 | Mimari: **FastAPI çekirdek + Streamlit istemci** | Pipeline HTTP arkasına alınır; Streamlit `app/`'i doğrudan import etmez |
| K-4 | Build rolü: **karışık** — kritik modüller İhsan, altyapı Claude | PLAN'da her adımın yazarı açıkça belirtilir |
| K-5 | Baseline sonrası yön: **ucuz kazanç turu (İP-03b) önce, QLoRA kararı ikinci ölçümden sonra** | ADR-2 bugün tetiklenmiyor; PLAN Faz 1'e İP-03b eklendi (2026-08-16) |
| K-6 | Sessiz yanlış için yeni gereksinim **B-7** eklendi ve Faz 1'e alındı | Ölçümde yanlışların %65'i sessizdi; G-03'ün güven eşiği tek başına yetmiyor (2026-08-16) |

**Varsayım — ÇÖZÜLDÜ (2026-08-16).** Ollama Windows'ta sorunsuz koştu, Vulkan çökmesi
hiç görülmedi. Ölçüm alındı: **%30,0 execution accuracy**, p50 23,8 sn, p95 46,3 sn.
Başarısızlığın %65'i sessiz yanlış. Ayrıntılı teşhis: baseline teşhis notu ve
`docs/kanit/accuracy-2026-08-16.md`.

---

## 3. Mevcut durum — doğrulanmış boşluk envanteri

Aşağıdakilerin tamamı `ffe5db3` commit'i üzerinde kodla doğrulandı.

### 3.1 Belge ile kod uyuşmazlıkları

| # | Bulgu | Dayanak |
|---|-------|---------|
| E-1 | README'nin "QLoRA fine-tune" bölümü `training/generate_dataset.py` ve `training/train_qlora.py` diyor; **`training/` klasörü depoda yok.** Klasör yapısı listesinde de duruyor. | Depo kök listesi |
| E-2 | README ve sistem analizi "kişisel veri işaretli kolonlar maskelenir" (G-16) diyor. `demo/glossary.json` içinde `masked_columns` alanı var, `schema_rag.load_glossary()` onu okuyup döndürüyor — **hiçbir modül kullanmıyor.** Var olan tek maskeleme: `generator._TCKN` regex'i (11 haneli sayı). | `app/generator.py:312-317`, `app/schema_rag.py:189-194` |
| E-3 | Denetim izi "değiştirilemez" olarak belgelenmiş; gerçekte düz bir SQLite dosyası — hash zinciri, WORM, imza yok. Dosyaya erişen kayıtları sessizce değiştirebilir. | `app/audit.py` |
| E-4 | Sistem analizi §9 mimariyi "Python + FastAPI" olarak tanımlıyor; kodda API katmanı yok, iş mantığı Streamlit sayfalarından doğrudan çağrılıyor. | `ui/`, `app/` |

### 3.2 Güvenlik / sağlamlık boşlukları

| # | Bulgu | Dayanak | Ciddiyet |
|---|-------|---------|----------|
| G-A | **Zaman aşımı yalnız SQLite'ta gerçek.** `executor.run()` limiti sadece `sqlite3.interrupt()` ile kuruyor (`hasattr(raw, "interrupt")`). Postgres/MySQL/MSSQL'de hiçbir `statement_timeout` ayarlanmıyor → v2.2 ile açılan sunucu bağlantılarında G-14'ün 30 sn sözü **geçersiz**. | `app/executor.py:524-562` | Yüksek |
| G-B | **Salt-okunurluk yalnız SQLite'ta zorlanıyor.** `_readonly_url()` sadece `sqlite:///` şemasını `mode=ro` yapıyor; diğerlerinde önlem README'de bir temenni. Bağlantı testi, verilen hesabın gerçekten yazamadığını kontrol etmiyor. | `app/executor.py:516-521`, `app/connections.py:44-70` | Yüksek |
| G-C | **Çok kullanıcılı sızıntı riski.** `connections.aktifle()` süreç genelindeki `config.DB_URL`'i değiştiriyor; `pipeline._index` modül düzeyinde tek nesne. Streamlit tüm oturumları tek Python sürecinde çalıştırır → A kullanıcısı bağlantı değiştirdiğinde B kullanıcısının sorusu **başka bir veritabanına** gider. | `app/connections.py:74-80`, `app/pipeline.py:632-645` | Yüksek |
| G-D | **SQL sertleştirmesi yüzeysel.** Validator ifade türünü (SELECT/UNION/CTE) ve tablo-kolon varlığını kontrol ediyor; **fonksiyon allowlist'i yok.** SQLite `load_extension`, Postgres `pg_read_file`/`dblink`, `information_schema`/`sqlite_master` gezinmesi engellenmemiş. Kötü niyetli girdi test seti yok. | `app/validator.py:408-411` | Orta-Yüksek |
| G-E | **Kimlik katmanı pilot seviyesinde.** Brute-force sayacı/kilit yok, oturum zaman aşımı yok, yönetici tarafından şifre sıfırlama yok. Kullanıcılar düz JSON dosyada. | `app/auth.py`, `ui/ortak.py` | Orta |
| G-F | API modunda **şema metaverisi maskesiz** dışarı gidiyor. Veri değeri gitmiyor (doğru) ama tablo/kolon adları bazı kurumlar için hassas kabul edilir; sözleşmede bunun konuşulması gerekir. | `app/generator.py:344-355` | Düşük-Orta |

### 3.3 Uygulanmamış gereksinimler

| G-kapısı | Durum |
|----------|-------|
| G-03 (netleştirme sorusu) | **Kısmi.** Güven <0.6'da red + mesaj var; gerçek bir soru-cevap turu yok. Kullanıcı netleştirse bile sistem o cevabı kullanmıyor. |
| G-04 (doğal dil özeti) | **Yok.** Pipeline'da hiç yer almıyor. |
| G-08 (sorgu geçmişi + tekrar önerisi) | **Yok.** `audit.recent()` var ama geçmişten öneri üretme yolu yok; sistem analizindeki `soru_ozeti_hash` indeksi uygulanmamış. |
| G-11 (≥%80 execution accuracy) | **ÖLÇÜLDÜ (2026-08-16): %30,0** (15/50). 2+ JOIN gerektiren 9 sorunun tamamı başarısız. |
| G-12 (≤10 sn yanıt) | **ÖLÇÜLDÜ (2026-08-16):** p50 23,8 sn · p95 46,3 sn — hedefin 2,4–4,6 katı. Soğuk başlangıç artefaktı değil. |
| G-16 (maskeleme) | **Yok** (bkz. E-2). |
| G-17 (değiştirilemez iz) | **Kısmi** (bkz. E-3). |

### 3.4 Mühendislik altyapısı

CI yok (`.github/` yok) · bağımlılıklar `>=` ile pinsiz, Docker build tekrarlanabilir değil ·
`pyproject.toml` yok · lint/format/tip kontrolü yok · CHANGELOG ve sürüm etiketi yok ·
testler `generator`, `schema_rag`, `pipeline`, `audit` modüllerini hiç kapsamıyor —
yani pipeline'ın kendisi test altında değil · `eval/evaluate.py` içinde `globals()["generator"]`
enjeksiyonu var, kırılgan.

---

## 4. Kapsam — gereksinimler ve kabul kriterleri

### A. Kanıt hattı — doğruluk ve gecikme

**A-1 · Eval hattı LLM'den bağımsız koşabilmeli.**
`eval/evaluate.py` içindeki `globals()` enjeksiyonu kaldırılır; generator arayüzü enjekte
edilebilir hale gelir.
*Kabul:* sahte (mock) generator ile `pytest tests/test_eval_runner.py` LLM olmadan geçer;
`--gold-only` CI'da koşar ve 50/50 raporlar.

**A-2 · G-11 baseline ölçümü alınır.**
Mevcut RAG-only mimarinin execution accuracy'si ölçülür; zorluk ve JOIN sayısı kırılımıyla.
*Kabul:* `docs/kanit/accuracy-<tarih>.md` dosyasında tek bir sayı + kırılım tablosu +
model adı + commit hash + koşum ortamı. Sayı %80'in altındaysa bu bir **başarısızlık değil,
ADR-2'nin tetiklenmesidir** — QLoRA kararı yeni bir İP olarak açılır.

**A-3 · G-12 gecikme ölçümü alınır.**
Test setinin tamamında uçtan uca süre: p50, p95, en yavaş 5 soru.
*Kabul:* `docs/kanit/gecikme-<tarih>.md`; yerel modda p95 ≤ 10 sn hedefi karşılandı/karşılanmadı
açıkça yazılır.

**A-4 · Regresyon kapısı.**
*Kabul:* CI'da accuracy, son kayıtlı ölçümden 3 puandan fazla düşerse iş akışı kırmızıya döner.

**A-6 · Ucuz kazanç turu ve ikinci ölçüm.** *(2026-08-16 ölçümüyle eklendi)*
Baseline'ın başarısızlık şekli üç somut eksiğe işaret ediyor: birleştirme yolları modele
hiç anlatılmıyor (12 reddin 6'sı), istem kolon adlarını koruma talimatı vermiyor (3 red +
2 uydurma kolon), taban model SQL'e özel eğitilmemiş.
*Kabul:* (a) JOIN yolları FK grafiğinden otomatik üretilip bağlama eklenir, yoldaki ara
tabloların şeması da bağlama girer; (b) istem, gözlenen dört hata türünün her birine bir
kural içerir; (c) aynı test seti en az iki modelle koşulur ve sonuçlar yan yana yazılır.
İkinci ölçüm alınmadan ADR-2 (QLoRA) kararı verilmez.

**A-5 · Test seti genişletilir ve ikinci şemaya taşınır.**
Hastane setine 30 soru eklenir (50 → 80); satış şeması (`demo/seed_satis.py`) için 30 soruluk
ikinci set yazılır.
*Kabul:* iki set de `--gold-only` ile %100 sağlıklı; ADR-4'ün taşınabilirlik iddiası artık
tek şemaya dayanmıyor.

### B. Güvenlik kapıları — söylenenin gerçekten yapılması

**B-1 · G-16 kolon maskelemesi uygulanır.**
`masked_columns` şema keşfiyle birleştirilir ve üç noktada etkili olur:
(a) API moduna giden bağlamda maskeli kolonlar "MASKELİ" olarak işaretlenir,
(b) üretilen SQL maskeli bir kolonu ham seçiyorsa sorgu reddedilir ya da maskeleyen ifadeyle sarılır
(politika yapılandırılabilir: `RED` | `MASKELE`),
(c) sonuç tablosunda değer maskelenir.
*Kabul:* `tests/test_masking.py` — maskeli kolonu isteyen soru ham değer döndürmez;
API moduna giden HTTP gövdesinin anlık görüntüsünde hiçbir veri satırı yok;
maskeleme politikası yapılandırmadan okunuyor.

**B-2 · G-14 zaman aşımı her lehçede gerçek olur.**
Postgres `statement_timeout`, MySQL `max_execution_time`, MSSQL sorgu zaman aşımı,
SQLite mevcut `interrupt` yolu.
*Kabul:* her lehçe için uzun-sorgu testi (ör. Postgres'te `pg_sleep(60)`) 30 sn içinde
`ZAMAN_ASIMI` döner. Docker Compose ile ayağa kalkan gerçek Postgres üzerinde koşulur.

**B-3 · G-14 salt-okunurluk zorlanır ve doğrulanır.**
Oturum düzeyinde salt-okunur işlem (`SET TRANSACTION READ ONLY` vb.) + bağlantı testinde
**yazma denemesi**: hesap yazabiliyorsa arayüz kırmızı uyarı verir ve bağlantı "riskli" işaretlenir.
*Kabul:* yazabilen hesapla bağlanıldığında uyarı görünür ve denetim izine yazılır; test var.

**B-4 · G-18 sertleştirilir + kırmızı takım test seti.**
Fonksiyon allowlist'i; tehlikeli fonksiyon ve sistem kataloğu erişimi reddedilir.
*Kabul:* `tests/test_security_redteam.py` en az 25 kötü niyetli girdi içerir
(çok ifadeli enjeksiyon, yazılabilir CTE, `load_extension`, `pg_read_file`, `dblink`,
sistem kataloğu gezinmesi, yorumla kaçırma, `UNION` ile şema sızdırma) — **hepsi reddedilir.**

**B-5 · G-17 hash zinciri.**
Her denetim kaydı bir önceki kaydın hash'ini taşır; `audit.verify_chain()` bozulmayı bulur.
*Kabul:* kaydı elle değiştirdikten sonra `verify_chain()` False döner ve hangi satırda
koptuğunu söyler; test var. Arayüzde yönetici için "denetim izi bütünlüğü" göstergesi.

**B-7 · Sessiz yanlış azaltma.** *(2026-08-16 ölçümüyle eklendi)*
Ölçümde 50 sorunun 22'si (%44) hatasız çalıştı ama yanlış cevap verdi; doğrulama katmanı
hataların yalnız üçte birini yakaladı. Sistem analizi B7 bunu en büyük risk olarak
kaydetmişti — ölçüm bunu baskın başarısızlık modu olarak doğruladı.
Sistem, modelin kendi güven beyanından **bağımsız** bir doğruluk sinyali üretmelidir.
Aday mekanizmalar: aynı soruyu iki kez üretip sonuç kümelerini karşılaştırma ·
üretilen SQL'i doğal dile geri çevirip soruyla karşılaştırma · sonuç biçimi tutarlılığı
(sayı sorulmuş, çok satır dönmüş) · kullanılan tabloların soru terimleriyle örtüşmesi.
*Kabul:* test setinde sessiz yanlış oranı, doğruluğu düşürmeden ölçülebilir biçimde azalır;
azaltılamayan kısım kullanıcıya "bu cevaptan emin değilim" olarak gösterilir.
Ölçüm koşucusu sessiz yanlış oranını ayrı bir metrik olarak raporlar.

**B-6 · Kimlik sertleştirilir.**
Başarısız giriş sayacı + geçici kilit, oturum zaman aşımı, yönetici tarafından şifre sıfırlama.
*Kabul:* testler; kilit ve zaman aşımı süreleri yapılandırılabilir.

### C. Mimari — çağrılabilir çekirdek

**C-1 · Durum yalıtımı (G-C bulgusunun kapatılması).**
Süreç genelindeki `config.DB_URL` mutasyonu ve `pipeline._index` tekil nesnesi kaldırılır.
Bağlantı bir **oturum bağlamı** nesnesiyle taşınır; indeks bağlantı anahtarına göre önbelleklenir.
*Kabul:* iki farklı bağlantıyla eşzamanlı çağrı testi — her cevap kendi veritabanından gelir.
**Bu, C-2'nin ön koşuludur ve tek başına da gönderilebilir.**

**C-2 · FastAPI çekirdeği.**
Uç noktalar: `POST /ask` · `GET /schema` · `GET /audit` · `POST /connections/test` · `GET /health`.
Kimlik: oturum jetonu (arayüz) + API anahtarı (entegrasyon).
*Kabul:* OpenAPI şeması üretiliyor; Streamlit sayfaları `app/` modüllerini **doğrudan import etmiyor**
(bir içe aktarım denetimi testi bunu zorlar); mevcut tüm arayüz akışları API üzerinden çalışıyor.

**C-3 · Docker Compose güncellenir:** `api` + `ui` + `ollama` üç servis; sağlık kontrolleri bağlı.
*Kabul:* `docker compose up -d` sonrası üç servis de sağlıklı; arayüz API'yi görüyor.

### D. Ticarileşme yapısı

**D-1 · Çift lisans kurulumu.**
Çekirdek açık kalır (mevcut MIT sürdürülebilir; patent maddesi için Apache-2.0'a geçiş
ayrı bir karar olarak İP'de değerlendirilir). Kurumsal katman (çok kiracılılık, SSO,
denetim raporları, öncelikli destek) ayrı kapalı depoda ve ticari lisansla.
*Kabul:* `LICENSE`, `LICENSE-ENTERPRISE.md`, `NOTICE`, README lisans bölümü, katkı sağlayan
lisans sözleşmesi (CLA) metni depoda. Hangi özelliğin hangi tarafta olduğu tek bir tabloda.

**D-2 · Sürümleme.**
SemVer + `CHANGELOG.md` + git tag; her Ship kararı bir tag üretir.
*Kabul:* v3.0.0 tag'i, geçmiş sürümler için geriye dönük CHANGELOG girdileri.

### E. Mühendislik altyapısı

**E-1 · `pyproject.toml` + ruff + pinlenmiş bağımlılıklar** (kilit dosyası).
*Kabul:* `ruff check` temiz; Docker build iki kez koşulduğunda aynı sürümleri kuruyor.

**E-2 · CI (GitHub Actions):** lint → birim testler → `--gold-only` eval → docker build.
*Kabul:* PR'da zorunlu; master'a doğrudan itme kapalı.

**E-3 · Test kapsamı.** `generator` (sahte HTTP ile), `schema_rag`, `pipeline` (uçtan uca,
sahte LLM), `audit` için testler.
*Kabul:* satır kapsamı ≥ %70 ve CI'da eşik olarak zorlanıyor.

**E-4 · Yapısal loglama.** `print` yerine `logging`; her sorunun bir korelasyon kimliği.
*Kabul:* bir sorunun tüm aşamaları tek kimlikle izlenebiliyor.

**E-5 · Belge-kod tutarlılığı (E-1..E-4 bulgularının kapatılması).**
*Kabul:* Verify kontrol listesi temiz; README'de gösterilen her komut koşturuldu.

---

## 5. Kapsam dışı — bilinçli olarak yapılmayacaklar

| Ne | Gerekçe |
|----|---------|
| React/Next.js yeniden yazımı | Doğruluk kanıtlanmadan arayüz yatırımı erken optimizasyon. C-2 bu kapıyı zaten açık bırakıyor. |
| Çok kiracılı SaaS | K-2 gereği kurumsal katmana ait; önce on-prem kanıt. |
| QLoRA fine-tune | ADR-2 koşulu: yalnız A-2 ölçümü %80'in altında çıkarsa açılır. Şu an spekülatif. |
| G-04 doğal dil özeti, G-08 geçmiş/öneri | "Could/Should" seviyesinde; kanıt turunu geciktirir. v3.1 backlog'una yazılır. |
| Dashboard'un doğal dil ile filtrelenmesi, zamanlanmış PDF rapor | Demo değeri yüksek, kanıt değeri sıfır. Backlog. |
| İngilizce soru desteği (G-19) | Sistem analizinde zaten "Won't" olarak kayıtlı; karar değişmedi. |

---

## 6. Etkilenen kapılar ve kararlar

**Doğrudan etkilenen G-kapıları:** G-11, G-12, G-14, G-16, G-17, G-18
**Dolaylı:** G-05 (indeks önbellekleme C-1 ile değişir), G-15 (API modu maskelemeyle sıkılaşır)
**ADR'ler:** ADR-2 (A-2 sonucuna bağlı yeniden açılabilir) · ADR-4 (A-5 ile ilk kez gerçekten sınanır)
**Yeni ADR gerekecek:** ADR-6 lisans yapısı · ADR-7 API katmanı ve durum yalıtımı

---

## 7. Riskler

| # | Risk | Etki | Azaltma |
|---|------|------|---------|
| R-1 | Ollama/Windows sorunu ölçümü yine engeller | Kanıt turu tıkanır | İlk adım varsayım doğrulaması; başarısızsa Linux konteynerinde ölçüm — İP-03'ün ilk yarım günü |
| R-2 | Baseline accuracy %80'in belirgin altında çıkar | Ürün tezi sarsılır | Bu bir çıktıdır, başarısızlık değil. ADR-2 tetiklenir; ölçüm olmadan zaten satış yapılamıyordu |
| R-3 | FastAPI refaktörü Build'i uzatır | Takvim kayar | C-1 (durum yalıtımı) C-2'den ayrı gönderilebilir; C-2 kayarsa kanıt turu etkilenmez |
| R-4 | Gerçek Postgres/MSSQL test ortamı yok | B-2/B-3 doğrulanamaz | Postgres ve MySQL Docker ile kolay; MSSQL için Linux imajı var, yoksa B-2/B-3 MSSQL kısmı "doğrulanmadı" olarak açıkça işaretlenir — sessizce geçilmez |
| R-5 | Çift lisans geçişi mevcut MIT sürümü nedeniyle karmaşıklaşır | Hukuki belirsizlik | Tek yazar avantajı var; yine de D-1 öncesi kısa bir hukuki gözden geçirme adımı planda duruyor |

---

## 8. Geri alma

Her İP kendi dalında; master'a yalnız Ship kararıyla girer. Güvenlik değişiklikleri
(B-1..B-4) davranış değiştirici olduğundan her biri yapılandırma anahtarıyla kapatılabilir
olur — bir pilot kurulumda sorun çıkarsa sürüm geri alınmadan kapatılabilir.
