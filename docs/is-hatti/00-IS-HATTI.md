# SorBI — İş Hattı Operasyon Modeli

**Sürüm:** 1.0 · **Tarih:** 2026-08-11 · **Karar sahibi:** İhsan Arvas

Bu belge, SorBI'de bundan sonra yapılacak **her işin** izleyeceği yolu tanımlar.
Kural basit: hiçbir kod, bir SPEC'e ve onaylanmış bir PLAN'a bağlanmadan yazılmaz;
hiçbir sürüm, REVIEW triyajı ve VERIFY raporu olmadan çıkmaz.

---

## 0. Temel birim: İş Paketi (İP)

İş hattından akan şey "proje" değil, **iş paketi**dir. Bir İP:

- tek bir amaca hizmet eder (ör. "G-16 kolon maskelemesini gerçekten uygula"),
- tek bir dalda yaşar: `ip-XX-kisa-ad`,
- tek bir PR ile birleşir,
- tek bir Ship kararına konu olur.

Bir İP iki haftadan uzun sürüyorsa yanlış bölünmüştür — parçala.

**Artefakt yeri:** `docs/is-hatti/IP-XX-kisa-ad/` klasörü altında
`SPEC.md`, `PLAN.md`, `REVIEW.md`, `TEST.md`, `VERIFY.md`, `SHIP.md`.
Bu klasör depoda kalır; projenin hafızası budur, sohbet geçmişi değil.

---

## 1. Dokuz adım

| # | Adım | Kim yürütür | Çıktı artefaktı | Kapı |
|---|------|-------------|-----------------|------|
| 1 | **Intent** | İhsan | `SPEC.md` § Amaç | — |
| 2 | **Clarify** | Claude sorar, İhsan cevaplar | `SPEC.md` § Kararlar | — |
| 3 | **Spec** | Claude yazar, İhsan düzeltir | `SPEC.md` | — |
| 4 | **Plan** | Claude yazar | `PLAN.md` | **KAPI 1 — İhsan onayı** |
| 5 | **Build** | Rol dağılımına göre | Kod + commit'ler | — |
| 6 | **Review** | Claude bulur, İhsan triyaj eder | `REVIEW.md` | **KAPI 2 — İhsan triyajı** |
| 7 | **Test** | Claude | `TEST.md` + CI yeşil | — |
| 8 | **Verify** | Claude | `VERIFY.md` | — |
| 9 | **Ship** | Claude hazırlar | `SHIP.md` + git tag | **KAPI 3 — İhsan kararı** |

---

## 2. Adım adım: amaç, girdi, çıktı, tamamlanma tanımı

### 1 — Intent
**Amaç:** Ne istendiğini, *neden* istendiğini ve başarının nasıl görüneceğini tek paragrafta sabitlemek.

**DoD:** Aşağıdaki üç cümle yazılabiliyor:
- "Bugün şu sorun var: …"
- "Bu İP bittiğinde şu mümkün olacak: …"
- "Bunu şuradan anlayacağız: …" (gözlemlenebilir bir olgu; "daha iyi olacak" geçmez)

**Tuzak:** Çözümü intent sanmak. "FastAPI ekleyelim" bir intent değil, bir çözümdür.
Intent: "Pipeline'ı UI dışından da çağırabilmek istiyorum, çünkü entegrasyon satamıyorum."

---

### 2 — Clarify
**Amaç:** Spec'i yazmadan önce, cevabı spec'i değiştirecek soruları sormak.

**Kural:** Claude yalnız **kararı değiştiren** soruları sorar. Cevabı ne olursa olsun
aynı şeyi yapacaksa sormaz, varsayar ve varsayımı SPEC'e yazar.

**DoD:** Açık soru kalmadı ya da kalan her açık soru SPEC'te *"Varsayım (doğrulanacak): …"*
olarak yazıldı ve bir sahibi var.

---

### 3 — Spec
**Amaç:** Ne yapılacağını, ne yapılmayacağını ve neyin "bitti" sayılacağını yazmak.

