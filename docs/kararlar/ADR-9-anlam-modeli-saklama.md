# ADR-9 — Anlam modelinin saklanması ve sürümlenmesi

**Durum:** ÖNERİLDİ (v4 SPEC K-2) · **Tarih:** 2026-08-28 · **Karar sahibi:** İhsan Arvas
**İlgili:** ADR-8 · G-13 · G-16 · BULGU-15 · BULGU-16 · SPEC A-5, F-5

---

## 1. Bağlam

Ürünün sözü: *veri hiçbir yere yazılmaz.* Ama anlam modeli bir kere kurulup her
oturumda yeniden kurulamaz — 20 tablolu bir HBYS'de bu, her açılışta yarım saat
demektir ve ürün kullanılamaz hâle gelir.

Çelişki görünürde. Sınır doğru çizilince kalkıyor:

> **Veri yazılmaz. Tanım yazılır.**

Anlam modeli veri değildir: tablo adları, kolon adları, ölçü ifadeleri, insan
onaylı değer sözlükleri. Hiçbir satır içermez.

## 2. Karar

Anlam modeli **müşterinin kendi makinesinde, depo içinde bir dosyada** tutulur:

```
anlam/
  <baglanti>.json            # yürürlükteki sürüm
  gecmis/
    <baglanti>-v1.json       # önceki sürümler, ekle-only
    <baglanti>-v2.json
```

Her onay sürüm numarasını bir artırır. Her ölçüm damgası yürürlükteki sürümü
taşır (SPEC F-5).

### 2a. Neden `.sorbi/` değil — SPEC A-5'in düzeltmesi

v4 SPEC taslak 1.0 yolu `.sorbi/anlam-<baglanti>.json` olarak yazdı. **Bu yanlış
ve burada düzeltiliyor.**

`.sorbi/` bu depoda **sır dizinidir**: `users.json` (admin salt+hash) ve
`connections.json` oradaydı, BULGU-15 ile takipten çıkarıldı ve dizin
`.gitignore`'a alındı. Anlam modelini oraya koymak, onu **kalıcı olarak
sürümlenemez** yapardı — oysa bu belgenin lehine sayılan başlıca özellik
git'lenebilir, gözden geçirilebilir olmasıydı.

İki farklı varlık, iki farklı dizin:

| Dizin | Ne | Depoda |
|---|---|---|
| `.sorbi/` | sırlar: kimlik bilgileri, bağlantı dizeleri | **hayır** (`.gitignore`) |
| `anlam/` | anlam modeli: tanımlar, onaylı sözlükler | **evet**, kasten izlenir |

## 3. Sonuçlar

### Lehte
- **Salt-okunurluk bozulmaz.** Müşterinin veritabanına hiçbir şey yazılmaz.
- **Model müşterinin malı olur.** Git'lenebilir, gözden geçirilebilir, PR'a
  konabilir. Ticari olarak da doğru yer: müşteri onu bırakamaz — ve o belge
  kullanıldıkça zenginleşir (ADR-8 §3, öneri döngüsü).
- **Ölçüm karşılaştırılabilirliği korunur.** Farklı model sürümleriyle alınmış
  iki koşum `karsilastirilamaz()` tarafından reddedilir (SPEC F-5) — İP-23
  cetvel çürümesi dersinin anlam katmanına uygulanmış hâli.
- **Şema kayması izlenebilir.** Kaynak şema değişince fark hesaplanır ve
  sihirbaz yalnız farkı sorar (SPEC A-5).

### Aleyhte
- Model dosyası elle düzenlenebilir; bozuk bir dosya sessiz yanlış üretebilir.
  *Azaltma:* `dogrula()` her yüklemede koşar ve bozuk modeli **reddeder**
  (kapalı devre), yüklemez.
- Çok kullanıcılı kurulumda dosyanın sahibi belirsizleşir.
  *Azaltma:* v4 tek kurulum varsayar; çok kiracılılık kurumsal katmanda ve o
  zaman bu ADR yeniden açılır.

## 4. Reddedilen seçenekler

| Seçenek | Neden reddedildi |
|---|---|
| Bağlanılan veritabanının içinde ayrı şema | Yazma yetkisi ister. Ürünün ana vaadini (salt-okunur) doğrudan bozar |
| Hiçbir yerde — her oturum baştan etiketleme | 20 tablolu bir kurulumda ürünü kullanılamaz kılar |
| Merkezî bulut deposu | Veri değil ama **şema metaverisi**; v3 SPEC G-F bunu bazı kurumlar için hassas olarak kaydetti. Ayrıca on-prem vaadiyle çelişir |
| `.sorbi/` altında | O dizin sırlar için ve `.gitignore`'da; anlam modeli sürümlenebilir olmalı (§2a) |

## 5. Koda inecek yer

`app/cekirdek/anlam.py` (model + `dogrula`) · `app/baglanti/anlam_deposu.py`
(`DosyaAnlamDeposu`) · `config.py::ANLAM_DIZINI` (varsayılan `anlam/`)
`.gitignore`: `anlam/` **eklenmez** — kasten izlenir.

## 6. Geri alma

Dosya yolu yapılandırmadan okunur; başka bir depo (ör. ileride bir veritabanı)
`AnlamDeposu` portunu uygulayarak devralabilir — çağıran kod değişmez (ADR-8'in
port tasarımı, SOLID/DIP).
