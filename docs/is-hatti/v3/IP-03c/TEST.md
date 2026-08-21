# İP-03c — TEST

**Tarih:** 2026-08-16 · **Ortam:** LLM'siz, demo SQLite'a karşı

## 1. Süit

| | İP-03 sonu | İP-03c sonu |
|---|---|---|
| Test sayısı | 213 | **292** |
| ruff | temiz | temiz |
| Kapsam (`app` + `eval`) | %63 | **%74** — eşik artık ZORLAYICI (`fail_under = 70`) |
| `app/pipeline.py` kapsamı | **%0** | %86 |

Yeni dosyalar: `tests/test_guven.py` (43), `tests/test_pipeline.py` (13),
`tests/test_guven_olcum.py` (12), `tests/test_generator_dusus.py` (3),
`tests/test_eval_runner.py` +3.

Uçtan uca hattın hiç testi olmaması, İP-03c'nin yan ürünü olarak çıktı: güven
kontrolünü hatta takarken `pipeline.ask()`'in tek bir dalının bile test altında
olmadığı görüldü. K1 güven eşiği, K2 doğrulama reddi, öz-onarım ve elle SQL
bypass'ı artık test ediliyor.

## 2. Kontrolün kendi karnesi — mutasyon ölçümü

`python eval/guven_olcum.py` · 101 gold + 240 geçerli mutant (17 mutant
sonucu değiştirmediği için sayılmadı — yanlış cevap değiller).

| Ölçü | Değer |
|------|-------|
| Bilinen yanlışın yakalananı | **199/240 (%82,9)** |
| Doğru cevaba konan gereksiz bayrak | **1/101 (%1,0)** |

### Mutasyon türüne göre

| Mutasyon | Yakalama |
|----------|----------|
| imkânsız filtre (boş küme) | 96/101 (%95) |
| filtre değeri yazımı (İ/I) | 35/38 (%92) |
| COUNT↔SUM↔AVG takası | 26/30 (%87) |
| WHERE düşürme | 32/54 (%59) |
| LIMIT düşürme | 10/17 (%59) |

### Kontrol bazında

| Kontrol | Yanlışta | Doğruda | İsabet |
|---------|----------|---------|--------|
| `sifir_toplama` | 75 | 0 | %100 |
| `bos_sonuc_filtreli` | 54 | 0 | %100 |
| `bilinmeyen_deger` | 35 | 0 | %100 |
| `filtresiz` | 33 | 0 | %100 |
| `atlanan_kolon` | 5 | 0 | %100 |
| `bicim_adet` | 4 | 0 | %100 |
| `bos_sonuc` | 1 | 0 | %100 |
| `toplama_uyumsuz` | 29 | 1 | %97 |
| `sema_ortusmez` *(kapalı)* | 16 | 6 | %73 |
| `bicim_sayi` *(kapalı)* | 1 | 1 | %50 |

Tek gereksiz bayrak: **"EKG işlemi kaç kez uygulanmış?"** — gold `SUM(adet)`
kullanıyor, soru "kaç kez" diyor. Kontrolün COUNT beklemesi savunulabilir bir
şüphedir; bunu bir kusur değil, kabul edilebilir bir uyarı sayıyoruz.

## 3. Bu ölçümün sınırı

Mutantlar **bizim** hayal ettiğimiz hatalardır. Modelin gerçekte yaptığı
hatalarla aynı dağılımda olduklarını iddia etmiyoruz. Gerçek karne, bir
sonraki Ollama'lı 101 soruluk koşumda `accuracy-*.md` içindeki
"Güven kontrolü karnesi" bölümünde çıkacak — orada evren, doğruluğu
gerçekten bilinen model çıktılarıdır.

Mutasyon karnesinin işi başka: kontrolü değiştirip **3 saniyede** etkisini
görmek. Bugün bu döngü sekiz kez döndü ve yakalama %54,6 → %82,9'a,
yanlış alarm %15,8 → %1,0'e taşındı.
