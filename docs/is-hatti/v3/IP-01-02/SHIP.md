# İP-01/02 — SHIP  ▸ KAPI 3: KARAR BEKLİYOR

**Hazırlayan:** Claude · **Tarih:** 2026-08-11
**Dal:** `ip-01-02-altyapi` · **Taban:** `ffe5db3`
**Karar:** İhsan Arvas — *bekleniyor* (**ÇIKAR** · **BEKLET: …** · **GERİ AL**)

---

## Önerilen sürüm

**v2.4.0** — küçük sürüm artışı.

Gerekçe: kırıcı değişiklik yok, davranış değişikliği yok; ama yeni bir yapı geldi
(katmanlı bağımlılıklar, CI, iş hattı belgeleri) ve README'nin güvenlik bölümü anlamlı
biçimde değişti. Yama sürümü (2.3.1) bunu küçümser.

**v3.0.0 tag'i şimdi atılmamalıdır** — v3, kanıt turunun tamamlanmasıyla hak edilir.

---

## Değişen dosyalar

**Yeni (12+9):** `pyproject.toml` · `CHANGELOG.md` · `.github/workflows/ci.yml` ·
`requirements/` (11 dosya: 6 `.in` kaynağı + 6 pinlenmiş kilit) ·
`docs/is-hatti/00-IS-HATTI.md` · `docs/is-hatti/BACKLOG.md` ·
`docs/is-hatti/v3/SPEC.md` · `docs/is-hatti/v3/PLAN.md` ·
`docs/is-hatti/v3/IP-01-02/{REVIEW,TEST,VERIFY,SHIP}.md` · `docs/kanit/`

**Değişen (13):** `README.md` · `requirements.txt` · `Dockerfile` · `.dockerignore` ·
`app/{pipeline,preprocess,schema_rag,validator}.py` · `eval/evaluate.py` ·
`tests/{test_eval_testset,test_preprocess}.py` · `ui/streamlit_app.py` · `ui/pages/1_Dashboard.py`

Toplam: 13 dosyada 92 ekleme, 58 silme (kod tarafı) + yeni belgeler.

---

## Göç / kurulum notu

Mevcut kurulumu olan biri için **hiçbir şey değişmiyor**: `pip install -r requirements.txt`
aynı komut, artık pinlenmiş sürümleri kuruyor. Bunun tek görünür etkisi, kurulumun
artık tekrarlanabilir olması ve `sqlglot`'un 25.x'ten 30.16.0'a sabitlenmesidir.

Yeni seçenek — RAG'siz hafif kurulum (torch indirmez):

```bash
pip install -r requirements/core.txt -r requirements/ui.txt
```

Bu modda bağlam derleme anahtar-kelime eşleşmesine düşer; sistem çalışır, kalite düşer.

---

## Geri alma

```bash
git checkout master          # dal birleştirilmediyse: hiçbir şey yapmaya gerek yok
git branch -D ip-01-02-altyapi
```

Birleştirildikten sonra geri almak için:

```bash
git revert --no-commit <birlestirme-commit>
git commit -m "İP-01/02 geri alındı"
```

Bağımlılık kilidi geri alınırsa `pip install -r requirements.txt` yeniden serbest
sürüm çözümlemesine döner — yani eski (tekrarlanamaz) davranışa.

---

## Ship öncesi kapatılması gereken — BLOK

Bu iki madde kapanmadan tag atılmamalıdır (kaynak: `VERIFY.md` § 5, `REVIEW.md` BULGU-06):

1. **İlk CI koşumu yeşil olmalı.** Docker imajı bu ortamda derlenemedi; `Dockerfile`'daki
   `COPY requirements/ ./requirements/` satırı henüz kanıtlanmadı.
2. **`.git/index.lock` temizlenmeli** ve değişiklikler gerçekten commit'lenmeli
   (aşağıdaki nota bakın).

---

## Bilinen kısıtlar (bu sürümle gitmiyor, kayıt için)

- G-16 maskeleme uygulanmıyor (İP-06) · G-14 zaman aşımı ve salt-okunurluk yalnız
  SQLite'ta gerçek (İP-07) · bağlantı değişikliği süreç genelinde etkili (İP-10) ·
  G-11 hiç ölçülmedi (İP-03)
- Bu sürüm bunların **hiçbirini düzeltmiyor**; yalnızca belgelerin artık doğruyu
  söylemesini sağlıyor.

---

## Karar

| | |
|---|---|
| **ÇIKAR** | CI yeşile döndükten sonra `master`'a birleştir, `v2.4.0` tag'i at, CHANGELOG'daki "Yayınlanmamış" başlığını `[2.4.0] — <tarih>` yap |
| **BEKLET** | Gerekçe ve tetikleyici koşul buraya yazılır |
| **GERİ AL** | Dal birleştirilmez; öğrenilenler BACKLOG'a yazılır |

**Karar:** _(bekleniyor)_
