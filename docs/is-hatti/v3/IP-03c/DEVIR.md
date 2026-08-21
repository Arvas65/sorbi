# İP-03c — DEVİR NOTU (İhsan uyandığında okunacak)

**Yazıldı:** 2026-08-16, sen uyurken · **Durum:** Build ✔ Test ✔ Verify ✔
**Bekleyen:** senin Review triyajın, sonra Ship kararın

---

## 1. Ne yapıldı — üç cümle

Sessiz yanlışı yakalayan, modelin kendi güven beyanına hiç bakmayan, LLM
gerektirmeyen sekiz kontrol yazıldı ve uçtan uca hatta takıldı. Kontrollerin
**kendisi** ölçüldü: 101 doğru sorgu + 240 kasten bozulmuş sorgu üzerinde
yakalama %81,2, gereksiz uyarı %1,0. Ölçüm sırasında kendi kodumuzda beş
kusur, `preprocess`te bir Türkçe hatası ve uçtan uca hattın hiç test
edilmemiş olduğu bulundu; hepsi kapatıldı.

---

## 2. Sayılar

| | İP-03 sonu | Şimdi |
|---|---|---|
| Test | 213 | **292** |
| Kapsam (app+eval) | %63 | **%74**, eşik artık CI'ı kırar |
| `app/pipeline.py` kapsamı | %0 | %86 |
| ruff | temiz | temiz |
| B-7 yakalama (mutasyon) | — | **%82,9** (199/240) |
| B-7 gereksiz uyarı | — | **%1,0** (1/101) |

Doğruluk ve gecikme **ölçülmedi** — bu kutuda Ollama yok. Ölçüm senin
makinende yapılacak (§5).

---

## 3. Kontrolün gelişimi — beş turda

| Tur | Ne değişti | Yakalama | Yanlış alarm |
|-----|-----------|----------|--------------|
| 1 | ilk beş kontrol | %54,6 | %15,8 |
| 2 | `sifir_toplama` + `filtresiz` eklendi | %84,2 | %14,9 |
| 3 | `keywords` İ hatası + ön ek eşleşmesi | %84,2 | %12,9 |
| 4 | LIMIT'te harcanan sayı daraltma sayılmaz | %82,5 | **%6,9** |
| 5 | iki zayıf kontrol varsayılan kapalı | %81,2 | **%1,0** |
| 6-8 | `atlanan_kolon` eklendi, kolon adı parçalara ayrıldı, kök alt sınırı 5 harf, 'kayıt' durak sözcüğü | **%82,9** | **%1,0** |

Son adımda 1,3 puan yakalama verip yanlış alarmı yediye böldük. Gerekçe:
sürekli bağıran bir uyarı okunmaz hâle gelir ve o noktadan sonra sessiz
yanlış geri döner — gürültü, kaçırmadan pahalıdır. Karar `app/config.py`
içinde ölçüm tablosuyla birlikte yazılı; `SORBI_GUVEN_KAPALI=` ile geri alınır.

---

## 4. Yan ürünler (aranmadan bulunanlar)

- **`preprocess.keywords` Türkçe İ hatası.** `İşlemlerin` → `şlem`.
  `'İ'.lower()` Python'da `i` + birleştirici nokta verir; ikinci kod noktası
  token sınıfında olmadığı için kelime ikiye bölünüyor, `i` kısa diye atılınca
  **baş harfi eksik** bir kök kalıyordu. Türkçe bir üründe İ ile başlayan her
  kelime etkileniyordu. RAG anahtar-kelime yolunu da etkiler → **İP-22**.
- **`app/pipeline.py` hiç test edilmemişti** (%0). K1 eşiği, K2 reddi,
  öz-onarım, elle SQL bypass'ı — hiçbiri. 13 test yazıldı.
- **İP-15 kapandı.** `generator.py`'de API hatası iki yerde sessizce
  yutuluyordu; artık `logging.warning` + `SON_API_HATASI`. Kapsam eşiği
  zorlayıcı hale getirildi (`fail_under = 70`).

---

## 4b. Sen uyurken kapatılan üç backlog maddesi

| # | Ne | Not |
|---|-----|-----|
| **İP-15** | API hatası artık yutulmuyor + kapsam eşiği zorlayıcı | `fail_under = 70` |
| **İP-19** | B-7 API modunda artık kör değil | Gizlilik kısıtı **yanlış katmandaydı**: risk değerleri okumakta değil, dış servise göndermekte. Örnekleme her zaman yapılıyor (yerelde), `SORBI_ORNEK_DEGER` yalnız İSTEME yazmayı kapatıyor. G-16 maskeleme aynen duruyor. |
| **İP-16** | Tanımlayıcı alıntılama | **Bulgunun tarifi yanlıştı.** Dashboard tablo adı gömmüyor; gerçek nokta şema sekmesindeki elle `"{ad}"` alıntılamasıydı. Sürücünün `identifier_preparer`ına çevrildi. Ders: Review bulgusunun kendisi de doğrulanmalı. |

---

## 5. Senin makinende koşacaklar (sırayla)

```
cd C:\Users\Arvas\SorBı
.venv\Scripts\activate

del .git\index.lock                       :: hâlâ duruyorsa
ruff check .
pytest tests\ --cov=app --cov=eval        :: 287 test, kapsam >= %70

python eval\guven_olcum.py                :: LLM'siz, ~5 sn
python eval\evaluate.py                   :: 101 soru, Ollama gerekir
```

Son komut raporun içine **"Güven kontrolü karnesi"** diye yeni bir bölüm
yazacak. Beklentim:

- doğruluk **değişmemeli** (~%62). Değişirse kontrol yan etki üretiyordur ve
  bu bir hatadır, bulgu olarak açılmalı.
- p95 **değişmemeli** (~21 sn).
- yakalama **> %50** çıkmalı. Mutasyon karnesindeki %81'i beklemiyorum:
  mutantlar bizim hayal ettiğimiz hatalar, model başka hatalar yapıyor.

---

## 6. Kapıdaki üç şey — karar senin

1. **Review triyajı:** `docs/is-hatti/v3/IP-03c/REVIEW.md` — yedi madde,
   her birinde önerim var, kutular boş.
2. **ADR-1 / ADR-2 revizyonları:** `docs/is-hatti/v3/ADR/` — ADR-1'in
   gerekçesi ölçümle çürüdüğü için yeniden yazıldı, ADR-2 tetiklendi ama
   ertelendi. Gerekçeleri okuyup onaylaman gerekiyor.
3. **Ship:** BULGU-06 hâlâ BLOK. İlk yeşil CI koşumu olmadan `v2.4.0` yok.
