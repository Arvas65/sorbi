# SorBI — Plan (FDE yöntemiyle)

**Sürüm:** 1.0 · **Tarih:** 2026-09-30 · **Karar sahibi:** İhsan Arvas
**Yerini aldığı:** `docs/tasarim/PLAN.md` (v4 planı, 2026-08-28). Onun iş paketi
numaraları (İP-43…58) ve SPEC gereksinimleri aynen geçerli; değişen **sıra** ve
**çerçeve**.

**Durum:** Faz A ✔ (2026-09-30). **Faz B ONAYLANDI** (İhsan, 2026-09-30) — Build'de.

---

## 0. Neden yeniden sıralandı

v4 planı çekirdeği önce, kenarları sonra kurmayı öngörüyordu. Bu mantıklıydı ve
çekirdek gerçekten yazıldı. Ama sonuç, **kullanıcının hiç göremediği ~2.000
satır** oldu (BULGU-39). Üstüne üç hafta ölçüm hattının kendisine gitti ve ürün
3 Eylül'de durdu.

FDE'nin ilk kuralı tersini söyler: **müşterinin önüne en erken, en ince,
uçtan uca çalışan dilimi koy; sonra kalınlaştır.** Bu plan o kuralla yeniden
sıralandı. Hiçbir SPEC gereksinimi düşmedi.

## 1. FDE çerçevesi — bu projenin FDE'ye ne kazandırdığı

İhsan'ın FDE yolunda kapatacağı dört boşluk var. Bu plan dördüne de doğrudan
kanıt üretecek şekilde kuruldu:

| FDE boşluğu | Bu planda nerede kapanır | Çıktı |
|-------------|--------------------------|-------|
| Dış müşteri kanıtı | Faz C — kurgusal müşteriyle tam keşif → teslim döngüsü, Faz E — hastane pilotu | Keşif notu, kabul demosu kaydı |
| Bulutta üretim dağıtımı | Faz C — Azure Container Apps + yönetilen Postgres | Canlı URL, IaC dosyası |
| Canlı İngilizce teknik anlatım | Faz D — 10 dk demo videosu + müşteri sunumu | Video, sunum |
| Yazılı vaka çalışması | Faz D — İngilizce case study | `docs/vaka/` |

**FDE ritüeli her fazda aynı:** keşif (müşteri ne istiyor, ne *demiyor*) →
ayrıştırma (en küçük teslim edilebilir parça) → ince dilim → sahada sına →
geri bildirimle kalınlaştır → yazıya dök.

## 2. Müşteri sırası (2026-09-30 kararı)

1. **Müşteri 1 — Marmara Dağıtım A.Ş.** (kurgusal). Orta ölçekli bir toptan
   dağıtım şirketi; Postgres'te ~20 tablo, dağınık şema: iptal bayrakları,
   yumuşak silme, bir satırda üç farklı tarih, tutarsız adlandırma. Gizlilik
   vaadi yok → **API modu serbest** (ADR-5 B). Kullanıcı hikâyesi ve brief
   İngilizce yazılır: vaka çalışmasının hammaddesi.
2. **Müşteri 2 — hastane pilotu** (TGH, izin alınırsa). KVKK, **yalnız yerel
   mod**, salt-okunur replika. Önkoşul: Faz C'nin kanarya testi (İP-54) yeşil.
   İzin alınamazsa pilot, hastane şemasının sentetik kopyasıyla yapılır ve öyle
   damgalanır.

## 3. Fazlar

Tahminler **odak-saat**. Haftalık bütçe 12–15 saat, FDE talimi dahil; SorBI'ye
düşen gerçekçi pay **~8 saat/hafta**. Claude'un yazdığı kısım saate dahil
değil; darboğaz İhsan'ın kalemleri ve kapıları.

### Faz A — Toparlama ✔ (bu PR)

