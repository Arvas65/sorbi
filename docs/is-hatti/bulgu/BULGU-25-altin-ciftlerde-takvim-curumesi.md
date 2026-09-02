# BULGU-25 — Altın çiftlerde takvim çürümesi: `zaman-hafta` kendiliğinden kırmızıya döndü

**Bulan:** bulut nöbeti, 2026-09-02 · **Ağırlık:** orta
**Durum:** **KAPANDI** — 2026-09-03, Ö-a uygulandı (`demo/seed_data.py` + `tests/test_seed_determinizmi.py`)
**Nerede:** `tests/cekirdek/altin/derleyici.json` · `tests/cekirdek/test_derleyici.py`
**İlgili:** İP-23 (cetvel çürümesi), BULGU-18 (cetvel politikası), BULGU-31, CLAUDE.md § 7

## Belirti

Taze tohumlanmış temiz bir klonda, `ip-46-cekirdek` (`148cfd1`) üzerinde:

```
$ python3 demo/seed_data.py && python3 -m pytest tests/
1 failed, 672 passed

FAILED tests/cekirdek/test_derleyici.py::test_altin_cift_gercek_veritabaninda_kosar[zaman-hafta]
E   AssertionError: zaman-hafta: satır sayısı değişti
E   assert 79 == 80
```

**Kod değişmedi. Takvim değişti.**

## Kök sebep

`demo/seed_data.py:31` → `TODAY = date.today()`. Veri **bugüne göre**
üretiliyordu. Altın çiftler ise satır sayısını sabit tutuyor.

Asıl cümle dosyanın kendi başlığındaydı:

> Deterministik (seed=42) — her çalıştırmada aynı veri.

`random.seed(42)` rastgele diziyi sabitler, **tarihleri sabitlemez.** Söz
docstring'de duruyordu; onu tutan hiçbir şey yoktu. Bu, CLAUDE.md § 7'nin
üç satırının aynı anda tekrarı: "beklenen değeri betiğe gömmek",
"referans günü sabit kodlamak", ve "gizlilik vaadini docstring'e yazmak"
— sonuncusu bu kez determinizm vaadi.

İP-23 bu hastalığı **ölçüm cetvelinde** teşhis edip `eval/tarih_sabitle.py`
ile çözmüştü. Altın çiftler o çözümün dışında doğdu.

## Etkisi (ölçülmüş)

43 altın çiftin **9'u** zaman filtreli ve **dokuzu da** sabit bir
`satir_sayisi` iddiası taşıyor: `zaman-gun` (544), `zaman-hafta` (80),
`zaman-ay` · `zaman-randevu` (19), `tam-kombinasyon` ·
`zaman-arti-kirilim` (10), `zaman-ceyrek` (7), `zaman-yil` (2),
`zaman-kirilimsiz` (1).

Biri düştü. Kalan sekizi ay/çeyrek sınırında düşecekti — **1 Ekim'de
beşi birden.**

**Neden şimdiye kadar görülmedi:** İhsan'ın `demo/hospital.db` dosyası
2026-07-25'te üretilmiş ve yeniden tohumlanmıyordu. Kusur yalnız taze
tohumlanan bir klonda — CI'da ve bulut nöbetinde — görünüyordu.
20260903-0010 koşumunun 674/674 yeşili, **eski bir veri dosyası
sayesinde** yeşildi.

## Karar ve çözüm (2026-09-03)

Karar İhsan'ın: **Ö-a** — demo verisinin penceresi sabitlensin, altın
çiftlere dokunulmasın.

Ö-a'nın göze görünen maliyeti şuydu: referans günü değiştirmek veriyi
değiştirir, veri değişince 43 çiftin `satir_sayisi`'ı ve karnenin mutant
havuzu **yeniden temellendirilmek** zorunda kalır.

**Gerek kalmadı.** `seed_data.py` ilk commit'ten (`86981d3`) beri hiç
değişmemişti, yani üretim tekrarlanabilirdi. Diskteki veritabanının hangi
günle üretildiği arandı:

| Denenen gün | Veri imzası |
|---|---|
| 2026-07-23 | `2c0a7f59…` |
| 2026-07-24 | `f09bf103…` |
| **2026-07-25** | **`20e2657d…` ← diskteki dosyayla birebir** |
| 2026-07-26 | `020ec956…` |

Referans gün 2026-07-25'e donduruldu — **cetvelin kalibre edildiği gün.**
`python demo/seed_data.py` artık diskte duran veriyi satır satır aynı
üretiyor: 43 altın çift, 101 gold beklentisi ve karne havuzu dokunulmadan
geçerli kaldı. Eşleşme Python 3.11 (bulut) ile 3.13 (İhsan) arasında
tuttu; üretim sürümden de bağımsız.

`SORBI_BUGUN` kaçış kapısı duruyor — projenin geri kalanıyla aynı.

## Sözü çalıştırılabilir kılan beş test

`tests/test_seed_determinizmi.py`:

1. **Donmuş imza** — izole bir dizinde tohumlanan verinin tüm satırlarının
   sha256'sı sabitle karşılaştırılıyor. Docstring'in vaadi artık bir iddia.
2. **İki koşum aynı veriyi verir.**
3. **Duvar saati denetimi (AST)** — `.today()/.now()/.utcnow()` çağrısı yok.
   Metin araması değil AST: hem betiğin hem testin docstring'i kusuru adıyla
   anlatıyor, metne bakan bir denetim kendi belgesine takılırdı.
4. **Referans gün veriyi gerçekten belirliyor** — `SORBI_BUGUN` başka gün
   verince veri değişiyor. Bu geçmezse sabit ölüdür ve imza yanlış şeyi korur.
5. **Depodaki veritabanı cetvelin dayandığı veri** — asıl nöbetçi. Biri
   `hospital.db`'yi başka bir günle tohumlarsa burası öter, altın çiftler
   ötmeden.

Tohumlama izole dizinde koşuluyor: bir testin yan etkisi olarak ölçümün
dayandığı veriyi ezmek, tam da bu belgenin anlattığı hatanın başka bir
türü olurdu.

**Reddedilen seçenek Ö-c** kayda geçsin: değeri her tohumlamada yeniden
yazmak. Kendi beklentisini kendi güncelleyen bir test hiçbir şey iddia
etmez.

## Ders

Bir cetvel kusuru düzeltildiğinde, **aynı kusurun başka nerede yaşadığı
aranmalı.** İP-23 ölçüm cetvelini onardı; altın çiftler o gün henüz yoktu
ve doğdukları anda aynı hatayı yeniden yaptılar. Onarım bir yamadır;
kural değilse tekrar eder.

CLAUDE.md § 7'ye satır olarak eklendi (nöbet tarafından).
