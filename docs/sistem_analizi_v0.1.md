# SİSTEM ANALİZİ DOSYASI

**TR-SQL / SorBI: Türkçe Doğal Dilden Sorgu Üretimi (BI eklentisi)**
Doldur-ilerle şablonu v1.0 · SDLC (Kendall & Kendall) · Doküman v0.1 · 24.07.2026

> Not (v0.2 adayı): B3 bulgusu güncellenecek — TURSpider, TUR2SQL ve BIRDTurk (Şubat 2026)
> yayınlandı; "Türkçe set yok" → "genel amaçlı set var, alan-özel değil".

---

## 0. PROJE KİMLİĞİ ve YÖNETİCİ ÖZETİ

| Alan | Değer |
|---|---|
| Proje adı | SorBI: Türkçe Doğal Dilden Sorgu Üretimi (BI eklentisi) |
| Analist | İhsan (analist + geliştirici — tek kişi bağımlılığı Böl. 15'te risk kaydı) |
| Sponsor / talep eden | Kurgu pilot: BI ürün sahibi / portföy vitrini |
| Tarih / Doküman sürümü | 24.07.2026 / v0.1 |
| Durum | ☑ Taslak ☐ İncelemede ☐ Onaylandı |

**Yönetici Özeti** *(en son yazıldı)*:

1. **Problem:** İş birimleri veri sorularını kendileri yanıtlayamıyor; her soru analiste rapor talebi olarak dönüyor ve yönetim bu bekleme maliyetini göremiyor.
2. **Kanıt:** Yalnızca geçen yıl kurgu pilotta ~480 ad-hoc talep, ortalama 2,5 iş günü bekleme, ≈576.000 TL analist zamanı (varsayım — pilotta doğrulanacak).
3. **Öneri:** Değerlendirilen 3 alternatif (yalnız-API, yalnız-yerel fine-tune, hibrit) arasından **hibrit: yerel Llama 3.2 3B + QLoRA + şema-RAG, API karşılaştırmalı** önerilmektedir.
4. **Maliyet/fayda:** İlk yatırım ~1.500 TL (bulut eğitim) + mevcut donanım olup geri ödeme süresi <6 ay; NBD 3 yıl ufukta pozitife geçmektedir.
5. **İstenen karar:** *Veri seti 1. ayda tamamlanır ve KVKK maskeleme onayı alınır* koşullarıyla 8 haftalık pilot geliştirme kararı talep edilmektedir.

> ✅ Öz-denetim: beş cümle ✓ · kaynaklı sayı var ✓ · karar koşullu ✓ · kip öneri ✓

---

## 1. PROBLEM TANIMI

**Tetikleyici türü:** ☑ Problem ☑ Fırsat (büyük dil modellerinin olgunlaşması)

**Problem paragrafı:** İş birimleri ve yöneticiler, veriye dair sorularını kendileri yanıtlayamıyor; her soru bir rapor talebi olarak analist ekibine iletiliyor. Talepler e-posta ve sözlü kanallardan geldiği için kurgu pilot vakada ayda ~40 ad-hoc talep oluşuyor ve ortalama yanıtlanma süresi 2,5 iş günü (varsayım — pilot görüşmesiyle doğrulanacak). Analist ekibinin zamanının ~%35'i daha önce yanıtlanmış, tekrarlayan taleplere gidiyor. Yönetim bu bekleme ve tekrar maliyetini göremiyor, çünkü talepler hiçbir yerde kayıt altına alınmıyor.

> ✅ Çözüm kelimesi yok ✓ · somut sayı var (varsayım etiketli) ✓ · iddialar atıflı ✓

---

## 2. PAYDAŞ ANALİZİ

| Paydaş | Rolü | Güç | İlgi | Strateji | Direnç/beklenti notu |
|---|---|---|---|---|---|
| Üst yönetim (sponsor) | Karar verici, ad-hoc soru soran | Y | Y | Yakından yönet | Beklenti: hız; direnç: yanlış sayıya güven kaybı tek seferde olur |
| SQL bilmeyen iş birimleri | Birincil son kullanıcı | D | Y | Bilgilendir | "Yanlış SQL üretirse ben nereden bileceğim?" güven sorunu |
| Analist/rapor ekibi | Hem kullanıcı hem doğrulayıcı | O | Y | Yakından yönet | **Direnç kaynağı #1:** "işimi elimden alacak" algısı; rolü doğrulayıcıya evrilir |
| BT/DBA | Şema erişimi, yetki veren | Y | O | Memnun tut | Üretim DB'sine LLM bağlanması güvenlik itirazı; salt-okunur hesapla ikna |
| KVKK/veri güvenliği sorumlusu * | Onay makamı | Y | D | Memnun tut | Dış API'ye şema/veri gönderimi kırmızı çizgi |
| Dış LLM/API sağlayıcısı * | Dış veri işleyen taraf | O | D | İzle | Fiyat/limit değişikliği; veri işleme sözleşmesi |

\* Yazılmayan paydaşlar — mevzuat ve dış bağımlılık taramasından bulundu.

> ✅ ≥6 paydaş ✓ · analist matriste değil ✓ · her satırda gerekçe notu ✓

---

## 3. FİZİBİLİTE (TELOS)

| Boyut | Risk (adı + kanıtı) | Önlem |
|---|---|---|
| Teknik | **VRAM darboğazı:** RTX 3060 6GB; 7B model QLoRA'da bile ~8-10 GB ister (HF/QLoRA raporları) | Llama 3.2 3B / Qwen2.5 3B + QLoRA (4-bit); 7B gerekirse bulutta tek seferlik eğitim, yerelde 4-bit çıkarım |
| Teknik-2 | **Türkçe veri seti yokluğu:** Spider/BIRD İngilizce; kamuya açık Türkçe text-to-SQL seti yok denecek kadar az (literatür) | Spider'ı makine çevirisi + elle düzeltme; şemadan sentetik soru-SQL üretimi |
| Ekonomik | **Yanlış tarafa yatırım:** eğitim maliyeti API'den pahalıya gelebilir | Karşılaştırma hesabı aşağıda; karar sayıya bağlandı |
| Legal | **KVKK:** dış API'ye giden istemde kişisel veri/şema sızıntısı | Yerel model varsayılanı; API modunda maskeleme + yalnız şema-metaveri gönderimi |
| Operasyonel | **Sessiz yanlış SQL:** çalışan ama yanlış sonuç veren sorgu güveni bitirir | SQL her zaman görünür + salt-okunur yetki + analist doğrulama akışı |
| Schedule | **Kritik yol = veri seti üretimi** (model eğitimi değil) | Veri üretimi 1. sprint'e alındı; eğitim onu bekler |

**Finansal hesap (kurgu pilot — tümü doğrulanacak):**

- İlk yatırım: ~1.500 TL (bulut eğitim, gerekirse) · Yıllık net fayda: ~400.000 TL (geri kazanılan analist zamanının temkinli %70'i) · İskonto oranı: %30
- **Geri ödeme süresi** = 1.500 ÷ 400.000 → ilk ayda; anlamlı maliyet parasal değil, ~4 haftalık veri seti emeği (≈160 saat)
- **NBD** (emek dahil yatırım ≈100.000 TL sayılırsa): Yıl 1: 307.700 · Yıl 2: 236.700 · Yıl 3: 182.100 → toplam bugünkü değer 726.500 **− ilk yatırım 100.000 = NBD ≈ +626.500 TL**
- **"Hiçbir şey yapma"nın yıllık maliyeti (baz çizgi):** 40 talep/ay × 2 saat × 600 TL/saat ≈ **576.000 TL/yıl** + ölçülemeyen bekleme maliyeti
- **Karar cümlesi:** "3 yıl ufkunda NBD pozitif; *veri seti 1. ayda biter ve KVKK onayı alınır* koşullarıyla hibrit mimariyle devam önerilir."

> ✅ Her boyutta risk ADI var ✓ · NBD'de −yatırım satırı ✓ · karar ufka bağlı ✓ · bekleme maliyeti hesaplandı ✓

---

## 4. PROJE BERATI

- **Amaç:** Türkçe doğal dil sorusunu, bağlı veritabanı şemasına uygun, doğrulanabilir SQL'e çeviren veritabanı-bağımsız bir yetenek geliştirmek.
- **Kapsam:** TR soru→SQL üretimi · şema RAG (dinamik şema bağlama) · SQL lehçe çevirisi · salt-okunur çalıştırma + sonuç tablosu · SQL'in kullanıcıya gösterimi
- **KAPSAM DIŞI:** 1. Yazma işlemleri (INSERT/UPDATE/DELETE) 2. Dashboard/görselleştirme tasarım aracı 3. ETL/veri kalitesi 4. İngilizce ve diğer diller 5. Kurumsal SSO/kullanıcı yönetimi
- **Başarı ölçütleri:** 1. 50 soruluk Türkçe test setinde execution accuracy: baz (prompt-only) %X'ten fine-tune+RAG ile **≥%80'e** 2. Ortalama yanıt süresi **≤10 sn** (yerel 4-bit) 3. Analiste düşen ad-hoc talep oranı **%100'den ≤%40'a** (pilot)
- **Kaba takvim:** H1-2 analiz + şema/veri seti · H3-4 RAG iskeleti (baseline) · H5-6 QLoRA fine-tune · H7 değerlendirme · H8 UAT + demo
- **Ana riskler (ilk bakış):** Türkçe veri seti kalitesi · 6GB VRAM sınırı · sessiz yanlış SQL · tek kişi bağımlılığı

**RACI:**

| İş | R (yapan) | A (hesap veren) | C (danışılan) | I (bilgilendirilen) |
|---|---|---|---|---|
| Gereksinim dokümanı | Analist (İhsan) | Sponsor | Analist ekibi, DBA | İş birimleri |
| Tasarım onayı | Analist (İhsan) | Sponsor | DBA, KVKK sorumlusu | Analist ekibi |
| UAT yürütme | Pilot kullanıcılar | Sponsor | Analist (İhsan) | BT |
| Geçiş kararı | BT | Sponsor | Analist ekibi, DBA | Tüm kullanıcılar |

> ✅ Kapsam dışı ≥3 ✓ · ölçütlerde sayı var ✓ · hiçbir satırda iki A yok ✓

---

## 5. BİLGİ TOPLAMA ve GÖRÜŞME RAPORU

**Yöntem planı:**

| Paydaş grubu | Yöntem | Neden bu yöntem |
|---|---|---|
| Analist/rapor ekibi | Görüşme | Derinlik: gerçek sorgu örnekleri ve talep akışının fiili işleyişi |
| İş birimi kullanıcıları | Anket + Gözlem | Genişlik: Türkçe soru kalıpları (eğitim verisi kaynağı); söylenen-yapılan farkı |
| Yöneticiler | Görüşme (kısa, elmas) | Karar soruları farklı: trend/karşılaştırma odaklı |
| BT/DBA | Görüşme + Belge inceleme | Yetki, şema dokümantasyonu, erişim politikaları |
| Geçmiş rapor talepleri | Belge inceleme | En sık sorular = test seti çekirdeği; sıklık sayıları |
| Literatür (Spider, BIRD, SQLCoder) | Belge inceleme | Kıyas: doğruluk oranları; yöntem seçimi kanıta bağlanır |

**Görüşme hazırlığı:** Yapı: Huni (rahat) · kılavuz soru ≥5, etiketli açık/kapalı · yönlendirici soru yasak · rapor 48 saat içinde.

**Görüşme raporu (Bulgu → Kanıt → Dönüşüm):**

| # | Bulgu | Kanıt (kurgu görüşme sözü) | Dönüşüm |
|---|---|---|---|
| 1 | Kullanıcılar tablo/kolon adı bilmiyor, iş terimiyle soruyor | "Ciro dediğimde hangi tablonun hangi kolonu, bilmiyorum" | Gereksinim: iş terimi ↔ şema sözlüğü (G-06) |
| 2 | Aynı sorular dönemsel tekrarlanıyor | Talep kayıtları: 20 sorunun ~%60'ı önceki dönemin kopyası | Gereksinim: sorgu geçmişi + önbellek (G-08) |
| 3 | Kamuya açık Türkçe text-to-SQL seti yok denecek kadar az | Literatür taraması (HF Hub, arXiv) | **Risk:** veri üretimi kritik yol; çeviri + sentetik plan |
| 4 | Sorular çoğunlukla göreli zaman içeriyor | "Geçen ay, son çeyrek, yılbaşından beri diye sorarız" | Gereksinim: göreli tarih deterministik (G-07) |
| 5 | Türkçe ekler/kısaltmalarla varlık adları bozuluyor | "Müşteriyle müşterinin farklı kelime sanıyor eski araç" | Gereksinim: morfolojik normalizasyon (G-09) |
| 6 | Analistler üretilen SQL'i görmeden sonuca güvenmez | "Sorguyu görmeden sayıyı yönetime taşımam" | Gereksinim: SQL görünür + kopyalanabilir (G-02) |
| 7 | Yanlış-ama-çalışan sorgu en büyük korku | "Hata verse anlarız; yanlış sayı verirse felaket" | **Risk:** sessiz hata; Gereksinim: güven skoru + netleştirme (G-03) |
| 8 | DBA üretim DB'sine doğrudan erişime karşı | "Salt-okunur replika dışında bağlantı vermem" | Gereksinim: read-only + zaman aşımı (G-14) |
| 9 | Şemalar müşteriden müşteriye değişiyor | "Her kurulumda tablo adları farklı" | Gereksinim: otomatik şema keşfi + kurulum indeksi (G-05) |
| 10 | Bazı kolonlar kişisel veri içeriyor | DBA: "CRM tablolarında kimlik alanları var" | **Risk (KVKK):** maskeleme (G-16); **Doğrulanacak:** kişisel veri tablo listesi |
| 11 | Yöneticiler sonucu tablo değil özet ister | "Bana satır listesi değil, trendi söylesin" | Gereksinim: doğal dil özeti (G-04); tasarım aracı değil |
| 12 | Maliyet sorgu başına değil deneme başına | Gözlem: doğru sonuca ortalama 3 denemede ulaşılıyor | **Doğrulanacak:** deneme katsayısı; hesap ×3 ile revize |
| 13 | Fine-tune küçük model ≈ prompt-only büyük model | SQLCoder/BIRD raporları: 7B fine-tune GPT-4 sınıfına yaklaşıyor | Mimari kanıtı: 3B+QLoRA vs RAG-only baseline kıyası (G-11) |
| 14 | JOIN'li sorular tek tablolulardan belirgin zor | BIRD kıyası: çok-tablolu doğruluk ~20 puan düşük | **Doğrulanacak:** test setinin JOIN oranı gerçek dağılımla eşleşmeli; **Risk:** ölçüt şişirme |

**Doğrulanacaklar (üçgenleme):** 40 talep/ay, 2,5 gün, %35 tekrar (kurgu varsayım → pilot talep kayıtları + görüşme) · kişisel veri tablo listesi (DBA sözü → şema taraması) · deneme katsayısı ×3 (gözlem → kullanım logları) · JOIN oranı (literatür → talep arşivi).

> ✅ Her sayı not edildi ✓ · bulgu türleri karışık ✓ · suçlama/nostalji/çözüm ayıklandı ✓

---

## 6. GEREKSİNİMLER

Kalıp: "Sistem, [koşul gerçekleştiğinde] [ölçülebilir eylemi] yapmalıdır." Teknoloji adları yok (Böl. 9'a). Kaynak = Bölüm 5 bulgu no.

| No | Kategori | Tür | MoSCoW | Gereksinim cümlesi | Kaynak |
|---|---|---|---|---|---|
| G-01 | Kullanıcı | F | Must | Sistem, Türkçe yazılmış bir soruyu aldığında çalıştırılabilir bir sorgu üretmelidir | B1, B5 |
| G-02 | Kullanıcı | F | Must | Sistem, ürettiği sorguyu sonuçla birlikte her zaman görünür ve kopyalanabilir biçimde sunmalıdır | B6 |
| G-03 | Kullanıcı | F | Should | Sistem, soru birden fazla yoruma açıksa sonuç üretmeden önce tek bir netleştirme sorusu sormalıdır | B7 |
| G-04 | Kullanıcı | F | Could | Sistem, sonuç kümesiyle birlikte en çok 2 cümlelik doğal dil özeti üretmelidir | B11 |
| G-05 | Veri | F | Must | Sistem, yeni veritabanı bağlantısı tanımlandığında tablo/kolon/ilişki metaverisini otomatik keşfedip arama indeksine eklemelidir | B9 |
| G-06 | Veri | F | Must | Sistem, iş terimlerini şema nesneleriyle eşleyen düzenlenebilir bir sözlük tutmalı ve sorgu üretiminde kullanmalıdır | B1 |
| G-07 | Veri | F | Must | Sistem, göreli zaman ifadelerini model tahminine bırakmadan takvim kuralıyla mutlak tarihe çevirmelidir | B4 |
| G-08 | Veri | F | Should | Sistem, her soru-sorgu çiftini geçmişe kaydetmeli; aynı soru tekrar sorulduğunda kayıtlı sorguyu önermelidir | B2 |
| G-09 | Teknik | F | Must | Sistem, Türkçe sorudaki çekim eklerini sorgu üretiminden önce kök biçime indirgemelidir | B5 |
| G-10 | Teknik | F | Must | Sistem, üretilen sorguyu hedef veritabanı lehçesine çevirerek en az 3 farklı veritabanı türünde çalıştırabilmelidir | Bağlam kararı |
| G-11 | Teknik | FO | Must | Sistem, 50 soruluk Türkçe test setinde en az %80 çalıştırma doğruluğu (execution accuracy) sağlamalıdır | B13, B14 |
| G-12 | Teknik | FO | Must | Sistem, tek soruya en geç 10 saniyede yanıt üretmelidir (yerel çıkarım modu) | Berat |
| G-13 | Fiziksel | FO | Must | Sistem, çıkarım aşamasında en fazla 6 GB grafik belleği olan tek kartlı iş istasyonunda çalışabilmelidir | Altyapı kısıtı |
| G-14 | Sistem arayüzü | F | Must | Sistem, kurum veritabanına yalnızca salt-okunur hesapla bağlanmalı ve 30 saniyeyi aşan sorguyu iptal etmelidir | B8 |
| G-15 | Sistem arayüzü | F | Should | Sistem, dış dil modeli servisini bağlantı başına açık/kapalı seçilebilir kılmalıdır | B10, TELOS |
| G-16 | Güvenlik | F | Must | Sistem, kişisel veri sınıfı işaretli kolon içeriklerini dış servise giden her istekte maskelemelidir | B10 |
| G-17 | Güvenlik | F | Must | Sistem, kim-ne zaman-hangi soru-hangi sorgu-kaç satır sonuç bilgisini değiştirilemez denetim izine yazmalıdır | B8, KVKK |
| G-18 | Güvenlik | F | Must | Sistem, SELECT dışındaki her sorgu türünü çalıştırma öncesi sözdizim düzeyinde reddetmelidir | B8, TELOS |
| G-19 | Kullanıcı | F | **Won't** | Sistem, bu sürümde İngilizce veya başka dilde soru kabul etmeyecektir — *gerekçe: Türkçe morfoloji hattı ve Türkçe eğitim seti kritik yolun kendisi; ikinci dil veri emeğini ikiye katlar, MVP doğruluk kanıtına katkısı yok. v2 adayı.* | Kapsam dışı 4 |
| G-20 | Veri | F | **Won't** | Sistem, bu sürümde hiçbir yazma sorgusu üretmeyecek ve çalıştırmayacaktır — *gerekçe: G-18 ile çift kilit; yazma yeteneği DBA itirazını (B8) ve KVKK riskini (B10) büyütür; salt-okunur MVP güven inşasının ön koşulu.* | B8, B10 |

**Diğer Won't notları:** görselleştirme tasarım aracı · kurumsal SSO/yetki matrisi · sorgu maliyet optimizasyonu — tümü v2 adayı, kapsam dışıyla tutarlı.

> ✅ 6 kategori dolu ✓ · her cümle test edilebilir ✓ · yasaklı kelime yok ✓ · teknoloji adı yok ✓

---

## 7. MANTIKSAL MODEL (Bağlam + DFD + Veri Sözlüğü)

**Bağlam diyagramı — tek süreç: "Türkçe Soru–Sorgu Çevrim Süreci"**

- Kullanıcı → soru metni, netleştirme cevabı, geri bildirim → süreç · süreç → sonuç + üretilen sorgu + özet → Kullanıcı
- Kurum veritabanı → şema metaverisi, sorgu sonucu → süreç · süreç → salt-okunur sorgu → Kurum veritabanı
- Dış dil modeli servisi (ops.) → sorgu taslağı → süreç · süreç → maskelenmiş bağlam istemi → servis
- Sistem yöneticisi → bağlantı tanımı, sözlük düzenlemesi → süreç · süreç → denetim raporu → yönetici

☑ Veri deposu bağlamda yok · ☑ her varlık hem veren hem alan

**Seviye 0 süreçleri:** 1·Soru ön işleme (G-07, G-09) · 2·Bağlam derleme (G-05, G-06, G-08) · 3·Sorgu üretimi (G-01, G-15) · 4·Doğrulama ve çalıştırma (G-10, G-14, G-18) · 5·Sunum ve kayıt (G-02, G-17) · **Depolar:** D1·Şema-terim indeksi, D2·Sorgu geçmişi ve denetim izi

**DFD dört-hata denetimi:** ☑ kara delik yok ☑ mucize yok ☑ gri delik yok ☑ süreçsiz akış yok ☑ dengeleme

**Veri sözlüğü (ana akış):**

```
soru_metni         : metin       — kullanıcının ham Türkçe sorusu (Kullanıcı)
normalize_soru     : metin       — kök indirgeme + mutlak tarihli hali (Süreç 1)
sema_baglami       : liste       — seçilmiş tablo/kolon metaverisi (D1)
uretilen_sorgu     : metin       — ANSI sorgu + hedef lehçe hali (Süreç 3-4)
guven_skoru        : ondalık 0-1 — netleştirme eşiği <0,6 (Süreç 3)
maskeleme_bayragi  : E/H         — dış servise gidişte zorunlu E (G-16)
calistirma_durumu  : kod         — BASARILI/SOZDIZIM_RED/ZAMAN_ASIMI/YETKI_RED
sonuc_satir_sayisi : tamsayı     — denetim izine yazılır (G-17)
```

---

## 8. VERİ TASARIMI (ER + Normalizasyon + İndeks)

*Not: Bu bölüm uygulamanın kendi deposunu tasarlar; hedef kurum veritabanı dış varlıktır.*

**Varlıklar ve ilişkiler:** KULLANICI 1:N SORU_OTURUMU 1:N SORGU_DENEMESI · BAGLANTI 1:N SEMA_NESNESI · TERIM N:M SEMA_NESNESI → kesişim: TERIM_ESLEME (bileşik PK: terim_id + nesne_id) · SORGU_DENEMESI 1:1 DENETIM_KAYDI

**Fazlalık avı:** Sorgu metni yalnız SORGU_DENEMESI'nde; şema adları yalnız SEMA_NESNESI'nde (FK ile gösterilir) — kopyalanan alan bulunmadı. **Normalizasyon:** ☑ 1NF ☑ 2NF ☑ 3NF

**İndeks kararları:**

| Ekran/rapor | Ürettiği WHERE | Önerilen indeks |
|---|---|---|
| "Bu soru daha önce soruldu mu" (G-08) | baglanti_id = ? AND soru_ozeti_hash = ? | (baglanti_id, soru_ozeti_hash) bileşik |
| Denetim raporu | tarih BETWEEN ? AND ? AND kullanici_id = ? | (kullanici_id, tarih) |
| Terim çözümleme | terim_kok = ? | terim_kok tekil indeks |

---

## 9. MİMARİ ve AĞ TASARIMI

**Ölçek verileri:** Kullanıcı: pilot 20-50 kişi, eşzamanlı ≤5 (varsayım — pilotta ölçülecek) · İşlem hacmi: ~200 soru/gün tepe · Veri hacmi: uygulama deposu <1 GB/yıl; vektör indeksi şema başına 10-50 MB

**Katman kararı (gerekçe ölçeğe bağlı):** Eşzamanlı ≤5 kullanıcı için mikroservis gereksiz; **tek sunuculu 3 katman**: (1) Sunum: Streamlit/basit web arayüzü (2) İş mantığı: Python + FastAPI; orkestrasyon LangChain; ön işleme Zemberek (G-09) + kural tabanlı tarih çözümleme (G-07); lehçe çevirisi SQLGlot (G-10) (3) Veri: uygulama deposu SQLite→PostgreSQL; vektör indeksi Chroma (yerel — ölçek gerekçesi). Model servisi ayrı süreç: llama.cpp/Ollama 4-bit GGUF.

**Dış bağımlılıklar:** OpenAI-uyumlu API (opsiyonel mod, G-15) → son-değer: erişilemezse yerel modele otomatik düşüş + mod etiketi · HuggingFace (yalnız kurulum anı) → model dosyası yerelde, çalışma zamanı bağımlılığı yok

**Güvenlik denetim listesi:** ☑ TLS ☑ Kimlik doğrulama (pilot tek kademe; v2 çift) ☑ En az ayrıcalık: salt-okunur hesap + tablo bazlı görünüm (G-14) ☑ Denetim izi (G-17) ☑ Yalıtım: üretim DB'sine yalnız replika/görünüm ☑ KVKK: maskeleme (G-16); geçmişte sonuç verisi değil yalnız satır sayısı

**Mimari karar kayıtları (ADR):**

| # | Karar | Alternatifler | Gerekçe |
|---|---|---|---|
| ADR-1 | Taban model: **Llama 3.2 3B-Instruct** (fine-tune hedefi) | 7B (Llama 3.1 / Qwen2.5-Coder-7B); yalnız API | 6 GB VRAM'de (G-13) 4-bit 3B hem eğitilir hem çıkarım yapar; 7B QLoRA bu kartta güvenilir sığmaz — gerekirse eğitim tek seferlik bulutta. B13: küçük+fine-tune, büyük+prompt'a yaklaşır |
| ADR-2 | Fine-tuning: **QLoRA** (4-bit taban + LoRA adaptörü) | Tam fine-tune; yalnız RAG/prompt | Tam FT 3B için bile ~24 GB ister; QLoRA ~5-6 GB. RAG-only baseline zaten ölçülüyor (G-11) — fine-tune ancak farkı kanıtlarsa kalıcı |
| ADR-3 | RAG: **LangChain + Chroma**; tablo başına belge + terim sözlüğü belgeleri (G-05/06) | LlamaIndex; elle pipeline | Ekosistem olgunluğu + hazır SQL araç zinciri; tek kişilik projede düşük bakım |
| ADR-4 | Model tek lehçe üretir (ANSI/SQLite); **SQLGlot** hedefe çevirir | Her lehçe için ayrı eğitim verisi | Eğitim setini N lehçeye kopyalamak veri emeğini katlar (kritik yol!); transpile deterministik ve test edilebilir |
| ADR-5 | Servis: **Ollama/llama.cpp 4-bit GGUF** | vLLM; HF Transformers | vLLM daha büyük ölçek ister; 6 GB kartta GGUF 4-bit en yüksek token/sn |

---

## 10. KULLANICI ARAYÜZÜ

| Ekran | Kullanıcısı | Cevapladığı soru | Tür |
|---|---|---|---|
| Soru ekranı (soru kutusu + SQL paneli + sonuç tablosu) | İş birimi, analist | "Sorumun cevabı ne ve hangi sorguyla geldi?" | Operasyonel |
| Netleştirme kartı (G-03) | İş birimi | "Sistem beni doğru anladı mı?" | Operasyonel |
| Geçmiş ekranı (G-08) | Analist | "Bu soru daha önce nasıl çözülmüştü?" | Operasyonel |
| Bağlantı ve sözlük yönetimi (G-05/06) | Sistem yöneticisi/DBA | "Hangi şemalar bağlı, terimler doğru eşli mi?" | Yönetsel |
| Yönetim dashboard'u | Sponsor/yönetici | "Yatırım kendini kanıtlıyor mu?" | Yönetsel |

**Nielsen denetimi (soru ekranı):** ☑ durum görünür (yerel/API mod etiketi) ☑ kullanıcı dili (ham SQL hatası yok) ☑ geri al ☑ tutarlılık ☑ hata önleme (takvim önerisi, netleştirme) ☑ tanıma>hatırlama (örnek sorular + otomatik tamamlama) ☑ kısayol ☑ sade ☑ hata mesajı: ne oldu + hangi alan + ne yapmalı ☑ yardım

**Yönetim dashboard'u = fizibilitenin karnesi:** Gösterge 1: analiste düşen talep oranı (%100→≤40) · Gösterge 2: execution accuracy haftalık trend (%80) · Gösterge 3: soru başına deneme sayısı (×3 varsayımının canlı ölçümü, B12). Renk kuralı: kritik bilgi renk + ikon + metin; çok kategoriye yatay bar.

---

## 11. OLAY TABLOSU

| Olay | Tetikleyici | Kaynak | Aktivite | Yanıt | Hedef |
|---|---|---|---|---|---|
| Soru soruldu | Kullanıcı gönderdi | Dış | Ön işle → bağlam → üret → doğrula → çalıştır | Sonuç + SQL | Kullanıcı |
| Güven skoru <0,6 | Üretim sonrası eşik | **Durum** | Netleştirme sorusu oluştur | Netleştirme kartı | Kullanıcı |
| Sorgu 30 sn'yi aştı | Zaman aşımı eşiği | **Durum** | Sorguyu iptal et, denetime yaz | Sadeleştirme önerisi | Kullanıcı |
| Gece 02:00 | Takvim | **Zamansal** | Şema yeniden keşfi + indeks tazeleme (G-05) | Değişiklik özeti | DBA |
| API bütçesi %80 | Sayaç eşiği | Durum | Bağlantıları yerel moda çevir, bildir | Uyarı | Yönetici |
| Ay kapanışı (ayın 1'i) | Takvim | Zamansal | Denetim + doğruluk raporu üret | Dashboard verisi | Sponsor |

> ✅ En az bir zamansal ✓ ve bir durum olayı ✓

---

## 12. İŞ AKIŞI (Swimlane)

**Kulvarlar:** Kullanıcı · Uygulama katmanı · Model servisi · Kurum veritabanı

**Ana akış:** 1·[Kullanıcı] soruyu yazar → 2·[Uygulama] kök indirgeme + tarih çözümleme → 3·[Uygulama] şema + terim bağlamı → 4·[Model] SQL taslağı + güven skoru → **K1: güven ≥0,6?** hayır → netleştirme kartı → 5·[Uygulama] sözdizim denetimi + **K2: SELECT mi?** hayır → red (G-18) → 6·[Uygulama] lehçe çevirisi → 7·[Kurum DB] salt-okunur çalıştırma + **K3: 30 sn?** → 8·[Uygulama] sonuç + SQL + özet, denetim izi → 9·[Kullanıcı] geri bildirim (doğru/yanlış — eğitim verisine döner)

**Devir noktası sayısı: 4** — bugün e-posta + analist + DBA arasında günler süren devirler sistemde saniyeler.

**İstisna akışı kararı:** Katı kural kullanıcıyı atlatmaya iter mi? → Evet: model yanlış SQL üretirse analist elle SQL yazmak ister. **Kontrollü bypass:** analist rolü elle SQL girebilir; aynı K2 (SELECT-only) ve denetim izinden geçer, bayraklanır — yaptırım değil kayıt. Hayati kontroller (salt-okunur + maskeleme) regülatif → **bypass yoktur**; API maskesi kapatılamaz, sistem alternatif üretir (yerel mod). *Gerekçe (paydaşla verilen politika kararı): elle yazılan doğru SQL'ler en değerli eğitim verisidir — yasaklamak veri kaynağını kurutur.*

---

## 13. TEST PLANI

**Piramit:** Birim (kök indirgeme, tarih çözümleyici, lehçe çevirici) → Entegrasyon (bağlam → model → doğrulayıcı zinciri) → Sistem (50 soruluk Türkçe test seti — **JOIN dağılımı gerçek talep arşiviyle eşleştirilmiş**, B14 önlemi) → Kabul (UAT: pilot kullanıcılar yürütür; RACI Böl. 4)

| TS (→G) | Ön koşul | Adımlar | Beklenen |
|---|---|---|---|
| TS-01 → G-01/11 | Demo şema (8 tablo) indeksli; test seti hazır | "Geçen ay en çok muayene yapan 5 doktor kim?" | Çalışan SQL + doğru 5 satır; 50 soruda ≥%80 execution accuracy |
| TS-02 → G-02 | Herhangi bir başarılı sorgu | Sonuç ekranı incelenir | SQL paneli görünür, kopyala düğmesi çalışır |
| TS-05 → G-05 | Yeni SQLite bağlantısı tanımlanır (12 tablo) | Kurulum tamamlanır | 12 tablonun tamamı metaverisiyle indekste; süre ≤5 dk |
| TS-06 → G-06 | Sözlükte ciro=satis_tutari eşi | "Toplam ciro nedir?" | Üretilen SQL satis_tutari kolonunu kullanır |
| TS-07 → G-07 | Sistem tarihi 15.07.2026 | "Son çeyrek" içeren soru | WHERE 01.04.2026–30.06.2026 (kural çıktısı, model tahmini değil) |
| TS-09 → G-09 | — | "Müşterilerimizin şehirlere dağılımı" | Ön işleme kökleri: müşteri, şehir, dağılım |
| TS-10 → G-10 | Aynı soru; SQLite + PostgreSQL + MSSQL hedefleri | Üç hedefte çalıştır | Üçünde de sözdizim hatasız eşdeğer sorgu |
| TS-12 → G-12/13 | 6 GB kartlı makine, 4-bit model | 20 ardışık soru | Ortalama yanıt ≤10 sn; bellek taşması yok |
| TS-14 → G-14 | 50 sn süren ağır sorgu | Sorgu tetiklenir | 30. saniyede iptal + sadeleştirme önerisi + denetim kaydı |
| TS-16 → G-16 **(NEGATİF)** | API modu açık; TCKN kolonu kişisel veri işaretli | Müşteri listesi sorusu; dış istek ağ kaydı incelenir | İstek gövdesinde ham TCKN YOK (kanıt: ağ kaydı) |
| TS-17 → G-17 | 3 farklı kullanıcı 3 soru sorar | Denetim raporu çekilir | Her satırda kim-zaman-soru-sorgu-satır sayısı; değiştirilemez |
| TS-18 → G-18 **(NEGATİF)** | — | "Geçen yılki kayıtları sil" | ÇALIŞTIRILMAZ; sözdizim reddi + açıklama + denetim kaydı |

> ✅ Her Must için en az bir senaryo ✓ · negatif senaryo var (TS-16, TS-18) ✓

---

## 14. GEÇİŞ STRATEJİSİ

| Strateji | Bu proje için artı | Bu proje için eksi |
|---|---|---|
| Doğrudan | Hızlı | Yanlış SQL güveni tek günde bitirir — kabul edilemez |
| Paralel | Analist raporu = doğrulama kaynağı | Analist yükü geçici artar |
| Pilot | Tek departman + demo şemayla risk sınırlı | Yaygınlaşma kanıtı gecikir |
| Aşamalı | Modül modül | Değer kanıtı en sonda |

**Seçim + gerekçe:** **Pilot + paralel karışımı** — tek departmanda açılır; ilk 4 hafta analist aynı soruları eski usul de yanıtlar, iki sonuç kıyaslanır (execution accuracy'nin canlı ölçümü). Finansal raporlamada yanlış sayı maliyeti yüksek → paralel doğrulama şart.

**Eski sistemin AKTİF rolü:** Analistin elle yazdığı SQL'ler paralel dönemde "doğrulayan otorite"dir ve eğitim setine akar — çöpe atılmaz, emekli edilir.

---

## 15. RİSK TABLOSU

| Risk | Olasılık | Etki | Önlem | Sahibi |
|---|---|---|---|---|
| Türkçe veri seti kalitesi düşük → %80 tutmaz | Y | Y | Çeviri + sentetik + elle düzeltme; 2. haftada ara ölçüm — %60 altıysa 7B buluta geç (ADR-1 B planı) | Analist/geliştirici |
| Tek kişi bağımlılığı | Y | O | ADR'ler + kurulum dokümante (Böl. 16); repo + README | Analist/geliştirici |
| Sessiz yanlış SQL güven kaybettirir | O | Y | Paralel kıyas + güven eşiği + SQL görünürlüğü (G-02/03) | Analist ekibi |
| API fiyat/politika değişikliği | O | D | Yerel varsayılan (ADR-1); bütçe olayı (Böl. 11) | Yönetici |
| Kullanıcı eski usule geri kaçar | O | O | Geçmiş ekranı + öneriler; dashboard kullanım göstergesi | Sponsor |

---

## 16. BELGELENDİRME PLANI

☑ Teknik/sistem dokümantasyonu (mimari + ADR'ler + eğitimin yeniden üretim adımları) ☑ Kullanıcı kılavuzu (kullanıcı dilinde, ekran ekran) ☑ İşletim dokümanı (model yedekleme, indeks yeniden kurma — "analist tatildeyken okunacak sayfa") ☑ Eğitim materyali (10 dk demo video — portföy vitrini)

**Sürümleme kuralı:** Belge kodla birlikte sürümlenir — adaptör v2 olduysa kılavuz v1 kalamaz. **Sorumlusu:** analist/geliştirici (İhsan).

---

## SON KONTROL — YEDİ TUZAK AVI

☑ 1. Problem tanımında çözüm kelimesi yok ☑ 2. Ölçüsüz gereksinim yok ☑ 3. NE/NASIL karışmadı (teknoloji adları yalnız Böl. 9) ☑ 4. Fazlalık yok ☑ 5. Tek kaynaklı iddialar "doğrulanacak" işaretli ☑ 6. Kapsam dışı + Won't dolu ve tutarlı ☑ 7. Karar cümleleri koşullu ☑ +. Yönetici özeti EN SON yazıldı ve başa taşındı

---

## EK: MİNİMUM GEREKSİNİM (MVP) — UYGULAMA SIRASI

1. **Demo şema + 50 soruluk test seti** (G-11'in ölçüm zemini — kritik yol)
2. **Şema keşfi + Chroma indeksi** (G-05)
3. **Ön işleme hattı** (G-07, G-09)
4. **RAG-only baseline** (G-01) — ilk accuracy ölçümü
5. **Güvenlik çekirdeği** (G-14, G-18)
6. **SQL görünürlüğü + basit arayüz** (G-02)
7. **QLoRA fine-tune** (G-11) — ancak baseline %80 altındaysa
8. **Lehçe çevirisi** (G-10)
9. **Denetim izi + maskeleme** (G-16, G-17)
10. Should'lar (G-03, G-08, G-15) → pilot geri bildirimiyle

*Kural: 4. adımdaki baseline ölçülmeden 7. adıma geçilmez — ADR-2'nin koşulu.*
