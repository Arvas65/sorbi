# İP-03 — Devir Notu: baseline ölçümü senin makinende

**Tarih:** 2026-08-11 · **Durum:** A-1 tamamlandı · A-2 ve A-3 sende

---

## Neden bu ölçüm burada koşulamadı

Bulut kabının ağ izin listesi kapalı. Denenen ve sonuç:

| Kaynak | Sonuç |
|--------|-------|
| `ollama.com` (kurulum scripti) | **HTTP 403** — engelli |
| `huggingface.co` (GGUF ağırlıkları) | **Bağlantı kurulamadı** |
| `pypi.org`, `registry.npmjs.org` | Erişilebilir (kod bağımlılıkları sorunsuz) |

Yani hiçbir model ağırlığı bu ortama indirilemiyor. Ölçüm zorunlu olarak senin
donanımında koşacak — zaten PLAN'da da öyle yazıyordu (İP-03 adım 3).

**Ölçümü sahte bir modelle koşup "baseline" diye yayınlamak seçenek değildi.**
Farklı bir model ya da çalışma zamanıyla alınan sayı, ürünün gerçek sayısı olmaz;
`docs/kanit/` klasörünün tüm değeri, oradaki rakamın ne olduğunun tam olarak
bilinmesinde.

---

## Sende ne kaldı: dört komut

```bat
cd C:\Users\Arvas\SorBı

:: 0) Sanal ortamı ETKİNLEŞTİR — atlanırsa sistem Python'u kullanılır ve
::    'ModuleNotFoundError: sqlalchemy' alınır. (Saha kaydı: 2026-08-16)
.venv\Scripts\activate
:: Komut isteminin başında (.venv) görmelisin.
:: Paketler eksikse:  pip install -r requirements\core.txt

:: 1) Ortam hazır mı?  (~10 saniye)
python eval\evaluate.py --doctor
```

Bu komut sırayla şunları yapar: Ollama'ya bağlanır → `llama3.2:3b` yüklü mü bakar →
**gerçek bir üretim denemesi koşar**. Windows/Vulkan çökmesi (0xe06d7363) tam olarak
bu üçüncü adımda ortaya çıkar ve komut sana ne yazacağını satır satır söyler:

```
PowerShell:  $env:OLLAMA_LLM_LIBRARY='cpu_avx2'; ollama serve
cmd:         set OLLAMA_LLM_LIBRARY=cpu_avx2 && ollama serve
```

CPU'da da olmuyorsa daha küçük bir modele düşme talimatı da çıktının içinde.

```bat
:: 2) Hızlı deneme — 5 soru, ölçümün gerçekten yürüdüğünü görmek için (~1-2 dakika)
python eval\evaluate.py --db demo\hospital.db --limit 5

:: 3) Tam ölçüm — 50 soru
python eval\evaluate.py --db demo\hospital.db
```

Tam ölçüm bittiğinde üç dosya üretir:

- `eval/results.json` — soru bazlı ham kayıt
- `docs/kanit/accuracy-<tarih>.md` — **G-11 sayısı**, zorluk ve JOIN kırılımı,
  hangi aşamada kaybedildiği, ve ölçüm damgası (commit + model + platform)
- `docs/kanit/gecikme-<tarih>.md` — **G-12 sayısı**: p50, p95, en yavaş 5 soru

Bu iki markdown dosyasını commit'le. v3 SPEC A-2 ve A-3'ün kabul kriteri tam olarak
bunların varlığıdır.

---

## Sonuç ne çıkarsa ne olacak

| Accuracy | Ne anlama gelir | Sonraki adım |
|----------|-----------------|--------------|
| **≥ %80** | RAG-only mimari hedefi karşılıyor | QLoRA kapalı kalır. İP-04 (test setini genişlet) ile devam. Kanıt dosyasına ilk gerçek sayı girer. |
| **%60–80** | Mimari çalışıyor ama yetmiyor | Önce ucuz kazançlar: istem iyileştirme, RAG top-k ayarı, terim sözlüğü genişletme. Bunlar bitmeden QLoRA'ya geçmek pahalı bir tahmindir. |
| **< %60** | Taban model bu iş için küçük | **ADR-2 tetiklenir.** QLoRA yeni bir İP olarak açılır; PLAN revize edilir ve yeniden onayına sunulur. |

Rapor bu kararı senin yerine vermiyor ama %80'in altında kalındığında ADR-2 uyarısını
dosyanın içine kendisi yazıyor — altı ay sonra o dosyaya bakan kişi kararın neye
bağlı olduğunu görsün diye.

**Düşük bir sayı bu turun başarısızlığı değildir.** Bugün elimizde hiçbir sayı yok;
kötü bir sayı bile ondan iyidir, çünkü üzerine karar kurulabilir.

---

## Bu İP'te bitenler (Claude tarafı — A-1)

- `eval/evaluate.py`: `globals()["generator"]` enjeksiyonu kaldırıldı; üretici artık
  `run_one(..., gen_mod)` ile dışarıdan veriliyor
- Gecikme ölçümü hattın içine girdi — süre artık **her** yolda kaydediliyor
  (önceden yalnız başarılı sorularda yazılıyordu, yani G-12 ölçümü baştan eksikti)
- `ozetle()`: accuracy, p50, p95, en yavaş 5, onarım sayısı, **aşama dağılımı**
  (hangi adımda kaybediyoruz)
- `rapor_yaz()`: damgalı markdown raporları, hedef altında kalınca ADR-2 uyarısı
- `--doctor` · `--limit N`
- `tests/test_eval_runner.py`: **12 yeni test**, hiçbiri LLM gerektirmiyor —
  doğru cevap, yanlış cevap, halüsinasyon + öz-onarım, onarımın da başarısız olması,
  yazma sorgusunun reddi, üretim/onarım çökmesi, özet matematiği, rapor damgası,
  ADR-2 uyarısı, gold-only CLI yolu
- `pyproject.toml`: F821 geçici istisnası **silindi** (BULGU-01'de verilen sözün ilk sınavı)
- **Eksik bağımlılık teşhisi:** giriş noktası artık ham traceback yerine hangi Python'un
  kullanıldığını, sanal ortamın etkin olup olmadığını ve çalıştırılacak komutları yazıyor.
  Bu, 2026-08-16'da senin karşılaştığın hatadan geldi — ürünün kendi hata mesajı ilkesi
  (Nielsen 9) doğrulama katmanında uygulanıyordu ama giriş noktalarında uygulanmıyormuş.

Test durumu: **101 test geçiyor** (88 → 101), ruff temiz, gold-only 50/50.
