# SorBI — çalışma belleği

Bu dosya her oturumda ilk okunan şeydir. Amacı: yeni bir oturum açıldığında
projenin nerede olduğunu, hangi kararların verildiğini ve **hangi hataların
zaten yapıldığını** tekrar keşfetmek zorunda kalmamak.

Kısa tut. Bir şey burada yazmıyorsa `docs/is-hatti/` altına bak.

---

## 1. Bu ne

Türkçe doğal dilden SQL üreten BI asistanı. Kullanıcı Türkçe soru sorar,
sistem SQL üretir, çalıştırır, sonucu ve **ürettiği SQL'i** gösterir.

Depo: `github.com/Arvas65/sorbi` · Yerel: `C:\Users\Arvas\SorBı`
Sahibi: İhsan Arvas. Hedef: ticari seviye.

## 2. Çalışma düzeni — üç kapı

`Intent → Clarify → Spec → Plan → Build → Review → Test → Verify → Ship`

Bu üçü **İhsan'ındır, asla atlanmaz:**

| Kapı | Ne demek |
|------|----------|
| **Plan** | Onayı alınmadan yeni iş paketi başlamaz |
| **Review** | Bulguları o triyaj eder |
| **Ship** | Yayına çıkma kararı onun |

Bunların dışındaki her şey (build, test, ölçüm, refactor, belge) onay
beklemeden yürür. İhsan yoksa iş durmaz; dönüşünde tek bir özet bulur.

Triyaj sözlüğü: **BLOK · DÜZELT · SONRA · KABUL**
KABUL yazılı gerekçe olmadan verilmez.

## 3. Değişmezler

Bunlar tartışmaya açık değil; birini bozan bir değişiklik geri alınır.

1. **Yalnız SELECT çalışır.** (G-18) Doğrulama katmanı istisna fırlatmaz,
   kapalı devre başarısız olur.
2. **Üretilen SQL her zaman gösterilir.** (G-02) Hata durumunda bile.
3. **Yerel mod varsayılandır**, veri makineden çıkmaz. API modunda dış servise
   yalnız ŞEMA METAVERİSİ gider (tablo/kolon adları, ilişkiler, JOIN yolları);
   gerçek kolon değerleri `generator.mask_context()` ile **koşulsuz** düşürülür.
   Bu bir ayara bağlı değildir ve bağlanamaz (G-13/G-16, bulgu 2026-08-22).
4. **Ölçülmemiş şey iddia edilmez.** Rapor yalnız çalıştırılmış sayıyı yazar.
5. **Kanıt dosyalarının üzerine yazılmaz.** Her koşum damgalı ve benzersiz.
6. **Hiçbir hata sessizce yutulmaz.** `except: pass` yasaktır — kendi
   ürünümüzde kovaladığımız sessiz yanlışın kod hâli budur.

## 4. Nerede ne var

