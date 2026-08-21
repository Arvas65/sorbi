# İP-01/02 — VERIFY

**Tarih:** 2026-08-11 · **Taban:** `ffe5db3` · **Ortam:** Linux x86_64, Python 3.11.15

Verify'ın sorusu Test'ten farklıdır (`00-IS-HATTI.md` § 8):
*kod spec'in dediğini yapıyor mu* değil, **belgelerin iddiası gerçekte doğru mu.**

Dayanaksız ✔ yoktur. Aşağıdaki her satırın yanında ya bir komut çıktısı ya bir dosya:satır vardır.

---

## 1. Belge iddiaları dosyalara karşı

| # | İddia | Kontrol | Sonuç |
|---|-------|---------|-------|
| 1 | README artık var olmayan `training/` klasörünü anlatmıyor | `grep -c "training" README.md` → **0** | ✔ |
| 2 | README'nin belirttiği gibi `masked_columns` kodda kullanılmıyor | `grep -rn masked_columns app/ ui/ eval/` → yalnız `app/schema_rag.py:44` (boş varsayılan döndüren fallback) | ✔ |
| 3 | Test sayısı 88 (belgelerde 75 yazıyordu) | `pytest tests/` → **88 passed** | ✔ |
| 4 | Gold SQL sağlığı 50/50 | `eval/evaluate.py --gold-only` → **50/50 çalışıyor**, çıkış 0 | ✔ |
| 5 | `.dockerignore` var olmayan yol listelemiyor | `training/output/` satırı kaldırıldı; `.github/`, `.pytest_cache/` eklendi | ✔ |
| 6 | `.streamlit/config.toml` sır barındırmıyor | Dosya okundu: yalnız `fileWatcherType`, `gatherUsageStats` | ✔ |
| 7 | CHANGELOG'daki sürüm tarihleri gerçek | `git log --date=short` ile karşılaştırıldı: yedi commit de 2026-07-25 | ✔ |

---

## 2. README'de gösterilen her komut koşturuldu mu

| Komut | Koşuldu | Sonuç |
|-------|---------|-------|
| `python demo/seed_data.py` | ✔ | İki veritabanı üretildi |
| `python demo/seed_satis.py` | ✔ | Üretildi |
| `pytest tests/ -q` | ✔ | 88 passed |
| `ruff check .` | ✔ | All checks passed |
| `python eval/evaluate.py --db demo/hospital.db --gold-only` | ✔ | 50/50 |
| `pip install -r requirements/core.txt -r requirements/ui.txt` (hafif kurulum) | kısmi | `core.txt` iki kez temiz ortama kuruldu ve **birebir aynı** 15 paketi verdi. `ui.txt` ayrıca kurulmadı; katmanlar arası pin çelişkisi olmadığı programatik olarak doğrulandı (aşağıya bak). |
| `pip install -r requirements.txt` (tam kurulum) | ✖ | RAG katmanı torch dahil ~2 GB; bu oturumda indirilmedi. **Doğrulanmadı.** |
| `streamlit run ui/streamlit_app.py` | ✖ | Arayüz elle açılmadı. **Doğrulanmadı.** |
| `docker compose up -d` | ✖ | Bu ortamda docker daemon yok. **Doğrulanmadı.** |

---

## 3. Ölçüm iddiaları bu commit'te yeniden üretildi mi

| İddia | Yeniden üretildi | Sayı |
|-------|------------------|------|
| Kurulum belirlenimci ("aynı commit iki kez kurulunca aynı sürümler") | ✔ | İki bağımsız temiz sanal ortam, `pip freeze` çıktıları **birebir aynı**, 15 paket |
| Katmanlar arası çelişen pin yok | ✔ | `core.txt` + `rag.txt` + `ui.txt` içindeki tüm `paket==sürüm ; marker` üçlüleri karşılaştırıldı → **çelişki yok** |
| Test kapsamı %55 | ✔ | `pytest --cov=app` → TOPLAM **55%**; `audit`, `generator`, `pipeline`, `schema_rag` = %0 |
| Lint temiz | ✔ | `ruff check .` → All checks passed (12 bulgu geçici istisnayla susturuldu, BACKLOG'da) |

**Ölçüm damgası:** commit tabanı `ffe5db3` · Python 3.11.15 · ruff 0.16.2 · pytest 9.1.1 ·
sqlglot 30.16.0 · sqlalchemy 2.0.52 · pandas 2.3.3

> Not: `sqlglot` bu kilitle **25.x'ten 30.16.0'a** çıkıyor. `app/validator.py` beş sqlglot
> ifade sınıfına isimle bağlı (`TruncateTable`, `Grant`, `Attach`, `Set`, `Command`).
> 88 testin tamamı 30.16.0 altında geçiyor — yani bu beş sınıf hâlâ mevcut ve doğrulama
> katmanı çalışıyor. Kilit olmadan bu sıçrama sessizce olurdu; **kilidin ilk faydası budur.**

---

## 4. Kapsam dışı bırakılanlar sızdı mı

| Kapsam dışı | Sızdı mı |
|-------------|----------|
| Davranış değiştiren kod | ✖ Hayır. Üç kod düzenlemesi yapıldı: değişken adı `l`→`satir`, noktalı virgül ayrımı, `usedforsecurity=False`. Üçü de anlamsal olarak eşdeğer; test paketi her aşamada 88 passed. |
| `ruff format` (24 dosya) | ✖ Hayır. Bilinçli olarak yapılmadı — İP-17. |
| Güvenlik kapılarının uygulanması (Faz 2) | ✖ Hayır. Yalnız belgelerde durum düzeltmesi yapıldı. |
| Yeni özellik | ✖ Hayır. |

---

## 5. Doğrulanmadan bırakılanlar

Bunlar **açık** kalemlerdir; Ship kararında bilinmesi gerekir.

1. **Docker imajı derlenmedi** (daemon yok). Dockerfile'daki `COPY requirements/` satırı
   kanıtlanmamıştır. → REVIEW BULGU-06, BLOK önerisi.
2. **Python 3.10 ve 3.13 denenmedi.** Kilit `--universal --python-version 3.10` ile üretildi
   ve marker'lar üç sürümü de kapsıyor, ama yalnız 3.11.15 üzerinde koşuldu.
3. **Tam kurulum (`requirements.txt`) denenmedi** — RAG katmanı indirilmedi.
4. **Streamlit arayüzü elle açılmadı.** `1_Dashboard.py` üzerindeki üç satırlık düzenleme
   yalnız okunarak doğrulandı.

Bu dördü de CI'ın ilk koşumunda ya da senin makinende bir kerelik denemeyle kapanır.
Kapanmadan **v3.0.0 tag'i atılmamalıdır.**
