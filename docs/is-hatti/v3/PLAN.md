# SorBI v3 — PLAN  ▸ KAPI 1: ONAYLANDI

**Sürüm:** taslak 1.0 · **Tarih:** 2026-08-11 · **Taban:** `ffe5db3`
**Dayanak:** `SPEC.md` · **Onay:** İhsan Arvas — ✅ **ONAY** (2026-08-11)

> KAPI 1 geçildi: 2026-08-11'de ONAY verildi, İP-01 ve İP-02 başlatıldı.
> Onay sırasında planın üç sorusu ayrıca cevaplanmadı; İP-02'deki README kararı
> önerilen biçimde uygulandı (QLoRA bölümü kaldırıldı, ADR-2 ile geri gelecek).
>
> **Düzeltme (2026-08-11, BULGU-04):** İP-01 Review'unda planın kendisinde bir boşluk
> bulundu — E-3 (test kapsamı) ve E-4 (yapısal loglama) gereksinimlerinin sahibi yoktu.
> **İP-15** eklendi (Faz 1 sonu) — **2026-08-16'da İP-03c ile kapandı.** Faz 4 bitip "v3 tamam" denince bu iki gereksinim
> sessizce yapılmamış kalacaktı.

---

## Sıralama mantığı

Üç ilke sıralamayı belirledi:

1. **Ölçüm önce gelir.** Neyin ne kadar iyi olduğunu bilmeden iyileştirme yapılmaz.
   Bu yüzden altyapı ve eval hattı ilk fazda.
2. **Kanıt, mimariden önce gelir.** FastAPI refaktörü değerli ama doğruluk kanıtı
   olmadan yapılırsa güzelleştirilmiş bir kanıtsızlık üretir.
3. **Kritik kod İhsan'ın klavyesinde.** Güvenlik kapıları hem hata maliyeti en yüksek
   hem öğrenme değeri en yüksek modüller — K-4 kararı gereği bunları sen yazıyorsun.

---

## Faz 0 — Zemin (1. hafta · ~5 saat)

*Amaç: ölçüm ve değişiklik yapılabilir bir depo. Buradaki hiçbir iş davranış değiştirmez.*

### İP-01 · Mühendislik altyapısı — **Claude yazar**
- `pyproject.toml`, ruff yapılandırması, bağımlılık kilit dosyası
- `.github/workflows/ci.yml`: lint → pytest → `--gold-only` eval → docker build
- Kapsam eşiği raporlaması (henüz zorlayıcı değil, yalnız görünür)

**Dokunulan:** yeni dosyalar + `requirements.txt`
**Bağımlılık:** yok · **Kabul:** E-1, E-2 · **Geri alma:** dal birleştirilmez
**Süre:** ~1 gün

### İP-02 · Belge-kod tutarlılığı — **Claude yazar, İhsan karar verir**
- README'nin QLoRA bölümü: `training/` ya eklenir ya bölüm çıkarılır
  → **Senin kararın gerekiyor** (öneri: şimdilik çıkar, A-2 ölçümü sonrası geri gelir)
- Maskeleme ve denetim izi iddiaları, B-1/B-5 yapılana kadar "planlanan" olarak işaretlenir
- `CHANGELOG.md` + geriye dönük sürüm girdileri + v2.3 tag'i

**Bağımlılık:** yok · **Kabul:** D-2, E-5 (kısmi) · **Süre:** ~yarım gün

> **Neden ilk fazda:** Bugün depoda, karşılığı olmayan güvenlik iddiaları duruyor.
> Bunlar düzeltilene kadar depo herkese açık. Bu bir itibar riski, teknik borç değil.

---

## Faz 1 — Kanıt (2.–4. hafta · ~15 saat)

*Amaç: G-11 ve G-12 için, o commit'te yeniden üretilebilir sayılar.*

### İP-03 · Eval hattını koşulabilir hale getir ve baseline'ı ölç — **Karışık**
1. **Varsayım doğrulaması (İhsan, ~yarım gün):** Ollama CPU backend'i ya da Docker/Linux
   ile ölçüm koşuyor mu? Sonuç `SPEC.md` §2'ye yazılır.