| Yol | Ne |
|-----|-----|
| `app/guven.py` | B-7 sessiz yanlış kontrolleri (9 kontrol, LLM'siz) |
| `app/validator.py` | Güvenlik kapısı — asla fırlatmaz, kapalı devre |
| `app/schema_rag.py` | Şema keşfi, JOIN yolları, değer örnekleme |
| `eval/evaluate.py` | 101 soruluk ölçüm koşucusu |
| `eval/guven_olcum.py` | Güven kontrolünün mutasyon karnesi (LLM'siz) |
| `eval/tarih_sabitle.py` | Ölçüm referans günü (İP-23) |
| `gece-gorev/` | Tek seferlik gece görevleri — bir kez koşar, `bitti/`ye taşınır |
| `kontrol.bat` | İhsan'ın tek komutla koşturduğu denetim |
| `docs/is-hatti/` | İş hattı, SPEC, PLAN, BACKLOG, ADR'ler, İP kayıtları |
| `docs/kanit/` | Ölçüm çıktıları — **ekle-only, silinmez** |

## 5. Şu anki durum

**Ölçülen:** doğruluk %62,4 (63/101, GA %52,9–71,8) · p95 21,2 sn
**Hedefler:** G-11 ≥%80, G-12 ≤10 sn — **ikisi de karşılanmadı**

**Asıl sorun:** yanlış cevapların %95'i *sessiz* — temiz bir tablo dönüyor,
sayı yanlış. Doğruluk arttıkça bu oran da artıyor (güçlü model sözdizim değil
anlam hatası yapar). Güvenilirlik doğruluk artırılarak çözülmez.

**Buna karşı:** B-7 güven kontrolleri. **İki ayrı karne var, karıştırma:**

| Karne | Sayı | Ne demek |
|-------|------|----------|
| Mutasyon (bizim ürettiğimiz hatalar) | **%80,1** (245/306) | regresyon nöbetçisi |
| Gerçek model hataları (saha) | **%20** (6/30, GA %9,5–37,3) | sahada beklenen |

Aralıklar kesişmiyor; bu bir dalgalanma değil (BULGU-04, iki gecede %17 → %20).
Mutasyon karnesi bir **regresyon nöbetçisidir, saha tahmincisi değildir.**
Havuz 2026-08-23'te gerçek hata ailelerini de kapsayacak şekilde genişletildi
(239 → 306 mutant) ve sayı %83,3'ten düştü — düşüş bir gerileme değil, eski
sayının bir kısmının havuzun kolaylığından geldiğinin ölçülmesi.

Sahadaki bayraklar artık denetim izine yazılıyor (`audit.guven_karnesi()`),
yani saha karnesi bir daha tahmin edilmeyecek, sayılacak.

**Bekleyen:** Ship kapısı — ADR-5 (İP-32), karar bölümü boş.

## 6. Alınmış kararlar

- **ADR-1 rev.2** taban model `qwen2.5-coder:7b-instruct`. Ölçümle seçildi
  (McNemar p=2,8e-4), tahminle değil.
- **ADR-2 rev.2** QLoRA tetiklendi ama **ertelendi** — fine-tune yanlış cevap
  sayısını azaltır, görünmezliğini azaltmaz.
- **ADR-3** Chroma RAG · **ADR-4** sqlglot ile lehçe taşınabilirliği
- **ADR-5** çıkarım nerede koşacak (yerel / API) — **TASLAK, karar verilmedi.**
  Ship kapısıdır: API modunu kalıcı yapmak ADR-1'in "veri dışarı çıkmaz"
  reddini geri almak demektir.
- Lisans: çift — çekirdek açık, kurumsal katman kapalı
- Mimari: FastAPI çekirdek + Streamlit istemci, tam yeniden yazım yok
- Roller: güvenlik-kritik modülleri İhsan yazar, altyapıyı Claude

## 7. Bu projede zaten yapılmış hatalar

Tekrarlanmasın diye duruyorlar. Hepsi gerçekten oldu.

| Hata | Ders |
|------|------|
| Tek koşumu sinyal sanmak | Tek koşum gürültüdür |
| Binom SE ile eşli tasarımı test etmek | Aynı soru setinde **McNemar** |
| Kanıt dosyalarının üzerine yazmak | Damgalı benzersiz ad + ekle-only günlük |
| Kendi doğrulama katmanımızın accuracy'yi bastırdığını görmemek | Reddedilen sorguları **oku** |
| GPU'nun kullanılmadığını fark etmemek (2 saat) | `--doctor` her ölçümden önce |
| `except Exception: pass` yazmak | Kendi yasakladığımız kalıp |
| Referans günü sabit kodlamak | Sabit, yazıldığı makinenin verisine aittir |
| ADR'yi yazıp koda indirmemek | Karar `config.py`'de değilse karar değildir |
| Beklenen değeri betiğe gömmek | Sabit, yazıldığı ana ve makineye aittir. Ölçüleni **kendi geçmişiyle** karşılaştır |
| Kuralı skill'e yazıp koda yazmamak | `karsilastirilamaz()` belgelenen beş koşuldan ikisini denetliyordu |
| Gizlilik vaadini docstring'e yazmak | `generate_api` "veri değeri asla gitmez" diyordu; bunu sağlayan tek şey bir ayarın hatırlanmasıydı |
| Bağlı klasörde bulut oturumundan git yazmak | Montajda `rm` yasak; git kilidini **silemiyor**. Kalan `index.lock` gece koşumunu 5 gün sessizce durdurdu. Okuma için `--no-optional-locks`, yazdıysan kalıntıyı temizle |

Ortak paydaları: **bir yerde geçerli olanın başka yerde de geçerli olduğunu
varsaymak.** Çare hep aynı — varsayımı çalıştırılabilir bir kontrole çevir.

## 8. Komutlar

```
kur.bat                     paketi kur (yedek alır, kanıtı korur, otomatiği kurar)
kontrol.bat                 hızlı denetim (LLM'siz, ~1-2 dk)
kontrol.bat tam             + 101 soruluk ölçüm (Ollama, ~25-40 dk)
kontrol.bat tam /sessiz     aynısı, hiç tuşa basmadan (zamanlanmış koşum)
gemini-kur.bat              API modu: anahtarı sorar, kurar, gerçekten dener
gemini-kur.bat /kaldir      yerel moda dön
otomatik.bat /durum         gece koşumu ne zaman, ne oldu
otomatik.bat /simdi         gece koşumunu hemen bir kez çalıştır

python -m ruff check .
python -m pytest tests\ --cov=app --cov=eval
python eval\evaluate.py --doctor        ortam + GPU
python eval\evaluate.py --gold-only     LLM'siz bütünlük
python eval\guven_olcum.py              güven karnesi
```

## 9. İhsan komut yazmaz

Kural (2026-08-21): İhsan'dan komut yazmasını isteme. Ölçüm her gece 03:00'te
`gece-kosum.bat` ile kendiliğinden koşar ve sonucu `olcum-otomatik` dalına
iter; bulut nöbeti sabah o dalı okur.

Ondan bir şey istemek gerekiyorsa yalnızca üç kapıdan biri için iste:
**Plan onayı, Review triyajı, Ship kararı.** Başka bir şey için isteme —
çözümünü bul.

## 10. Paketleme kuralı

Paket **asla** `docs/kanit/` içeriği taşımaz (`.gitkeep` hariç). Kanıt, üretildiği
makineye aittir; paketle taşınırsa hedef makinenin kendi ölçüm geçmişini ezer.
Bir kez yapıldı: paket, paketleyenin `KARNE-GECMIS.log` dosyasını taşıyordu.

`kur.bat` buna ek olarak paketin içeriğine **güvenmez** — ne gelirse gelsin
`docs/kanit`'i açılan kopyadan temizler. Bu bilinçli bir çift koruma.

## 11. Oturum sonunda

Her oturum `docs/is-hatti/GUNLUK.md` dosyasının başına bir giriş ekler:
ne yapıldı, ne ölçüldü, ne açık kaldı. Bir sonraki oturum oradan devralır.
