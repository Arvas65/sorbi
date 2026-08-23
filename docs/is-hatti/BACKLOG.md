# Backlog

Review ve Verify adımlarında **SONRA** etiketi alan her bulgu buraya düşer.
Buraya düşmeyen bulgu kaybolmuş sayılır (`00-IS-HATTI.md` § 5).

Öncelik: **BLOK** (sürümü engeller) · **YÜKSEK** · **ORTA** · **DÜŞÜK**

---

## Planlı iş paketleri (v3 PLAN'ından)

| İP | Başlık | Kaynak | Öncelik | Durum |
|----|--------|--------|---------|-------|
| İP-01 | Mühendislik altyapısı | v3 SPEC E-1, E-2 | YÜKSEK | ✅ tamamlandı |
| İP-02 | Belge-kod tutarlılığı + sürümleme | v3 SPEC D-2, E-5 | YÜKSEK | ✅ tamamlandı |
| İP-03 | Eval hattı + G-11/G-12 baseline | v3 SPEC A-1, A-2, A-3 | BLOK | 🔄 A-1 ✅ · A-2/A-3 İhsan'ın makinesinde koşulacak |
| İP-04 | Test setini genişlet (80 + 30) | v3 SPEC A-5 | YÜKSEK | bekliyor |
| İP-05 | Regresyon kapısı | v3 SPEC A-4 | ORTA | bekliyor |
| ~~İP-15~~ | ~~Yapısal loglama + kapsam eşiği~~ | BULGU-04 (E-3, E-4) | YÜKSEK | **KAPANDI** (İP-03c, 2026-08-16) |
| İP-06 | G-16 kolon maskelemesi | v3 SPEC B-1 | BLOK | bekliyor |
| İP-07 | G-14 zaman aşımı + salt-okunurluk | v3 SPEC B-2, B-3 | BLOK | bekliyor |
| İP-08 | G-18 sertleştirme + kırmızı takım | v3 SPEC B-4 | YÜKSEK | bekliyor |
| İP-09 | G-17 hash zinciri + kimlik sertleştirme | v3 SPEC B-5, B-6 | YÜKSEK | bekliyor |
| İP-10 | Durum yalıtımı (bağlantı sızıntısı) | v3 SPEC C-1 | BLOK | bekliyor |
| İP-11 | FastAPI çekirdeği | v3 SPEC C-2 | ORTA | bekliyor |
| İP-12 | Docker Compose güncellemesi | v3 SPEC C-3 | DÜŞÜK | bekliyor |
| İP-13 | Çift lisans yapısı | v3 SPEC D-1 | ORTA | bekliyor |
| İP-14 | Kanıt dosyası | v3 SPEC E-5 | YÜKSEK | bekliyor |

---

## İP-01/02 sırasında ortaya çıkan yeni maddeler

