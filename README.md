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
pip install -r requirements.txt

# Yerel model — https://ollama.com kurulu olmalı:
ollama pull llama3.2:3b

# Demo hastane veritabanını üret (SQLite, tamamen sentetik veri):
python demo/seed_data.py          # demo/hospital.db

# Arayüz:
streamlit run ui/streamlit_app.py
```

## Kendi veritabanını bağlama (v2)

Arayüzdeki **Bağlantı** sayfasından SQLite / PostgreSQL / MySQL / SQL Server seçip
bağlanabilirsiniz; şema otomatik keşfedilir, SOR sayfası yeni şemayı kullanır.
Şifreler diske yazılmaz. Sunucu DB'lerinde **salt-okunur hesap** kullanmak önkoşuldur (G-14).
Sürücüler: `requirements.txt` sonundaki opsiyonel satırlara bakın.
Farklı şemayla denemek için ikinci demo: `python demo/seed_satis.py`

## Değerlendirme (G-11: execution accuracy)

```bash
python eval/evaluate.py --db demo/hospital.db --testset eval/test_set_tr.jsonl
# Çıktı: execution accuracy %, soru bazlı rapor → eval/results.json

# LLM'siz bütünlük kontrolü (gold SQL'ler geçerli mi ve çalışıyor mu):
python eval/evaluate.py --db demo/hospital.db --gold-only
```

## Testler

```bash
pytest tests/ -q        # birim testleri (LLM gerektirmez; önce demo DB'yi üretin)
```

## QLoRA fine-tune (ADR-2 koşulu: baseline < %80 ise)

```bash
pip install -r training/requirements-train.txt
python training/generate_dataset.py     # sentetik TR soru-SQL çiftleri
python training/train_qlora.py          # RTX 3060 6GB için ayarlı (4-bit, 3B)
```

## Klasör yapısı

```
app/        çekirdek pipeline
ui/         Streamlit soru ekranı
demo/       hastane şeması + sentetik veri üreteci + terim sözlüğü
eval/       Türkçe test seti + ölçüm koşucusu
training/   veri seti üreteci + QLoRA eğitim scripti
tests/      birim testleri (pytest)
docs/       sistem analizi dosyası
```

## Güvenlik varsayılanları (pazarlık edilemez — G-14/16/17/18)

- Veritabanına **yalnızca salt-okunur** bağlantı; SELECT dışı her sorgu sözdizim düzeyinde reddedilir
- 30 sn'yi aşan sorgu iptal edilir
- API modunda kişisel veri işaretli kolonlar maskelenir; hasta verisi dış servise gitmez
- Her soru-sorgu çifti denetim izine yazılır (kim, ne zaman, hangi SQL, kaç satır)
