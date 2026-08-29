# SorBı v4 — PLAN

**Sürüm:** taslak 1.0 · **Tarih:** 2026-08-28 · **Karar sahibi:** İhsan Arvas
**Durum:** **KAPI 1 — onay bekliyor.** Onay gelmeden tek satır kod yazılmaz.
**Ekler:** MIMARI.md · ADR-8 · ADR-9 · SPEC.md

---

## 0. Bu belge nasıl okunur

Onayın üç biçimi var (iş hattı §4): **ONAY** → Build başlar · **DEĞİŞTİR: …** →
plan revize edilir · **DUR** → İP rafa kalkar, gerekçe buraya yazılır.

Her İP satırında: bağımlılık · yazan · dokunulacak dosyalar · geri alma · tahmin.
Tahminler **gün-adam**, takvim günü değil.

---

## 1. Faz yapısı ve neden bu sıra

```
FAZ 0  Devralınan BLOK borç      ── müşteri DB'sine bağlanmadan kapanmalı
   ↓
FAZ 1  Çekirdek (saf)            ── LLM'siz, DB'siz; cetvel Katman 1 burada doğar
   ↓
FAZ 2  Kenarlar (IO)             ── sihirbaz, eşleyici, sınırlar, çizim
   ↓
FAZ 3  Ölçü ve kabul             ── yeni cetveller + H-3 kabul demosu
```

**Sıranın gerekçesi:** Faz 0 önce, çünkü v4'ün tamamı "yabancı bir veritabanına
bağlanmak" üzerine kurulu ve bugün o bağlantıda ne zaman aşımı ne salt-okunurluk
gerçek. Faz 1 ikinci, çünkü çekirdek saf olduğu sürece Faz 2'nin her parçası
sahte (mock) ile geliştirilebilir — kenarlar çekirdeği beklemez ama tersi doğru
değildir.

---

## 2. FAZ 0 — Devralınan BLOK borç · 4 gün-adam

| İP | İş | Gereksinim | Bağımlılık | Yazan | Tahmin |
|----|----|-----------|-----------|-------|--------|
| **İP-43** | Yürütücü sözleşmesi + gerçek zaman aşımı ve salt-okunurluk | SPEC E-3 | — | **İhsan** | 2 g |
| **İP-44** | Oturum bağlamı — süreç geneli durum kaldırılır | SPEC E-4 | — | Claude | 1,5 g |
| **İP-45** | ADR-5/8/9 koda iner | SPEC E-6 | — | Claude yazar, **İhsan imzalar** | 0,5 g |

**İP-43 · Yürütücü sözleşmesi.**
*Neden İhsan:* rol dağılımı — güvenlik kapısı. Ayrıca v3'ün en pahalı hata
sınıfı burada (söz belgede, uygulama yok) ve bunun bir kez elle yazılması
öğrenme değeri taşıyor.
*Dokunulacak:* `app/executor.py` → `app/baglanti/yurutucu.py` (bölünür) ·
`tests/sozlesme/test_yurutucu.py` (yeni) · `docker-compose.yml` (Postgres servisi) ·
`app/config.py` (havuz ayarları)
*Kapsam:* Postgres `statement_timeout` · MySQL `max_execution_time` · MSSQL sorgu
zaman aşımı · oturum düzeyinde `SET TRANSACTION READ ONLY` · `yazma_denemesi()` ·
sunucu tarafı `LIMIT` (bugün `fetchmany` istemci tarafında) · bağlantı havuzu
(bugün her çağrıda `create_engine`)
*Kabul:* sözleşme takımı her uygulamada yeşil; gerçek Postgres'te `pg_sleep(60)`
30 sn'de `ZAMAN_ASIMI`. MSSQL sınanamazsa **"doğrulanmadı" damgalanır.**
*Geri alma:* eski `executor.run()` bir sürüm boyunca korunur; anahtar
`YURUTUCU_V2=0` ile eskiye dönülür.

**İP-44 · Oturum bağlamı.**
*Dokunulacak:* `app/pipeline.py` (`_index` tekili) · `app/connections.py`
(`aktifle` mutasyonu) · yeni `app/akis/baglam.py` · `ui/ortak.py`
*Kabul:* iki bağlantı + iki anlam modeliyle eşzamanlı çağrı testi.
*Geri alma:* dal birleştirilmez; tek dosyalık geri alma.