| İP | Başlık | Kaynak | Öncelik |
|----|--------|--------|---------|
| İP-15 | *(PLAN'a taşındı — yukarıdaki tabloya bakın)* **Yapısal loglama + kapsam eşiği.** `app/generator.py` içinde API çağrısı başarısız olduğunda hata sessizce yutuluyor (`except Exception: pass`, iki yerde) ve yerel moda düşülüyor. Kullanıcı mod etiketini görüyor ama hatanın ne olduğunu hiç kimse görmüyor — saha teşhisi imkânsız. Ayrıca `pyproject.toml`'daki kapsam eşiği şu an yalnız raporlayıcı; zorlayıcı hale gelmeli. **v3 SPEC'te E-3 ve E-4 gereksinimlerinin sahibi bir İP yoktu — bu, planın kendi Review'unda çıkan bir boşluktur.** | Review İP-01 · ruff S110/B904 | YÜKSEK |
| ~~İP-16~~ | **KAPANDI (2026-08-16), ama tarifi yanlıştı.** Dashboard aslında tablo adı gömmüyor — `BASE`/`W` kod içi sabitlerden kuruluyor, değerler parametreli. Gerçek nokta `ui/streamlit_app.py` şema sekmesiydi: `f'... FROM "{_t}"'` elle alıntılıyordu ve `_t` kullanıcı şemasından geliyor. Sürücünün `identifier_preparer`ına çevrildi. **Ders: Review bulgusunun kendisi de doğrulanmalı.** ~~Dashboard sorgularında tanımlayıcı birleştirme.~~ `ui/pages/1_Dashboard.py` ve `ui/streamlit_app.py` tablo adlarını f-string ile SQL'e gömüyor (5 nokta). Girdi kullanıcıdan değil şema keşfinden geliyor, dolayısıyla bugün istismar edilebilir değil — ama ürünün kendi ilkesi bu kalıbı yasaklıyor ve kullanıcı tanımlı şemalarda tablo adı artık güvenilir bir kaynak değildir. Tanımlayıcılar sqlglot ile alıntılanmalı. | Review İP-01 · ruff S608 | ORTA |
| **İP-17** | **`ruff format` kararı.** Depo şu an biçimlendirilmemiş; `ruff format` 24 dosyayı değiştirir. İP-01'de bilinçli olarak **yapılmadı**: Faz 2'yi İhsan yazacak ve büyük bir biçim diff'i o çalışmanın üzerine gelirse gözden geçirmeyi zorlaştırır. Faz 2 bittikten sonra tek seferde uygulanmalı ve CI'a eklenmeli. | Review İP-01 | DÜŞÜK |
| **İP-18** | **pandas 3.x uyumluluğu.** Bağımlılık kilidi oluşturulurken pandas bilinçli olarak `<3` ile sınırlandı; en yeni çözümleme 3.0.5 getiriyordu ve dashboard kodunun bu sürümle uyumu denenmedi. Sınır kaldırılmadan önce arayüz akışları 3.x altında koşulmalı. | Verify İP-01 | DÜŞÜK |

---

## Kapsam dışı bırakılanlar (v3 SPEC § 5 — unutulmasın diye burada)

| Konu | Ne zaman yeniden açılır |
|------|-------------------------|
| QLoRA fine-tune | İP-03 baseline'ı %80'in altında çıkarsa (ADR-2) |
| G-04 doğal dil özeti | v3.1 |
| G-08 sorgu geçmişi + tekrar önerisi | v3.1 |
| Doğal dil ile dashboard filtreleme | v3.1 |
| Zamanlanmış PDF / e-posta raporu | v3.1 |
| Çok kiracılı SaaS | Kurumsal katman (İP-13 sonrası) |
| React yeniden yazımı | İP-11 sonrası, talep gelirse |

---

## Kapanan maddeler

| Madde | Sonuç |
|-------|-------|
| BULGU-04 — planda E-3/E-4 sahipsizdi | **Kapatıldı.** İP-15 olarak PLAN Faz 1'e eklendi (2026-08-11). |
| `eval/evaluate.py` globals() enjeksiyonu (F821) | **Kapatıldı.** İP-03/A-1 ile üretici enjekte edilebilir hale geldi; `pyproject.toml`'daki F821 geçici istisnası silindi. |
| `.streamlit/config.toml` sır barındırıyor mu? | **Hayır.** Yalnızca `fileWatcherType = "none"` ve `gatherUsageStats = false`. Verify sırasında okundu, temiz. |
| `.dockerignore` var olmayan `training/output/` yolunu listeliyordu | Kaldırıldı; `.github/` ve `.pytest_cache/` eklendi (İP-02). |
| Giriş noktalarında eksik bağımlılık ham traceback veriyordu | **Kapatıldı.** `eval/evaluate.py` artık sanal ortamı teşhis edip ne yapılacağını yazıyor; testi var. Saha kaydından geldi (İhsan, 2026-08-16). |


---

## İP-03c turunda açılan yeni maddeler (2026-08-16)

| # | Konu | Kaynak | Öncelik |
|---|------|--------|---------|
| ~~İP-19~~ | **KAPANDI (2026-08-16).** ~~B-7 API modunda kör.~~ `SORBI_ORNEK_DEGER=0` zorunlu olduğu için `bilinen_degerler` boş kalır; en isabetli kontrol (`bilinmeyen_deger`, mutasyon karnesinde 35/0) API modunda tümden susar. Değer örneklemesi gizlilik gereği kapalı — alternatif bir sinyal gerekiyor (ör. yalnız kolon adları + kardinalite, değer olmadan). | İP-03c REVIEW B7R-07 | **KAPANDI** — kısıt istem katmanına taşındı; örnekleme her zaman yapılıyor, isteme yazma `ORNEK_DEGERLER`e bağlı |
| **İP-20** | **Güven bayrakları denetim izine yazılmıyor.** Bugün yalnız ekranda görünüyor; hangi cevapların şüpheli işaretlendiği geriye dönük sorulamıyor. G-17 hash zinciriyle (İP-09) birlikte yapılmalı. | İP-03c REVIEW B7R-05 | ORTA |
| **İP-21** | **`where_dus` sınıfı kaçırma.** Sıfatla daraltılan sorular ("Kadın hastaların sayısı", "Profesör unvanlı doktorlar") filtre işareti taşımıyor; mutasyon karnesinde bu sınıfın %48'i kaçıyor. Soru terimlerini kolon değerlerine eşleyen bir adım gerekiyor. | İP-03c REVIEW B7R-03 | ORTA |
| **İP-22** | **İ harfi düzeltmesinin ölçüm tekrarı.** `preprocess.keywords` artık Türkçe İ ile başlayan kelimelerin ilk harfini yutmuyor. RAG anahtar-kelime yolunu etkiliyor; doğruluk ölçümü bu düzeltmeden sonra tekrarlanmadı. | İP-03c REVIEW B7R-04 | YÜKSEK |

| ~~İP-23~~ | **KAPANDI (2026-08-20)** — `docs/is-hatti/v3/IP-23/BULGU.md`. Sorun sanıldığından genişti: yalnız karne değil, accuracy ölçümü de etkileniyordu. ~~Mutasyon karnesi tarihe bağımlı.~~ Test setindeki 5 gold sorgu `date('now')` kullanıyor ("şu anda yatan hasta"). Karne 16 Ağustos'ta 199/240 + 1 yanlış alarm veriyordu, 20 Ağustos'ta 198/239 + 2 verdi — kod değişmeden. Kendi ölçüm aracımız günden güne kayıyor; bu, "kanıt damgalı ve tekrarlanabilir" ilkesinin ihlali. Çözüm: karne koşumuna sabit bir referans tarih enjekte etmek (`SORBI_BUGUN`) ya da bu 5 soruyu karne evreninden çıkarmak. | Oturum açılışı, 2026-08-20 | ORTA |

| ~~İP-24~~ | **KAPANDI (2026-08-21), aynı gün açıldı.** Teslim paketi `docs/kanit/KARNE-GECMIS.log` taşıyordu; kurulumda hedef makinenin ölçüm geçmişini ezecekti — karnenin karşılaştırma tabanı tam olarak o dosya. Bugünün diğer üç bulgusuyla aynı aile: paketleyenin makinesinde geçerli olanın hedefte de geçerli olduğunu varsaymak. İki yerden kapatıldı: paketleme kuralı (`CLAUDE.md` §9) ve `kur.bat` içindeki kanıt koruması (pakete güvenmez, `docs/kanit`'i açılan kopyadan siler). | kur.bat yazılırken, 2026-08-21 | — |

| ~~İP-25~~ | **KAPANDI (2026-08-22)** — `yedekle.bat` çalıştı, `ip-01-02-altyapi` dalı GitHub'da. |
| ~~İP-25 (özgün kayıt)~~ | **v3 işinin tamamı yalnız yerel diskte.** GitHub'daki depo 2026-07-25'ten beri güncellenmemiş: uzakta `master` var, içinde `app/guven.py`, `eval/tarih_sabitle.py`, `CLAUDE.md`, `.github/workflows/ci.yml`, `.claude/` ve testlerin 12'si **yok**. İki sonucu var: (a) tek nokta arıza — disk giderse altı haftalık iş gider, (b) **CI hiç koşamadı**, çünkü workflow dosyası uzakta yok; BULGU-06 (ilk yeşil CI) bu yüzden yapısal olarak kapanamıyordu. Ayrıca gece koşumunun `git push` adımı bu ön koşul olmadan tasarlanmıştı — **benim hatam: ön koşulu doğrulamadan kanal tasarladım.** Çözüm: `yedekle.bat` (tek çift tıklama), CI artık her dalda koşuyor, gece koşumunun push hatası artık sessiz değil (`PUSH-SORUNU.txt` + açılış kapısı). **Kalan iş İhsan'da: `yedekle.bat` bir kez çalıştırılmalı.** | Oturum açılışı, 2026-08-21 | **YÜKSEK** |

| ~~İP-26~~ | **KAPANDI (2026-08-22).** `karsilastirilamaz()` yalnız `n` ve referans gününü denetliyordu; `olcum-al` skill'inde yazılı olan model/sıcaklık/seed/num_ctx/değer-örnekleme koşulları koda hiç inmemişti. 2026-08-22 koşumunda num_ctx 4096→8192 değişmişti ve görünmüyordu. Kural belgede, denetim kodda değil — ADR-1'le aynı aile. 4 test eklendi. | 2026-08-22 ölçümü | — |
| ~~İP-27~~ | **KAPANDI (2026-08-22).** Ölçüm damgasındaki commit hash'i koşulan kodu göstermiyordu: 16 ve 22 Ağustos koşumlarının ikisi de `ffe5db3` taşıyor, aralarında altı haftalık işlenmemiş iş var. Damga artık kirli çalışma ağacını işaretliyor. | 2026-08-22 ölçümü | — |
| **İP-28** | **Gecikme %50 arttı** — p50 14,4→21,7 sn, p95 21,2→32,8 sn. Aynı koşumda num_ctx 4096→8192 değişti ama referans gün de değişti; **iki değişken birden oynadığı için nedensellik kurulamaz.** Tek değişkenli deney `gece-gorev/01-numctx-deneyi.bat` olarak kuyruğa alındı. Doğruluk düşmezse 4096'ya dönülür ve G-12 hedefine ~7 saniye kazanılır. | 2026-08-22 ölçümü | YÜKSEK |

| ~~İP-29~~ | **KAPANDI (2026-08-22), açıldığı gün.** `kontrol.bat` içindeki `BEKLENEN_TEST=320` sabiti, aynı gün 6 test eklenince yanlış alarm üretti ("gecti, ama test sayisi beklenenden farkli") — oysa artış iyi bir şeydi. Bu hafta **dördüncü** kez aynı kalıp: sabit referans günü, sabit karne sayıları, ADR'nin koda inmemesi ve şimdi bu. Sabit silindi; koşum artık kendi geçmişiyle karşılaştırılıyor (`docs/kanit/TEST-GECMIS.log`) ve **yalnızca düşüş** uyarı sayılıyor. 10 test. | kur.bat çıktısı, 2026-08-22 | — |

| ~~İP-30~~ | **KAPANDI (2026-08-22) — en ağır bulgu.** `generate_api` sorunun kendisini maskeliyordu ama **bağlamı olduğu gibi gönderiyordu.** Bağlam, `ORNEK_DEGERLER` açıkken "DEĞERLER (...)" bloğunu taşır ve o blok **gerçek kolon değerleridir** — hastane şemasında ünvanlar, bölüm adları, şehirler, durum kodları. Fonksiyonun docstring'i "veri değeri asla gitmez" diyordu; bunu sağlayan tek şey kullanıcının `SORBI_ORNEK_DEGER=0` yazmayı hatırlamasıydı. **Ürünün ana vaadi bir ayarın hatırlanmasına bağlıydı.** `mask_context()` ile yapısal hale getirildi: API yolundan geçen her bağlamdan değer blokları koşulsuz düşüyor, şema metaverisi kalıyor. Gerçek bağlamla doğrulandı (868→612 karakter, sızan değer yok). 6 test. | Gemini denemesi hazırlığı, 2026-08-22 | — |
| ~~İP-31~~ | **KAPANDI (2026-08-22).** Ücretsiz katmanda 429 (hız sınırı) alan sorular, modelin bilmediği sorular gibi sayılacaktı: 101 sorunun 40'ı takılsa doğruluk %20 görünürdü. `KotaHatasi` ayrı tür oldu, 429'da artan aralıklarla 4 deneme yapılıyor, tükenirse soru `kota_asildi` diye AYRI sayılıyor ve rapor "bu koşum karşılaştırma için kullanılamaz" uyarısı basıyor. Kota aşımı yerel moda düşerek de gizlenmiyor — düşseydi ölçüm "api" diye başlayıp sessizce yerel modelle biterdi. 8 test. | Gemini denemesi hazırlığı, 2026-08-22 | — |
| **İP-32** | **API modu ADR kararı gerektiriyor.** Gemini ölçümü alındıktan sonra: taban modeli API'ye taşımak, "veri makineden çıkmaz" vaadini **ürün konumlandırması** düzeyinde değiştirir. Demo/ölçüm için sorun yok (veri sentetik), gerçek hastane müşterisi için ayrı bir karar. ADR-1'in yanına ADR-5 (çalışma modu) gerekiyor ve bu **İhsan'ın Ship kapısı**. | 2026-08-22 | YÜKSEK |

| ~~İP-33~~ | **KAPANDI (2026-08-22).** Test süiti **üretim kanıtına yazıyordu**: `test_karne_ozet_satiri_makine_okunur` gerçek `docs/kanit/KARNE-GECMIS.log` dosyasına 3 soruluk bir karne kaydediyordu. İhsan'ın koşumunda "ÖNCEKİ KARNE: FARKLI — önceki: gold=3" diye yanlış alarm üretti. İki kat kapatıldı: (a) kısmi koşumlar (`gold < 101`) artık geçmişe hiç yazılmıyor — 3 soruluk karne 101 soruluk karneyle karşılaştırılamaz, aynı "farklı cetvel" kuralı; (b) test artık `tmp_path`e yazıyor. **Testin üretim kanıtını kirletmesi başlı başına bir kusurdur.** 2 test. | İhsan'ın kontrol logu, 2026-08-22 | — |
| ~~İP-34~~ | **KAPANDI (2026-08-22).** Her koşumda iki `ResourceWarning` (kapatılmamış sqlite bağlantısı) basılıyordu. `discover_schema` ve `veri_gunu` motoru `try/finally` ile kapatıyor artık. Küçük bir şey ama her koşumda görülen bir uyarı, okunmayan bir uyarıdır — ve bu projenin tüm tezi okunmayan uyarıların tehlikesi üzerine. | İhsan'ın kontrol logu, 2026-08-22 | — |
