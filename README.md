# SorBI — Türkçe Doğal Dilden SQL Üreten BI Asistanı

> "Geçen ay kardiyolojide en çok muayene yapan 5 doktor kim?" yaz — SQL'i ve cevabı gör.

Türkçe soruları, bağlı veritabanının şemasına uygun **salt-okunur** SQL'e çevirir.
Yerel LLM (Ollama) varsayılandır: hasta verisi gibi özel nitelikli veriler makineden çıkmaz (KVKK).

Tüm tasarım kararları sistem analizi dosyasına dayanır (`docs/` — ADR-1..5, G-01..G-20).

## Mimari

```
Soru (TR) → Ön işleme (kök indirgeme + tarih çözümleme)     app/preprocess.py
          → Bağlam (şema + terim sözlüğü, Chroma RAG)        app/schema_rag.py
          → LLM (Ollama yerel | OpenAI-uyumlu API, maskeli)  app/generator.py
          → Doğrulama (sqlglot: SELECT-only + lehçe)         app/validator.py
          → Salt-okunur çalıştırma (30 sn limit)             app/executor.py
          → Sonuç + SQL + denetim izi                        app/audit.py
```

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt          # tam kurulum (çekirdek + RAG + arayüz)
# Hafif kurulum (RAG'siz — bağlam anahtar-kelime moduna düşer, sistem çalışır):
#   pip install -r requirements/core.txt -r requirements/ui.txt

# Yerel model — https://ollama.com kurulu olmalı:
ollama pull llama3.2:3b

# Demo hastane veritabanını üret (SQLite, tamamen sentetik veri):
python demo/seed_data.py          # demo/hospital.db

# Arayüz:
streamlit run ui/streamlit_app.py
```

## Docker ile kurulum (pilot / on-prem)

```bash
docker compose up -d
docker compose exec ollama ollama pull llama3.2:3b   # ilk kurulumda bir kez
# Arayüz: http://localhost:8501
```

İlk açılışta **yönetici hesabı** oluşturmanız istenir. Roller: yönetici
(her şey + kullanıcı yönetimi) ve analist. Şifreler PBKDF2 ile hash'lenir,
düz metin saklanmaz. Denetim izi (G-17) oturum açan gerçek kimliğe bağlanır.

## Kendi veritabanını bağlama (v2)

Arayüzdeki **Bağlantı** sayfasından SQLite / PostgreSQL / MySQL / SQL Server seçip
bağlanabilirsiniz; şema otomatik keşfedilir, SOR sayfası yeni şemayı kullanır.
Şifreler diske yazılmaz. Sunucu DB'lerinde **salt-okunur hesap** kullanmak önkoşuldur (G-14).
Sürücüler: `requirements.txt` sonundaki opsiyonel satırlara bakın.
Farklı şemayla denemek için ikinci demo: `python demo/seed_satis.py`

## Değerlendirme (G-11: execution accuracy)

```bash
# 0) Önce ortam kontrolü — Ollama ayakta mı, model yüklü mü, üretim çalışıyor mu:
python eval/evaluate.py --doctor
# Sorun varsa tam olarak ne yapılacağını yazar (Windows/Vulkan çökmesi dahil).

# 1) Hızlı deneme (ilk 5 soru):
python eval/evaluate.py --db demo/hospital.db --limit 5

# 2) Tam ölçüm:
python eval/evaluate.py --db demo/hospital.db --testset eval/test_set_tr.jsonl
# Çıktı: accuracy + gecikme (p50/p95), soru bazlı rapor → eval/results.json
#        ve docs/kanit/accuracy-<tarih>.md + docs/kanit/gecikme-<tarih>.md

