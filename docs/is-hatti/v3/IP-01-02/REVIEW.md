# İP-01/02 — REVIEW  ▸ KAPI 2: TRİYAJ YAPILDI (BULGU-06 açık)

**Tarih:** 2026-08-11 · **Taban:** `ffe5db3` · **İnceleyen:** Claude
**Triyaj:** İhsan Arvas — 2026-08-11, "hadi devam edelim"

Triyaj sözlüğü (`00-IS-HATTI.md` § 6): **BLOK** · **DÜZELT** · **SONRA** · **KABUL**
Gerekçesiz KABUL yoktur.

---

## Bulgular

### [BULGU-01] `pyproject.toml:per-file-ignores` — CONFIRMED
**Ne:** İP-01, 12 gerçek lint bulgusunu düzeltmek yerine `per-file-ignores` ile susturdu.
**Nasıl patlar:** Susturulmuş bir kural, kapatılmış bir bulguya benzer. Altı ay sonra bu
dosyaya bakan biri "bunlar kabul edilmiş kalıplar" diye okur ve İP-15/16 hiç yapılmaz.
**Bugün alınan önlem:** İstisna bloğu "GEÇİCİ İSTİSNALAR" başlığı, tarih, İP numarası ve
"bunlar susturulmuş HATALARDIR" cümlesiyle yazıldı; her biri BACKLOG'a düştü.
**Öneri:** Bu tasarımı kabul et — alternatifi ya kapsam kayması (Faz 2 işini İP-01'de yapmak)
ya da ilk günden kırmızı bir CI'dır.
**Önerilen etiket:** KABUL (gerekçesi yukarıda)

### [BULGU-02] `app/generator.py:110,136` — CONFIRMED
**Ne:** API çağrısı başarısız olduğunda hata sessizce yutuluyor (`except Exception: pass`)
ve yerel moda düşülüyor.
**Nasıl patlar:** Bir pilotta API anahtarı yanlış girilmiş olsun. Sistem sessizce yerel
modelle çalışmaya devam eder; kullanıcı "api" beklerken "local" etiketi görür ama **neden**
düştüğünü ne kullanıcı ne de sen görebilirsin. Saha teşhisi imkânsız hale gelir.
**Öneri:** Yapısal loglama ile `logger.warning("API modu başarısız: %s — yerele düşülüyor", e)`.
**Önerilen etiket:** SONRA → İP-15

### [BULGU-03] `ui/pages/1_Dashboard.py`, `ui/streamlit_app.py` (5 nokta) — CONFIRMED
**Ne:** Tablo adları f-string ile SQL'e gömülüyor: `f'SELECT COUNT(*) FROM "{_t}"'`.
**Nasıl patlar:** Bugün istismar edilemez — `_t` şema keşfinden gelir, kullanıcıdan değil.
Ancak v2.2 ile kullanıcı artık **kendi veritabanını bağlıyor**; tablo adı artık senin
kontrolündeki bir sabit değil, dışarıdan gelen bir dize. Tırnak içeren bir tablo adı
(PostgreSQL'de yasal) sorguyu kırar; kötü niyetli bir şema adı daha fazlasını yapar.
Ayrıca ürünün kendi ilkesi (validator katmanı) tam olarak bu kalıbı yasaklıyor.
**Öneri:** Tanımlayıcıları sqlglot ile alıntıla.
**Önerilen etiket:** SONRA → İP-16

### [BULGU-04] v3 PLAN'ında sahipsiz gereksinimler — CONFIRMED
**Ne:** SPEC'te E-3 (test kapsamı) ve E-4 (yapısal loglama) gereksinimleri var; PLAN'daki
14 iş paketinin hiçbiri bunları üstlenmiyor.
**Nasıl patlar:** Faz 4 biter, "v3 tamam" denir, iki gereksinim hiç yapılmamış olur —
üstelik kimse fark etmez çünkü SPEC'te yazılı olmaları onları yapılmış gibi hissettirir.
**Not:** Bu, kodda değil **planın kendisinde** bir hata. Hattın Review adımının kendi
planını da denetlemesi gerektiğinin kanıtı.
**Öneri:** İP-15 açıldı ve BACKLOG'a YÜKSEK öncelikle yazıldı; PLAN'a eklenmeli.
**Önerilen etiket:** DÜZELT (PLAN belgesinde, kodda değil)

### [BULGU-05] `pandas<3` sınırı — CONFIRMED
**Ne:** Kilit oluşturulurken en yeni çözümleme pandas 3.0.5 getiriyordu; dashboard kodunun
pandas 3.x ile uyumu denenmediği için sınır `<3` olarak konuldu.
**Nasıl patlar:** Patlamaz — bu bir güvenlik önlemi. Ancak sınır kaydedilmezse ileride
"neden eski pandas'tayız" sorusunun cevabı kaybolur.
**Öneri:** Kod içinde gerekçe yazıldı (`core.in`, `pyproject.toml`), BACKLOG'a düştü.
**Önerilen etiket:** KABUL → İP-18'de tekrar bakılacak

### [BULGU-06] Docker imajı doğrulanmadı — CONFIRMED
**Ne:** Dockerfile pinlenmiş kilit dosyalarını kullanacak şekilde değiştirildi ama bu ortamda
docker daemon olmadığı için imaj derlenemedi.
**Nasıl patlar:** `COPY requirements/ ./requirements/` satırı yanlışsa imaj derlemesi kırılır
ve bunu ilk öğrenen kişi pilot kurulumu yapan olur.
**Öneri:** CI'ın `docker` işi ilk itişte bunu koşacak. **İlk CI koşumu yeşil olana kadar
Ship kararı verilmemeli.**
**Önerilen etiket:** BLOK (ilk CI koşumuna kadar)

### [BULGU-07] README'nin yeni güvenlik tablosu — CONFIRMED (olumlu bulgu, kayıt için)
**Ne:** README'deki "Güvenlik varsayılanları (pazarlık edilemez)" bölümü, "Güvenlik: tasarım
hedefi ve bugünkü durum" başlıklı iki sütunlu bir tabloyla değiştirildi. Artık her kapının
hedefi ve gerçek durumu ayrı ayrı yazıyor.
**Neden bir bulgu:** Bu, deponun **pazarlama gücünü bilinçli olarak azaltan** bir değişiklik.
Bunu senin görmeden birleştirmem doğru olmaz — açık bir depoda "Uygulanmadı" yazmak
stratejik bir karardır, teknik değil.
**Öneri:** Kabul et. Bir hastane satın alma komitesi bu tabloyu gördüğünde güven duyar;
tam tersi bir tablo bulup yakaladığında ise proje biter.
**Önerilen etiket:** senin kararın

---

## İnceleme kapsamı dışında bırakılanlar

- `app/` içindeki iş mantığı gözden geçirilmedi — İP-01/02 ona dokunmuyor.
  Güvenlik bulguları zaten v3 SPEC § 3'te kayıtlı.
- Streamlit sayfalarının işlevsel doğruluğu elle denenmedi.

---

## Triyaj tablosu

> **Triyajın niteliği:** İhsan "devam edelim" diyerek önerilen etiketleri onayladı.
> Bulgu bazında ayrı ayrı yazılı karar vermedi; aşağıdaki tablo bu nedenle
> **önerilerin kabulü** olarak kaydedilmiştir. Bir satıra itirazı varsa değiştirir.

| Bulgu | Etiket | Gerekçe / durum |
|-------|--------|-----------------|
| BULGU-01 | **KABUL** | Alternatifi kapsam kayması ya da ilk günden kırmızı CI. İstisnalar tarihli, İP numaralı ve "susturulmuş HATA" ibaresiyle yazıldı. **Vaadin ilk sınavı geçildi:** İP-03/A-1 tamamlanınca F821 istisnası `pyproject.toml`'dan gerçekten silindi. |
| BULGU-02 | **SONRA** → İP-15 | Backlog'a YÜKSEK öncelikle yazıldı. |
| BULGU-03 | **SONRA** → İP-16 | Backlog'a ORTA öncelikle yazıldı. |
| BULGU-04 | **DÜZELT** | ✅ Kapatıldı: İP-15 PLAN'a Faz 1'in sonuna eklendi, E-3 ve E-4 artık sahipli. |
| BULGU-05 | **KABUL** | Gerekçe `requirements/core.in` ve `pyproject.toml` içinde kodda yazılı; İP-18'de tekrar bakılacak. |
| BULGU-06 | **BLOK** — *açık* | Kapanmadı ve kapanamaz: docker daemon bu ortamda yok. İlk CI koşumu yeşile dönene kadar `v2.4.0` tag'i atılmaz. Bu, karar değil teknik bir engel. |
| BULGU-07 | **KABUL** | README'nin iki sütunlu güvenlik tablosu kalıyor. |

**Sonuç:** BLOK ve DÜZELT etiketlilerden DÜZELT kapatıldı, BLOK açık.
KAPI 2 **koşullu geçildi** — Build devam edebilir, Ship BULGU-06'ya bağlı.