**İP-45 · ADR'ler koda.**
*Dokunulacak:* `app/config.py` (`MODE` müşteri bağlantısında kilitli,
`ANLAM_KATMANI`, `ANLAM_DIZINI`) · `docs/is-hatti/v4/ADR-*.md` (karar bölümleri)
*Kabul:* demo dışı bağlantıda API modunun açılamadığını gösteren test.
*Not:* ADR-5'in karar satırını **İhsan imzalar** — Ship kapısı malzemesidir.

> **Faz 0 sonu:** bağımsız review + İhsan triyajı. Ölçülebilir çıktı: sözleşme
> takımı yeşil, gerçek Postgres üzerinde.

---

## 3. FAZ 1 — Çekirdek (saf) · 9,5 gün-adam

| İP | İş | Gereksinim | Bağımlılık | Yazan | Tahmin |
|----|----|-----------|-----------|-------|--------|
| **İP-46** | Anlam modeli + doğrulama + portlar | A-1 | — | Claude | 1,5 g |
| **İP-47** | **Seçim + derleyici + 40 altın çift** | B-1, B-2, F-1 | İP-46 | **İhsan** | 4 g |
| **İP-48** | Pano derleyici — deterministik grafik seçimi | D-1 | İP-46 | Claude | 1,5 g |
| **İP-49** | Maskeleme derleme anında + serileştirme | E-5, G-1 | İP-47 | Claude | 1 g |
| **İP-50** | `guven.py`'nin `Secim`'e taşınması | ADR-8 sonucu | İP-47 | Claude, İhsan triyaj | 1,5 g |

**İP-47 — planın en kritik maddesi.**
*Neden İhsan:* rol dağılımı "güvenlik-kritik" der; derleyici dar anlamda
güvenlik değil ama **doğruluk-kritik**tir ve v4'ün yeni sessiz-yanlış doğum
yeridir (SPEC R-3). Oradaki bir hata *tutarlı* olur, yani hiçbir kontrol
yakalamaz. Ayrıca eleştirel yolun en uzun tek kalemi bu — takvimi belirleyen
madde.
*Dokunulacak:* `app/cekirdek/secim.py` · `app/cekirdek/derleyici.py` ·
`tests/cekirdek/altin/*.json` (40 çift)
*Kapsam sınırı:* **tek olay tablosu + ona bağlı boyutlar.** Çoklu olay tablosu
üreten seçim reddedilir (SPEC R-3). Bu sınır İP-47'nin ilk yarım gününde
hastane şeması üzerinde sınanır — `randevu → muayene → fatura` bir zincir mi,
gerçek bir fan-out mu; sonuç PLAN'a geri yazılır.
*Geri alma:* `ANLAM_KATMANI=0` → v3 serbest SQL yolu.

**İP-50 · `guven.py` taşınması.** ADR-8 §3'ün ölçülebilir sonucu: AST
arkeolojisi (`_agac`, `_sql_tablolari`, `_takma_ad_haritasi`,
`_metin_sabitleri`, `_kolon_degerleri`, `_filtre_degerleri`) düşer; kalan
kontroller `Secim` üzerinde çalışır.
*Kabul:* mutasyon karnesi (`eval/guven_olcum.py`) taşınmadan **önce ve sonra**
koşar; düşerse taşıma geri alınır. Karne bir regresyon nöbetçisidir — burada
tam olarak o iş için kullanılır.

> **Faz 1 sonu:** bağımsız review + triyaj. Ölçülebilir çıktı: cetvel Katman 1
> (40 altın çift) CI'da yeşil, saniyeler içinde, LLM'siz.

---

## 4. FAZ 2 — Kenarlar (IO) · 11,5 gün-adam

