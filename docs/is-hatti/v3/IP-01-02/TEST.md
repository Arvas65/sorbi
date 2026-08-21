# İP-01/02 — TEST

**Tarih:** 2026-08-11 · **Taban:** `ffe5db3` · **Koşum ortamı:** Linux x86_64, Python 3.11.15

İP-01 ve İP-02 davranış değiştirmeyen paketlerdir. Bu yüzden testin asıl sorusu
"yeni davranış doğru mu" değil, **"eski davranış bozuldu mu"**dur.

---

## Koşulan adımlar

| # | Adım | Komut | Sonuç |
|---|------|-------|-------|
| 1 | Lint | `ruff check .` | ✅ `All checks passed` |
| 2 | Birim testleri | `pytest tests/ -q` | ✅ **88 passed** (1,26 sn) |
| 3 | Test seti bütünlüğü | `python eval/evaluate.py --db demo/hospital.db --gold-only` | ✅ **50/50 gold SQL çalışıyor**, çıkış kodu 0 |
| 4 | Demo veri üretimi | `python demo/seed_data.py && python demo/seed_satis.py` | ✅ İki veritabanı da üretildi |
| 5 | Kurulum belirlenimciliği | `requirements/core.txt` iki ayrı temiz sanal ortama kuruldu, `pip freeze` çıktıları karşılaştırıldı | ✅ **Fark yok** — 15 paket, aynı sürümler |
| 6 | Docker imajı | `docker build -t sorbi:ci .` | ⚠️ **Koşulamadı** — bu ortamda docker daemon yok. İlk itişte CI koşacak. |

---

## Testten önce / sonra karşılaştırma

Değişikliklerin davranışa dokunmadığını göstermek için test paketi, kod düzenlemelerinden
**önce ve sonra** koşuldu:

| Aşama | Test sonucu |
|-------|-------------|
| Değişiklikten önce (`ffe5db3` hâli) | 88 passed |
| `ruff --fix` sonrası (içe aktarım sırası, kullanılmayan içe aktarım, tip gösterimi) | 88 passed |
| Elle düzeltmeler sonrası (`l` → `satir`, noktalı virgül ayrımı, `usedforsecurity=False`) | 88 passed |

---

## Kapsam (taban ölçüm)

```
app/__init__.py       100%
app/config.py         100%
app/preprocess.py     100%
app/executor.py        98%
app/auth.py            96%
app/validator.py       89%
app/connections.py     82%
app/audit.py            0%   ← test yok
app/generator.py        0%   ← test yok
app/pipeline.py         0%   ← test yok
app/schema_rag.py       0%   ← test yok
------------------------------
TOPLAM                 55%
```

Bu sayı v3 SPEC § 3.4'teki iddiayı doğruluyor: **pipeline'ın kendisi test altında değil.**
Kapsam eşiği İP-01'de bilinçli olarak **zorlayıcı yapılmadı** — bugün eşik koymak,
%55'i kalıcı olarak meşrulaştırırdı. Eşiğin zorlayıcı hale gelmesi İP-15'in konusudur.

---

## Test edilmeyenler (dürüstlük bölümü)

- **Docker imajı** bu ortamda derlenemedi (daemon yok). CI'ın `docker` işi ilk PR'da
  bunu doğrulayacak; doğrulanana kadar Dockerfile değişikliği **kanıtlanmamış** sayılır.
- **Python 3.10 ve 3.13** yerel olarak denenmedi; yalnız 3.11.15 üzerinde koşuldu.
  CI matrisi üç sürümü de kapsıyor, ama ilk yeşil koşuma kadar bu bir iddiadır.
- **Streamlit arayüzü** hiçbir otomatik testle kapsanmıyor (İP-01 öncesinde de öyleydi).
  `1_Dashboard.py` üzerindeki noktalı virgül düzeltmeleri gözle okunarak doğrulandı;
  arayüz elle açılıp denenmedi.