2. `eval/evaluate.py` refaktörü — `globals()` enjeksiyonu kalkar, generator enjekte edilir *(Claude)*
3. Baseline koşumu: hastane seti, yerel mod *(İhsan koşar — donanım sende)*
4. `docs/kanit/accuracy-<tarih>.md` ve `gecikme-<tarih>.md` *(Claude yazar)*

**Bağımlılık:** İP-01 · **Kabul:** A-1, A-2, A-3
**Karar noktası:** accuracy < %80 ise ADR-2 tetiklenir → **yeni İP açılır, plan revize edilir**
**Süre:** ~1 hafta

### İP-03b · Ucuz kazanç turu + ikinci ölçüm — **Karışık** *(2026-08-16 baseline'ı ile eklendi)*
Baseline %30 çıktı; başarısızlığın şekli QLoRA'dan önce üç ucuz düzeltmeye işaret ediyor.

1. **JOIN yolları belgesi** *(Claude — ✅ yapıldı)*: FK grafiğinden her tablo çifti için
   en kısa yol + alternatifi otomatik üretilir, yoldaki ara tabloların şeması da bağlama
   eklenir. 13 test, LLM gerektirmiyor.
2. **İstem sertleştirme** *(Claude — ✅ yapıldı)*: kolon adını harfi harfine koruma,
   JOIN yollarını kullanma, hesaplanan değeri kolon sanmama + iki few-shot örnek.
3. **Model ablasyonu** *(İhsan koşar)*: aynı test seti `llama3.2:3b` ve
   `qwen2.5-coder:7b-instruct` ile; sonuçlar `docs/kanit/` altında yan yana.
4. **İkinci ölçüm ve karar** *(birlikte)*: ADR-2 bu sayıyla değerlendirilir.

**Bağımlılık:** İP-03 · **Kabul:** A-6 · **Süre:** ~2 gün
**Karar noktası:** ikinci ölçüm hâlâ %60'ın altındaysa ADR-2 tetiklenir ve PLAN
yeniden onaya sunulur.

### İP-03c · B-7 sessiz yanlış azaltma — **BUILD/TEST/VERIFY BİTTİ** *(2026-08-16)*
- ✔ Ölçüm koşucusu sessiz yanlış oranını ayrı metrik olarak raporlar
- ✔ Modelin güven beyanından bağımsız sinyal — **9 LLM'siz kontrol** (`app/guven.py`)
- ✔ Emin olunmayan cevaplar arayüzde açıkça işaretlenir (uyarı sonucun ÜSTÜNDE)
- ✔ **Kontrolün kendisi ölçüldü** — yeni araç `eval/guven_olcum.py`

**Plandan sapma ve gerekçesi:** plan "çift üretim + sonuç karşılaştırma" ve
"SQL'i doğal dile geri çevirip soruyla kıyaslama" diyordu. İkisi de **yapılmadı**;
ikisi de üretimi ikiye katlıyor ve p95 zaten hedefin iki katı (21,2 sn / 10 sn).
Yerine belirlenimci, LLM'siz kontroller yazıldı: ek gecikme yok, test edilebilir,
yanıldıklarında nasıl yanıldıkları anlaşılıyor. Mutasyon karnesi bu yaklaşımın
yettiğini gösterdi (%82,9 yakalama / %1,0 yanlış alarm) — LLM'li yaklaşım ancak
bu taban tükenince gerekçelendirilebilir.

**Bağımlılık:** İP-03b · **Kabul:** B-7 · **Süre:** ~1 gün (tahmin: 1 hafta)
**Bekleyen:** İhsan'ın Review triyajı (8 madde) + Ollama'lı doğrulama koşumu

### İP-04 · Test setini genişlet — **Karışık**
- Hastane setine +30 soru *(Claude üretir, İhsan alan bilgisiyle düzeltir)*
- Satış şeması için 30 soruluk ikinci set *(Claude)*
- İkisi de `--gold-only` ile %100

**Bağımlılık:** İP-03 · **Kabul:** A-5 · **Süre:** ~3 gün

