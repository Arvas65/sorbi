# SorBI

**Türkçe doğal dilden pano üreten BI motoru** — veriye dokunmadan, SQL'ini her zaman göstererek.

> *A Turkish-first natural-language BI engine. It connects read-only to an unfamiliar
> database, proposes a semantic model a human confirms, and compiles questions against
> that model deterministically — instead of trusting free-form LLM SQL.*

## Neden

Serbest LLM SQL'i ölçtük: 101 soruluk Türkçe sette en iyi model **%69–72** doğru,
ve yanlışların **%95–100'ü sessiz** — sorgu çalışıyor, tablo temiz, sayı yanlış.
Daha iyi model hatayı azaltmıyor, **görünmez** yapıyor.

SorBI v4 bu yüzden farklı çalışır:

```
Bağlan (salt-okunur) → Tara → Anlam modeli öner → İnsan onaylar
Soru → Eşleyici (LLM → Seçim, yalnız sözlükteki adlarla)
     → Derleyici (deterministik, fan-out korumalı) → Doğrulama (yalnız SELECT)
     → Yürütücü (zaman aşımı, salt-okunur) → Pano + SQL + satır sayısı
```

Yanlış bir etiket her cevabı **tutarlı** biçimde yanlış yapar — ama o yanlış
bir kez, anlam modelinde, görünür ve düzeltilebilir. Serbest SQL'de her soru
yeni bir zar atışıdır.

## Durum

| | |
|---|---|
| v4 çekirdek (`app/cekirdek/`) | Yazıldı, testli — anlam modeli, seçim, derleyici, pano |
| Ürüne bağlantı | **Henüz yok** — arayüz v3 serbest SQL yolunu gösteriyor. Sıradaki iş ([PLAN](docs/PLAN.md) Faz B) |
| Testler | 666 · LLM'siz · CI her push'ta |

## Hızlı başlangıç

```bash
python -m venv .venv && .venv\Scripts\activate       # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python demo/seed_data.py && python demo/seed_satis.py  # sentetik demo veritabanları
streamlit run ui/streamlit_app.py
```

Yerel model için [Ollama](https://ollama.com) + `ollama pull qwen2.5-coder:7b-instruct`.
API modu (Gemini) için Windows'ta `gemini-kur.bat`. Docker: `docker compose up -d`.

İlk açılışta yönetici hesabı istenir; parolalar PBKDF2 ile hash'lenir.

## Denetim

```bash
ruff check . && pytest tests/                 # lint + testler
python eval/evaluate.py --gold-only           # test setinin bütünlüğü
python eval/guven_olcum.py                    # sessiz-yanlış kontrollerinin mutasyon karnesi
python eval/evaluate.py --doctor              # ölçümden önce ortam
python eval/evaluate.py                       # 101 soruluk doğruluk ölçümü (LLM gerekir)
```

Windows'ta: `kontrol.bat` (hızlı) · `kontrol.bat tam` (+ ölçüm) · `guncelle.bat`.

## Güvenlik: hedef ve bugünkü durum

Bir güvenlik özelliğinin *hedeflendiği* ile *uygulandığı* aynı şey değildir.

| Kapı | Bugünkü durum |
|------|---------------|
| Yalnız SELECT | **Uygulanıyor** — `app/validator.py`, kapalı devre, testli |
| Salt-okunurluk | **Kısmi** — SQLite'ta dosya düzeyinde. Sunucu DB'lerinde salt-okunur hesap **kurulum önkoşulu**; oturum düzeyinde zorlama İP-43 |
| Zaman aşımı | **Kısmi** — yalnız SQLite'ta gerçek; sunucu tarafı İP-43 |
| Veri dışarı çıkmaz | **Uygulanıyor** — API modunda yalnız şema metaverisi gider, değerler koşulsuz maskelenir (`mask_context`, testli) |
| Denetim izi | **Kısmi** — ekle-yalnız; bütünlük zinciri (hash) yok |

> Pilot kurulum yapacaksanız: "Kısmi" satırlar kapanana kadar SorBI'yi yalnız
> salt-okunur bir replika üzerinde çalıştırın.

## Depo

```
app/cekirdek/   v4 saf çekirdek          app/            v3 hattı + kenarlar
ui/             Streamlit                eval/           ölçüm + karne
demo/           sentetik şemalar         tests/          pytest (LLM'siz)
docs/PLAN.md    yol haritası (FDE)       docs/kararlar/  ADR'ler
docs/tasarim/   v4 SPEC, mimari          docs/kanit/     ölçüm tablosu
```

Çalışma düzeni ve alınmış kararlar: [CLAUDE.md](CLAUDE.md). Lisans: ticari, tüm hakları saklı ([LICENSE](LICENSE)); `c0cfbc8`'e kadarki sürüm MIT ile yayımlanmıştı.