- master, v4 çekirdek dalına hızlı-ileri sarılır; iş artık master'da
- Gece ölçüm hattı emekli, belge yığını arşivde; `docs/` = plan + kararlar + tasarım + kanıt özü
- `46-yama` (BULGU-35) uygulandı; ADR'ler `docs/kararlar/`'da, ADR-5 güncel taslak
- **İhsan'ın bu hafta yapacağı üç şey** (her biri ≤15 dk):
  1. ~~`parola.bat` ile admin parolasını döndür~~ (BULGU-15) — ✔ 2026-09-30
  2. ~~Bu PR'ı merge et~~ — ✔ master `4579208`
  3. ~~ADR-5 § 6~~ — ✔ **B** · ~~BULGU-27~~ DÜZELT ✔ · BULGU-18 SONRA (İP-56)

### Faz B — Uçtan uca ince dilim ("walking skeleton") · ~3 hafta

**Hedef tek cümle:** Streamlit'te yeni bir "Pano (v4)" sayfasında, hastane demo
veritabanına Türkçe bir soru sorulur ve **çekirdekten geçen** bir pano döner.
Kalite değil, **akış**. Her kutu en basit hâliyle vardır.

| İP | İş | Yazan | Kabul |
|----|----|-------|-------|
| **İP-43** | Yürütücü: `Yurutucu` portunun gerçek uygulaması — sunucu tarafı zaman aşımı, `SET TRANSACTION READ ONLY`, sunucu tarafı `LIMIT`, bağlantı havuzu. SQLite + Postgres | **İhsan** (güvenlik-kritik; Claude eşlik eder) | Sözleşme testi iki lehçede yeşil; Postgres'te `pg_sleep(60)` 30 sn'de `ZAMAN_ASIMI`; yazma denemesi reddedilir |
| **İP-53a** | Eşleyici (ince): LLM soruyu anlam modelinin **sözlüğüne** göre bir `Secim` JSON'una çevirir. Serbest SQL üretmez | Claude | Sözlük dışı ad üretirse `gecersiz`; 10 soruluk duman seti |
| **İP-55a** | Pano sayfası (ince): soru kutusu → `Secim` → `derle` → `Yurutucu` → `pano` → tek grafik + **SQL gösterimi** + satır sayısı | Claude | Uçtan uca demo, hastane DB'sinde |
| **İP-45** | ADR-5/8/9 koda: `config.py`'de `ANLAM_KATMANI`, müşteri bağlantısında `MODE` kilidi | Claude yazar, İhsan imzalar | Demo dışı bağlantıda API modu açılamıyor testi |

Anlam modeli bu fazda **elle yazılmış bir dosyadan** yüklenir (hastane için
`tests/cekirdek/ornek.py` zaten bir tane içeriyor). Sihirbaz Faz C'de.

**Faz B sonu:** bağımsız review (yapımı görmemiş alt-ajan) + triyaj.
**FDE çıktısı:** 2 dakikalık ekran kaydı — "soru → pano, SQL görünür".

### Faz C — Müşteri 1: keşif, sihirbaz, bulut · ~4 hafta