### İP-05 · Regresyon kapısı — **Claude yazar**
- CI'da accuracy eşiği; son ölçümden 3 puandan fazla düşüş = kırmızı
**Bağımlılık:** İP-03, İP-04 · **Kabul:** A-4 · **Süre:** ~yarım gün

### İP-15 · Yapısal loglama + kapsam eşiği — **Claude yazar** *(BULGU-04 ile eklendi)*
- `print` yerine `logging`; her sorunun bir korelasyon kimliği (E-4)
- `generator.py`'deki iki sessiz `except Exception: pass` görünür hale gelir
  → `pyproject.toml`'daki S110/B904 geçici istisnası **silinir**
- Test kapsamı eşiği zorlayıcı hale gelir; `audit` ve `schema_rag` için testler (E-3)

**Bağımlılık:** İP-03 · **Kabul:** E-3, E-4 · **Süre:** ~3 gün

---

## Faz 2 — Güvenlik kapıları (4.–8. hafta · ~25 saat)

*Amaç: belgelerin söylediğinin gerçekten yapılması. Bu fazın çoğunu sen yazıyorsun.*

### İP-06 · G-16 kolon maskelemesi — **İhsan yazar** · Claude: spec + test iskelesi + review
- `masked_columns` şema keşfiyle birleşir
- Üç etki noktası: bağlam işaretleme · SQL düzeyi politika (`RED` | `MASKELE`) · sonuç maskeleme
- API payload'ının veri içermediğini kanıtlayan anlık görüntü testi

**Bağımlılık:** İP-01 · **Kabul:** B-1 · **Süre:** ~1 hafta
**Geri alma:** `SORBI_MASKING=off` ile kapatılabilir

### İP-07 · G-14: her lehçede zaman aşımı + salt-okunurluk — **İhsan yazar**
- Postgres / MySQL / MSSQL / SQLite için gerçek zaman aşımı
- Oturum düzeyinde salt-okunur işlem
- Bağlantı testinde yazma denemesi → yazabiliyorsa kırmızı uyarı + denetim kaydı
- Test ortamı: Docker Compose ile Postgres + MySQL *(Claude hazırlar)*

**Bağımlılık:** İP-01 · **Kabul:** B-2, B-3 · **Süre:** ~1 hafta
**Not:** MSSQL doğrulanamazsa "doğrulanmadı" olarak açıkça işaretlenir (R-4)

### İP-08 · G-18 sertleştirme + kırmızı takım — **İhsan yazar** · Claude: saldırı seti
- Fonksiyon allowlist'i, sistem kataloğu politikası
- `tests/test_security_redteam.py` — 25+ kötü niyetli girdi *(Claude üretir, hepsi reddedilmeli)*

**Bağımlılık:** İP-07 · **Kabul:** B-4 · **Süre:** ~4 gün

### İP-09 · G-17 hash zinciri + kimlik sertleştirme — **Karışık**
- Denetim izi hash zinciri + `verify_chain()` + yönetici göstergesi *(İhsan)*
- Brute-force kilidi, oturum zaman aşımı, şifre sıfırlama *(Claude)*

**Bağımlılık:** İP-01 · **Kabul:** B-5, B-6 · **Süre:** ~4 gün

---

## Faz 3 — Mimari (8.–11. hafta · ~20 saat)

### İP-10 · Durum yalıtımı — **İhsan yazar** · Claude: eşzamanlılık testi
- Süreç genelindeki `config.DB_URL` mutasyonu ve `pipeline._index` tekili kaldırılır
- Bağlantı bir oturum bağlamı nesnesiyle taşınır; indeks bağlantı anahtarıyla önbelleklenir
- **Bu, bugünkü en ciddi işlevsel hatayı kapatıyor** (G-C: kullanıcılar arası veritabanı sızıntısı)

**Bağımlılık:** Faz 2 tamamlanmış olmalı (aynı dosyalara dokunuyor)
**Kabul:** C-1 · **Süre:** ~1 hafta
**Not:** Tek başına gönderilebilir; C-2 kayarsa bile bu gitmeli.

### İP-11 · FastAPI çekirdeği — **Claude yazar, İhsan review eder**
- `POST /ask` · `GET /schema` · `GET /audit` · `POST /connections/test` · `GET /health`
- Streamlit sayfaları API istemcisine dönüşür; içe aktarım denetimi testi
- OpenAPI şeması

