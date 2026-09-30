# ADR-8 — Anlam katmanı: model SQL yazmaz, seçim yapar

**Durum:** ÖNERİLDİ (v4 SPEC K-5) · **Tarih:** 2026-08-28 · **Karar sahibi:** İhsan Arvas
**İlgili:** ADR-1 rev.2 · ADR-2 · ADR-3 · ADR-4 · G-11 · G-18 · B-7

---

## 1. Bağlam

v3'te akış: `soru → LLM → serbest SQL → doğrula → çalıştır`. LLM'nin hata yüzeyi
altı boyutlu: tablo seçimi, JOIN yolu, tarih kolonu, filtre, toplama fonksiyonu,
sözdizimi. Altısı da sessizce yanlış olabilir.

Üç ölçülmüş olgu bu kararı zorluyor:

1. **Doğruluk arttıkça sessizlik arttı.** llama3.2:3b'de yanlışların %63'ü
   sessizdi; qwen 7b'de %95; Gemini'de **%100** (0/101 red). Güçlü model
   sözdizim değil *anlam* hatası yapar; doğrulama katmanı anlam hatasını
   göremez, çünkü sorgu geçerlidir.
2. **Şemadan çıkarılamayan üç eksen var** (v4 SPEC §2): tane, olay tarihi,
   geçerlilik. Hiçbir model `iptal` kolonunun varlığından o satırların
   sayımdan çıkarılması gerektiğini bilemez — tahmin eder, tahmini sessizce
   yanlış çıkar.
3. **`guven.py`'nin yarısı kayıp bilginin arkeolojisi.** 760 satırın yaklaşık
   yarısı (`_agac`, `_sql_tablolari`, `_takma_ad_haritasi`, `_metin_sabitleri`,
   `_kolon_degerleri`, `_filtre_degerleri`) üretilen SQL'in AST'sinden yapıyı
   **geri türetmeye** harcanıyor. Oysa o yapı üretim anında zaten vardı; metne
   çevrilirken kayboldu ve şimdi tahminle geri kazanılmaya çalışılıyor.

## 2. Karar

**LLM bir `Secim` üretir; SQL, `Secim` + `AnlamModeli`'nden deterministik olarak
derlenir.** LLM'den SQL istenmez ve LLM'ye şema metni verilmez — yalnız anlam
modelinin sözlüğü (ölçü adları, boyut adları, onaylı değer sözlükleri, zaman
taneleri) verilir.

```
v3:  soru → LLM → SQL → doğrula → çalıştır
v4:  soru → LLM → Secim → DERLE → doğrula → çalıştır
                     ▲        ▲
          tek stokastik   tamamen deterministik,
             parça         LLM'siz test edilir
```

## 3. Sonuçlar

### Lehte

- **Derleyici garanti eder, hatırlatmaz.** Geçerlilik filtresi, doğru olay
  tarihi, doğru JOIN yolu, doğru toplama kuralı artık *unutulamaz* — istem
  disiplinine değil koda bağlıdır.
- **`guven.py` küçülür ve güçlenir.** AST arkeolojisi gereksizleşir; kalan
  kontroller `Secim` üzerinde çalışır, yani **beyan edilmiş niyeti** okur,
  çıkarılmış niyeti değil. B-7'nin işi kaybolmaz, zemini sağlamlaşır.
- **Cetvel Katman 1 LLM'siz ve saniyelik olur** (SPEC F-1): `Secim → SQL`
  altın çiftleri her PR'da koşar.
- **Taşınabilirlik bedava gelir.** Aynı soru → aynı `Secim`; yalnız derleyicinin
  ürettiği SQL lehçeye göre değişir (ADR-4 burada gerçekten iş görür).
- **Sağlayıcı değişimine dayanıklılık.** `Secim` şeması sabit; model değişince
  yalnız istem değişir, hat değişmez. BULGU-08'in (aynı model adı, iki gece
  arasında 7 soruluk oynama) etkisi daralır.

### Aleyhte

- **İfade gücü sınırı.** Anlam modelinde karşılığı olmayan soru cevaplanamaz.
  *Azaltma:* SPEC B-3 öneri döngüsü (model eksik ölçüyü adlandırır ve teklif
  eder) + SPEC B-4 serbest SQL kaçış kapısı.
- **Derleyici yeni bir sessiz yanlış doğum yeridir** — ve en kötüsü, oradaki
  yanlış *tutarlı* olur. *Azaltma:* 40 altın çift; tek olay tablosu sınırı
  (SPEC R-3); modülü İhsan yazar (rol dağılımı: güvenlik/doğruluk-kritik).
- **Bakım yükü:** anlam modeli yaşayan bir belge olur ve şema kaydıkça
  güncellenmesi gerekir (SPEC A-5).

## 4. Reddedilen seçenekler

| Seçenek | Neden reddedildi |
|---|---|
| Serbest SQL'i sertleştirmeye devam etmek | Ölçüldü: doğruluk arttıkça sessizlik arttı. Sertleştirme bu eğilimi tersine çevirmedi, hızlandırdı |
| Fine-tune (ADR-2) | ADR-2 rev.2'nin kendi gerekçesi: "yanlış cevap sayısını azaltır, görünmezliğini azaltmaz." Ayrıca taşınabilirlik problemine hiç dokunmaz |
| Şemayı zenginleştirip serbest SQL'de kalmak | Tane, geçerlilik ve olay tarihi şemada **yoktur**; zenginleştirme onları icat edemez, ancak bir insan söyleyebilir |
| Anlam modelini de LLM'ye kurdurmak, insana sormamak | Aynı sebep: üç eksen şemada yok. LLM'nin tahmini, insanın bilgisiyle aynı şey değil. LLM **önerir**, insan **onaylar** (SPEC A-2/A-3) |

## 5. Koda inecek yer

`app/cekirdek/secim.py` · `app/cekirdek/derleyici.py` · `app/cekirdek/portlar.py::Esleyici`
Karar `config.py`'de bir anahtarla temsil edilir: `ANLAM_KATMANI` (varsayılan açık).

> Kural (§7): ADR koda inmezse karar değildir.

## 6. Geri alma

`ANLAM_KATMANI=0` → sistem SPEC B-4'ün serbest SQL yoluna döner (v3 davranışı).
Pilot kurulumda sorun çıkarsa sürüm geri alınmadan kapatılabilir.