| İP | İş | Yazan | Kabul |
|----|----|-------|-------|
| **C-0** | **Keşif:** Marmara Dağıtım brief'i (İngilizce, 1 sayfa) — kim kullanır, hangi 10 soruyu sorar, neyi *sormaz*. Şema bu brief'ten üretilir | İhsan yazar, Claude karşı-sorgular | Brief + 10 iş sorusu + başarı ölçütü |
| **C-1** | `demo/seed_marmara.py`: Postgres, ~20 tablo, bilinçli dağınıklık | Claude | Docker Compose'da ayağa kalkar |
| **İP-51/52** | Ön-doldurma zaten var (`on_doldurma.py`); **etiketleme sihirbazı** + değer sözlüğü + satır sayısı göstergesi (R-6'nın çaresi) | Claude yazar, **İhsan UX triyajı** | 20 tabloda tek oturumda biter; etiketlenmemiş tablo sorguya girmez ve bu yazılır |
| **İP-53b** | Eşleyici tam: netleştirme soruları + zaman tanesi | Claude | Belirsiz soruda soru sorar, tahmin etmez |
| **İP-54** | **Kanarya:** tam oturum sonrası kanarya dizesi ne dışarı giden gövdelerde ne diskte | **İhsan** (gizlilik-kritik) | Kanarya yeşil — hastane pilotunun önkoşulu |
| **C-2** | **Azure dağıtımı:** Container Apps + Azure Database for PostgreSQL; anahtar Key Vault'tan (BULGU-40); IaC (Bicep) depoda. **Yalnız sentetik veri:** yabancı bulut KVKK md. 9 anlamında yurt dışı aktarımdır; müşteri verisi buraya girmez (docs/guvenlik § 1) | İhsan yapar, Claude eşlik eder | Canlı URL; sır imajda ve depoda yok; kapatma/açma tek komut |

**Faz C sonu:** H-3 kabul demosu — ekip dışından biri Marmara DB'sini bağlar,
≤30 dk etiketler, 3 soru, **3 kullanılabilir pano, elle düzeltme yok.**
Oturum kaydedilir.

### Faz D — Ölçü ve anlatı · ~2 hafta

| İP | İş | Kabul |
|----|----|-------|
| **İP-56** | Etiketleme cetveli (**F-2:** önerilen alanların kaçı değiştirilmeden kabul edildi — ürünün ticari değerinin tek sayısı) + eşleme cetveli | İki cetvel CI'da ya da tek komutla |
| **İP-50** | `guven.py`'nin `Secim`'e taşınması; mutasyon karnesi önce/sonra | Karne düşmez |
| **D-1** | **Case study (İngilizce):** problem → keşif → neden serbest SQL değil derleyici → sonuç sayıları → ne öğrenildi | `docs/vaka/marmara.md` |
| **D-2** | 10 dk İngilizce demo videosu | Kayıt |

### Faz E — Müşteri 2: hastane pilotu · izne bağlı

**Güvenlik kapısı** (`docs/guvenlik/GUVENLIK.md` § 5): G2 + G3 + G4 tamam, kanarya
yeşil, yalnız kurum içi kurulum. Ticari takvimle esnetilmez.

Yerel mod, salt-okunur replika, kanarya yeşil, KVKK değerlendirmesi yazılı.
Kapsamı Faz D'nin sonunda, pilotun cevabına göre planlanır. Bugünden
planlanmaz.

## 4. Eleştirel yol ve takvim

```
A (bu hafta) → İP-43 ─┐
                      ├→ İP-55a (uçtan uca) → C-0 → C-1 → İP-52 → İP-54 → C-2 → H-3 → D
        İP-53a ───────┘
```

**Takvimi belirleyen kalem İP-43** (İhsan, güvenlik-kritik). Claude onu
beklerken İP-53a ve İP-45'i paralel yürütür.

**Dürüst takvim:** 8 saat/hafta ile Faz B–D **~9–10 hafta** → Aralık ortası.
Qlik görüşmesi daha yakınsa: Faz B + C'nin sihirbazsız hâli (anlam modeli
elle) ile **"kısmi" damgalı** bir demo 4–5 haftada çıkar. Kabul metni
değişmez, damga değişir.

## 5. Bilinçli olarak yapılmayacaklar

- **Gece otomasyonu yok.** Ölçüm bir PR modeli, istemi ya da derleyiciyi
  değiştirdiğinde elle alınır. Otomasyon, ürün bir müşteride çalışır hâle
  geldikten sonra — ve o zaman bulutta — yeniden düşünülür.
- **v3 serbest SQL yolu silinmez.** `ANLAM_KATMANI=0` geri alma yoludur.
  Emekliliği Faz D'nin sonunda, cetvel iki yolu karşılaştırdıktan sonra karar.
- **Tahmin (forecasting) ve modül ekranı v5'te** (v4 CLARIFY kararı).

## 6. Kapı

```
Faz A  ✔ merge edildi (2026-09-30)
Faz B  ✔ ONAY (2026-09-30) → BUILD
```