| İP | İş | Gereksinim | Bağımlılık | Yazan | Tahmin |
|----|----|-----------|-----------|-------|--------|
| **İP-51** | Ön-doldurma + anlam deposu + şema kayması | A-2, A-5 | İP-46 | Claude | 2,5 g |
| **İP-52** | Etiketleme sihirbazı + değer sözlüğü + satır sayısı göstergesi | A-3, A-4, R-6 | İP-51 | Claude yazar, **İhsan UX triyajı** | 3 g |
| **İP-53** | Eşleyici + netleştirme + zaman tanesi | C-1, C-2, C-3 | İP-47 | Claude | 2 g |
| **İP-54** | **Sınır 1 + Sınır 2 + kanarya testi** | E-1, E-2 | İP-53 | **İhsan** | 1,5 g |
| **İP-55** | Pano render + filtre şeridi + bayraklar + SQL gösterimi | D-2…D-5 | İP-48, İP-52 | Claude | 2,5 g |

**İP-52 · Sihirbaz — R-6'nın çaresi burada.** Her cevabın yanında satır sayısı
gösterilir: *"bu geçerlilik filtresiyle 12.480 satır kalıyor, 1.204 satır
düşüyor."* İnsan sağlamayı gözle yapar. Bu, planın **ölçülemeyen tek riskine**
(insan yanlış etiketlerse her cevap tutarlı biçimde yanlış olur) verilen tasarım
cevabıdır — daha iyi bir fikir varsa İP başlamadan söylenmeli.
*Dokunulacak:* `ui/sihirbaz/*` · `app/akis/etiketle.py` · `app/baglanti/sema_kaynagi.py`
*Kabul:* 20 tablolu demo şemada tek oturumda bitirilebilir; etiketlenmemiş tablo
sorguya girmez ve bu **yazılır**.

**İP-54 · Kanarya.** *Neden İhsan:* gizlilik-kritik; ürünün müşteriye
gösterilebilir tek "kendiniz koşun" testi bu.
*Dokunulacak:* `tests/sinir/test_kanarya.py` · `app/baglanti/onbellek.py` ·
`app/audit.py` · `demo/seed_*.py` (kanarya dizesi)
*Kabul:* tam oturum sonrası kanarya ne giden gövdelerde ne diskte.

> **Faz 2 sonu:** bağımsız review + triyaj. Ölçülebilir çıktı: uçtan uca bir
> pano, hastane şemasında, kanarya yeşil.

---

## 5. FAZ 3 — Ölçü ve kabul · 5,5 gün-adam

| İP | İş | Gereksinim | Bağımlılık | Yazan | Tahmin |
|----|----|-----------|-----------|-------|--------|
| **İP-56** | Etiketleme cetveli + eşleme cetveli | F-2, F-3 | İP-52, İP-53 | Claude | 2,5 g |
| **İP-57** | BULGU-18 ikinci cetvel + damga + haftalık kadans | F-4, F-5, F-6 | — | Claude | 1 g |
| **İP-58** | Postgres + satış şeması + **kabul demosu** | H-1, H-2, H-3 | tümü | birlikte | 2 g |

**İP-56 · F-2 Qlik masasına gidecek sayıyı üretir:** önerilen anlam modeli
alanlarının kaçının değiştirilmeden kabul edildiği. Bu, ürünün ticari değerinin
tek ölçüsüdür ve sıkışma hâlinde **kesilmez** (§7).

**İP-58 · Kabul demosu = turun çıkış koşulu** (SPEC §7). Beşi aynı oturumda:
tanımadığı DB · ≤30 dk etiketleme · üç soru · üç pano · kanarya yeşil.

---

## 6. Toplam, eleştirel yol, takvim

| | Gün-adam |
|---|---|
| Faz 0 | 4 |
| Faz 1 | 9,5 |
| Faz 2 | 11,5 |
| Faz 3 | 5,5 |
| **Toplam** | **30,5** |
| — bunun **İhsan'a düşeni** | **~8** (İP-43, İP-47, İP-54 + triyajlar) |
| — Claude'a düşeni | ~22,5 |

**Eleştirel yol:** İP-43 → İP-46 → **İP-47** → İP-48/49 → İP-51 → İP-52 →
İP-53 → İP-55 → İP-58.

**Takvimi belirleyen tek kalem İP-47** (4 gün, İhsan, eleştirel yolda).
Paralel yürüyebilenler: İP-44, İP-45, İP-50, İP-57.