**Bağımlılık:** İP-10 · **Kabul:** C-2 · **Süre:** ~1,5 hafta

### İP-12 · Docker Compose güncellemesi — **Claude yazar**
**Bağımlılık:** İP-11 · **Kabul:** C-3 · **Süre:** ~yarım gün

---

## Faz 4 — Ticari yapı ve kanıt dosyası (11.–12. hafta · ~10 saat)

### İP-13 · Çift lisans yapısı — **Karışık**
- Kısa hukuki gözden geçirme *(İhsan — R-5)*
- `LICENSE-ENTERPRISE.md`, `NOTICE`, CLA metni, özellik ayrım tablosu, README lisans bölümü *(Claude)*
- Kurumsal depo iskeleti

**Bağımlılık:** yok (paralel yürüyebilir) · **Kabul:** D-1 · **Süre:** ~3 gün

### İP-14 · Kanıt dosyası — **Claude yazar**
Tek bir pakette, satış görüşmesine sokulabilir hâlde:
- Doğruluk raporu (A-2) + gecikme raporu (A-3)
- Güvenlik kapı raporu: her G-kapısı, nasıl zorlandığı, hangi testin kanıtladığı
- Pilot kurulum kılavuzu + DBA'ya verilecek salt-okunur hesap reçetesi
- Bilinen kısıtlar listesi (dürüstlük bölümü — doğrulanamayanlar burada)

**Bağımlılık:** Faz 1 + Faz 2 · **Kabul:** E-5 · **Süre:** ~3 gün

---

## Bağımlılık haritası

```
İP-01 ─┬─ İP-02
       ├─ İP-03 ── İP-03b ─┬─ İP-03c
       │                    ├─ İP-04 ── İP-05
       │                    └─ İP-15
       ├─ İP-06 ─┐
       ├─ İP-07 ── İP-08 ─┤
       └─ İP-09 ─────────┴─ İP-10 ── İP-11 ── İP-12
İP-13 (paralel) ────────────────────────────────┐
İP-03,04,06,07,08,09 ───────────────────────────┴─ İP-14
```

---

## Efor ve takvim

| Faz | İP | Süre | Kim ağırlıklı |
|-----|-----|------|----------------|
| 0 — Zemin | 01, 02 | ~1,5 gün | Claude |
| 1 — Kanıt | 03, **03b**, **03c**, 04, 05, 15 | ~4 hafta | Karışık |
| 2 — Güvenlik | 06, 07, 08, 09 | ~3,5 hafta | İhsan |
| 3 — Mimari | 10, 11, 12 | ~3 hafta | Karışık |
| 4 — Ticari | 13, 14 | ~1 hafta | Karışık |

**Toplam:** ~13 hafta · haftada ~7 saat varsayımıyla.
Haftalık kapasiten farklıysa **DEĞİŞTİR** de, sıralamayı değil kapsamı budayalım —
kesilecek ilk şey Faz 3, kesilmeyecek şey Faz 1 ve 2.

---

## Bu planın kabul etmediği şeyler

- **Faz 2 önce, Faz 1 sonra olmaz.** Güvenlik kapılarını ölçüm hattı olmadan yaparsak,
  değişikliklerin doğruluğu bozup bozmadığını göremeyiz.
- **İP-11 (FastAPI), İP-10 (durum yalıtımı) olmadan yapılmaz.** Bugünkü global durumu
  HTTP arkasına koymak, tek kullanıcılı bir hatayı çok kullanıcılı bir hataya dönüştürür.
- **Hiçbir İP, testi yazılmadan Review'a gelmez.**

---

## Onay için üç soru

1. **Sıralama doğru mu?** Kanıt → güvenlik → mimari → ticari.
2. **Rol dağılımı doğru mu?** Faz 2'nin tamamı sende; yükü ağır bulursan İP-09'u bana verebilirim.
3. **İP-02'deki README kararı:** QLoRA bölümü şimdilik çıksın mı, yoksa `training/` klasörü
   gerçekten yazılsın mı?

**Onayınla İP-01 başlar.**