# LLM'siz bütünlük kontrolü (gold SQL'ler geçerli mi ve çalışıyor mu):
python eval/evaluate.py --db demo/hospital.db --gold-only
```

> **Not:** G-11'in %80 hedefi henüz **ölçülmedi** — bugün depoda yayınlanmış bir
> execution accuracy sayısı yoktur. Test setinin kendi sağlığı ölçülüdür (gold SQL 50/50).
> Baseline ölçümü İP-03'ün konusudur; sonuç `docs/kanit/` altında tarih, model ve
> commit damgasıyla yayınlanacaktır.

## Sık karşılaşılan kurulum sorunu

`ModuleNotFoundError: No module named 'sqlalchemy'` alıyorsanız, sanal ortam etkin
değildir — `python` sistem kurulumunu kullanıyordur:

```bat
.venv\Scripts\activate            :: Windows  (Linux/Mac: source .venv/bin/activate)
python eval\evaluate.py --doctor
```

Komut isteminin başında `(.venv)` görmelisiniz. Aktivasyondan sonra da aynı hatayı
alıyorsanız ortam boştur: `pip install -r requirements\core.txt`
(ölçüm için yeterli, torch indirmez).

`eval/evaluate.py` bu durumu artık kendisi teşhis eder ve ne yapılacağını yazar.

## Testler

```bash
python demo/seed_data.py && python demo/seed_satis.py   # önce demo veritabanları
pytest tests/ -q                                        # 88 birim testi, LLM gerektirmez
ruff check .                                            # lint
```

CI her PR'da şunu koşar: ruff → pytest (Python 3.10 / 3.11 / 3.13) → test seti bütünlüğü
(`--gold-only`) → Docker derlemesi. Hiçbir adım gerçek bir LLM servisine ihtiyaç duymaz.

## Klasör yapısı

```
app/            çekirdek pipeline
ui/             Streamlit arayüzü (soru ekranı, dashboard, bağlantı, kullanıcılar)
demo/           hastane + satış şemaları, sentetik veri üreteçleri, terim sözlüğü
eval/           Türkçe test seti + ölçüm koşucusu
tests/          birim testleri (pytest)
requirements/   katmanlı ve pinlenmiş bağımlılıklar
docs/           sistem analizi dosyası
docs/is-hatti/  iş hattı, SPEC, PLAN, backlog
```

## Güvenlik: tasarım hedefi ve bugünkü durum

Bu bölüm bilinçli olarak iki sütunludur. Bir güvenlik özelliğinin "hedeflendiği" ile
"uygulandığı" aynı şey değildir ve bu ayrımı okuyucudan saklamak, aracın kendisinden
daha büyük bir risktir.

| Kapı | Hedef | Bugünkü durum |
|------|-------|---------------|
| G-18 | SELECT dışı her sorgu sözdizim düzeyinde reddedilir | **Uygulanıyor** — `app/validator.py`, testlerle kapalı. Tehlikeli fonksiyon allowlist'i henüz yok (İP-08) |
| G-14 salt-okunurluk | Veritabanına yalnızca salt-okunur bağlantı | **Kısmi** — SQLite'ta dosya düzeyinde zorlanıyor. PostgreSQL / MySQL / SQL Server'da salt-okunur hesap kullanmak **kurulum önkoşuludur**; uygulama bunu şu an doğrulamıyor (İP-07) |
| G-14 zaman aşımı | 30 sn'yi aşan sorgu iptal edilir | **Kısmi** — yalnız SQLite'ta gerçek. Sunucu veritabanlarında sorgu zaman aşımı henüz ayarlanmıyor (İP-07) |
| G-16 maskeleme | Kişisel veri işaretli kolonlar dış servise giden istekte maskelenir | **Uygulanmadı** — dışarıya veri değeri gitmiyor (istem yalnız şema metaverisi + soru içerir) ve sorudaki 11 haneli kimlik benzeri diziler maskeleniyor. Ancak `demo/glossary.json` içindeki `masked_columns` listesi kodda kullanılmıyor: bu kolonları isteyen bir soru sonucu ham döndürür (İP-06) |
| G-17 denetim izi | Kim, ne zaman, hangi soru, hangi SQL, kaç satır — değiştirilemez kayıt | **Kısmi** — her soru-sorgu çifti oturum açan gerçek kimlikle yazılıyor ve sonuç verisi saklanmıyor. Kayıt düz bir SQLite dosyasıdır; bütünlük zinciri (hash) henüz yok, yani "değiştirilemez" değil "ekleme-yalnız" doğru tanımdır (İP-09) |

Yol haritası ve iş paketleri: `docs/is-hatti/v3/PLAN.md`.
Açık maddelerin tam listesi: `docs/is-hatti/BACKLOG.md`.

> **Pilot kurulum yapacaksanız:** yukarıdaki "Kısmi" ve "Uygulanmadı" satırları kapanana kadar
> SorBI'yi yalnızca salt-okunur bir replika üzerinde ve kişisel veri içermeyen ya da
> maskelenmiş bir görünüm üzerinden çalıştırın.