**Dürüst takvim tahmini:** Claude sürekli çalışabilir; darboğaz İhsan'ın üç
kalemi. Akşamları çalışıldığı varsayımıyla **4–6 hafta**. Bu, daha önce sözlü
olarak söylenen "8–10 gün"den büyük — çünkü o tahmin ürünün yalnız pano tarafı
içindi; anlam katmanı ve devralınan BLOK borç o sayıya dahil değildi. Sayıyı
küçültmek yerine düzeltiyorum.

---

## 7. Sıkışma yolu — Qlik tarihi yakınsa

| Kesilen | Kazanç | Bedel |
|---|---|---|
| İP-50 (`guven.py` taşınması) | 1,5 g | Güven katmanı v3'ün AST yolunda kalır — çalışır ama çirkin |
| İP-57 (damga, kadans, BULGU-18) | 1 g | Ölçüm hijyeni gecikir |
| İP-56'nın **F-3 yarısı** (60 soruluk eşleme seti) | 1,5 g | Yeni birincil cetvel demo sonrasına kalır |
| İP-43'ün MySQL/MSSQL yarısı | 0,5 g | Yalnız Postgres doğrulanır, gerisi "doğrulanmadı" damgalı |
| **Toplam kazanç** | **~4,5 g** | |

**Kesilmeyecekler — gerekçeleriyle:**
- **İP-54 (kanarya):** demonun ayırt edici parçası. Kesilirse gizlilik vaadi
  sınanmamış olur; o vaat olmadan A/B/C konumlarının hiçbiri ayakta durmaz.
- **İP-56'nın F-2 yarısı:** Qlik masasına götürülecek tek sayı.
- **İP-47'nin 40 altın çifti:** derleyici sınanmadan gönderilirse sessiz yanlış
  doğduğu yerde kalır.

---

## 8. Bağımsız review — v3'ten fark

Yeni hattaki adım **BAĞIMSIZ REVIEW**. Bu, v3'teki "Claude bulur, İhsan triyaj
eder"den farklı: her fazın sonunda review'u **yapımı görmemiş** ayrı bir
inceleyici yapar (bağlamı temiz bir alt-ajan), çünkü kendi işini denetleyen bir
inceleyici kendi varsayımlarını denetleyemez.

Bulgu biçimi değişmiyor (iş hattı §6): `[BULGU-XX] dosya:satır — CONFIRMED / Ne /
Nasıl patlar / Öneri`. Triyaj sözlüğü değişmiyor: **BLOK · DÜZELT · SONRA ·
KABUL**, ve gerekçesiz KABUL yok.

---

## 9. Geri alma — faz düzeyinde

| Faz | Geri alma |
|---|---|
| 0 | `YURUTUCU_V2=0`; dal birleştirilmez |
| 1 | `ANLAM_KATMANI=0` → v3 serbest SQL yolu (SPEC B-4) |
| 2 | Sihirbaz atlanabilir; anlam modeli elle yazılmış bir dosyadan yüklenir |
| 3 | Cetveller ekle-only; eski 101 soruluk set hiç dokunulmadan durur |

Her İP kendi dalında (`ip-XX-kisa-ad`), tek PR, master'a yalnız Ship kararıyla.

---

## 10. Plan dışı — beklemez

- **BULGU-15:** admin parolasının döndürülmesi. Hash uzak depo geçmişinde;
  takipten çıkarmak geçmişi temizlemedi. İhsan'ın işi, beş dakika, v4'ü beklemez.
- **Qlik görüşme tarihi:** belliyse §7 devreye girer. Bilinmiyor varsayıldı.

---

## 11. Kapı 1

```
INTENT ✔   CLARIFY ✔   SPEC ✔   PLAN ◀ KAPI 1 — İhsan
   →  BUILD  →  BAĞIMSIZ REVIEW  →  [KAPI 2 — TRİYAJ]  →  TEST  →  VERIFY
   →  [KAPI 3 — SHIP]
```

**ONAY** / **DEĞİŞTİR: …** / **DUR**

Onay gelene kadar tek satır kod yazılmaz. Bekleme süresince yapılabilecek ve
kapı gerektirmeyen iş: belge, ölçüm hijyeni ve bu planın kendi gözden geçirmesi.