**Zorunlu bölümler:**
1. Amaç (Intent'ten)
2. Kararlar (Clarify'dan)
3. Kapsam — numaralı gereksinimler, her birinin **kabul kriteri** var
4. **Kapsam dışı** — bilinçli olarak yapılmayacaklar ve gerekçesi
5. Etkilenen G-kapıları (G-01..G-20) ve ADR'ler
6. Riskler ve geri alma yolu

**Kabul kriteri kuralı:** Her kriter ya bir testle ya da bir ölçümle doğrulanabilir olmalı.
- Kötü: "Maskeleme çalışmalı."
- İyi: "`masked_columns` içindeki bir kolonu isteyen soru için sonuç tablosunda ham değer
  bulunmaz; API moduna giden HTTP gövdesinde hiçbir veri satırı geçmez —
  `tests/test_masking.py::test_api_payload_has_no_data` bunu doğrular."

**DoD:** Her gereksinimin kabul kriteri var; kapsam dışı bölümü boş değil.

---

### 4 — Plan  ▸ **KAPI 1**
**Amaç:** Spec'i sıralı, bağımlılıkları belli, kim yazacağı belli adımlara bölmek.

**Zorunlu içerik:** adım listesi · her adımın bağımlılığı · her adımın yazarı (İhsan / Claude) ·
dokunulacak dosyalar · geri alma yolu · tahmini süre.

**KAPI 1 — İhsan onayı.** Onay gelmeden tek satır kod yazılmaz.
İhsan üç şeyden birini der:
- **ONAY** → Build başlar
- **DEĞİŞTİR: …** → Plan revize edilir, tekrar sunulur
- **DUR** → İP rafa kalkar, gerekçe `PLAN.md` sonuna yazılır

---

### 5 — Build
**Amaç:** Planı koda çevirmek.

**Rol dağılımı (bu proje için karar):** *karışık*.
- **İhsan yazar:** güvenlik kapıları, doğrulama katmanı, durum yalıtımı — öğrenme değeri yüksek,
  hata maliyeti yüksek modüller.
- **Claude yazar:** altyapı, CI, test iskelesi, tekrarlı refaktör, belge.
- Hangi adımı kimin yazacağı **PLAN'da adım adım yazılır**; Build sırasında değiştirilmez.

**Kurallar:**
- Küçük commit, Türkçe ve emir kipinde mesaj.
- Spec'te olmayan iş yapılmaz. İhtiyaç çıkarsa Build durur, Spec'e döner (kapsam kayması yasak).
- Kod yazılırken test de yazılır; "sonra eklerim" kabul edilmez.

**DoD:** Plandaki tüm adımlar bitti, dal derleniyor, yerel testler geçiyor.

---

### 6 — Review  ▸ **KAPI 2**
**Amaç:** Kodu, spec'e ve gerçekliğe karşı denetlemek. Bu bir "beğendim/beğenmedim" adımı değil,
**bulgu üretme** adımıdır.

**Claude'un ürettiği her bulgu şu formatta olur:**

```
[BULGU-03] app/executor.py:529 — CONFIRMED
Ne: Postgres bağlantısında statement_timeout ayarlanmıyor.
Nasıl patlar: 5 dakikalık bir GROUP BY, 30 sn limitine rağmen sunucuda çalışmaya devam eder;
              G-14 sözü sunucu DB'lerinde geçersiz.
Öneri: connect_args ile options='-c statement_timeout=30000'
```

**Triyaj sözlüğü — karar İhsan'ın:**

| Etiket | Anlamı |
|--------|--------|
| **BLOK** | Ship'i engeller. Bu İP'te düzeltilmeden gidilmez. |
| **DÜZELT** | Bu İP'te düzeltilir ama ship'i tek başına engellemez. |
| **SONRA** | Backlog'a yazılır, İP numarası verilir. |
| **KABUL** | Bilinçli olarak kabul edilir — **gerekçe yazmak zorunlu.** |

Gerekçesiz KABUL yoktur. Altı ay sonra "bunu neden böyle bıraktık" sorusunun cevabı
`REVIEW.md` dosyasında durur.

**DoD:** Her bulgunun bir etiketi var; BLOK ve DÜZELT etiketlileri kapatıldı.

---

### 7 — Test
**Amaç:** Kodun, spec'in söylediğini yaptığını göstermek.

**Katmanlar:**
1. **Birim** — saf fonksiyonlar: preprocess, validator, auth, connections URL üretimi
2. **Entegrasyon** — pipeline uçtan uca, LLM sahte (mock) ile; gerçek LLM olmadan koşar
3. **Kırmızı takım** — `tests/test_security_redteam.py`: kötü niyetli girdiler, hepsi reddedilmeli
4. **Eval** — `eval/evaluate.py`: execution accuracy + gecikme

**DoD:** CI yeşil · kapsam eşiğinin altına düşmedi · yeni davranışın testi var ·
eval regresyonu yok (accuracy son ölçümden 3 puandan fazla düşmedi).

---

### 8 — Verify
**Amaç:** Test'ten farklıdır ve karıştırılmamalıdır.
**Test** sorar: *kod, spec'in dediğini yapıyor mu?*
**Verify** sorar: *spec'in ve belgelerin iddiası gerçekte doğru mu?*

Bu adım tam olarak bugün bulduğumuz sınıftaki hataları yakalamak içindir:
README'nin var olmayan bir `training/` klasörünü anlatması; "maskelenir" yazan bir belgenin
altında maskelemeyen bir kod olması.

**Verify kontrol listesi:**
- [ ] README ve `docs/` içindeki her iddia, gösterdiği dosyaya karşı kontrol edildi
- [ ] Belgede adı geçen her komut gerçekten koşturuldu
- [ ] Ölçüm iddiaları (accuracy, gecikme) bu commit'te yeniden üretildi; sayı, tarih,
      model adı ve commit hash'i `VERIFY.md`'ye yazıldı
- [ ] Güvenlik kapıları **canlı** doğrulandı: gerçek bir Postgres'e yazma denemesi reddedildi mi,
      uzun sorgu 30 sn'de iptal edildi mi
- [ ] Kapsam dışı bırakılanlar hâlâ kapsam dışı (sessizce sızmadı)

**DoD:** `VERIFY.md` dosyasında her satırın yanında ✔ ve dayanağı var. Dayanaksız ✔ yoktur.

---

### 9 — Ship  ▸ **KAPI 3**
**Amaç:** Sürümü çıkarmak.

**Claude hazırlar:** sürüm numarası önerisi (SemVer) · CHANGELOG girdisi ·
göç/kurulum notu · geri alma komutu · bilinen kısıtlar listesi.

**KAPI 3 — İhsan kararı:**
- **ÇIKAR** → tag atılır, CHANGELOG işlenir, sürüm yayınlanır
- **BEKLET: …** → gerekçe `SHIP.md`'ye yazılır, tetikleyici koşul belirtilir
- **GERİ AL** → dal birleştirilmez, öğrenilenler backlog'a yazılır

**DoD:** Tag var · CHANGELOG güncel · `VERIFY.md` sürümle birlikte depoda ·
geri alma komutu denendi ve çalışıyor.

---

## 3. Kapıların özeti

```
Intent → Clarify → Spec → [KAPI 1: PLAN onayı — İhsan]
                            ↓
                          Build
                            ↓
                        [KAPI 2: REVIEW triyajı — İhsan]
                            ↓
                       Test → Verify
                            ↓
                        [KAPI 3: SHIP kararı — İhsan]
```

Kapılar arasında Claude özerk çalışır ve rapor eder. Kapılarda durur ve bekler.
**Bir kapıyı Claude kendi başına geçemez** — geçtiyse bu bir süreç ihlalidir ve
`REVIEW.md`'ye bulgu olarak yazılır.

---

## 4. Geri dönüş kuralları

Hat tek yönlü değildir. Geri dönüş, başarısızlık değil, hattın çalıştığının işaretidir.

| Nerede | Ne olursa | Nereye döner |
|--------|-----------|--------------|
| Build | Spec'te olmayan ihtiyaç çıktı | **Spec** |
| Build | Plan yanlış sıralanmış | **Plan** (yeniden onay gerekir) |
| Review | BLOK bulgu | **Build** |
| Test | Kabul kriteri karşılanmıyor | **Build** |
| Verify | Belge iddiası yanlış | **Spec** ya da belge düzeltmesi |
| Ship | İhsan BEKLET dedi | Tetikleyici koşula kadar rafta |

---

## 5. Backlog

Tek dosya: `docs/is-hatti/BACKLOG.md`. Her satır:
`İP-XX · başlık · kaynak (hangi REVIEW/VERIFY'dan geldi) · öncelik (BLOK/YÜKSEK/ORTA/DÜŞÜK)`.

SONRA etiketli her Review bulgusu buraya düşer. Buraya düşmeyen bulgu kaybolmuş sayılır.

---

## 6. Bu hattın kendisi de bir artefakttır

Üç İP sonunda bu belge gözden geçirilir: hangi kapı işe yaradı, hangisi tören oldu.
Tören olan kapı kaldırılır. Sürüm numarası artırılır.
