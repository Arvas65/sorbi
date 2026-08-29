# BULGU-18 (ağır) — Cetvel, fazladan kolon koyan doğru cevabı "sessiz yanlış" sayıyor

**Bulan:** bulut oturumu, 2026-08-28 · **İş paketi:** İP-34 (B-7)
**Durum:** ölçüldü, iki koşumda tekrarlandı. **Karar İhsan'da** — cetvel
politikası SPEC'e dokunur.

## Bulgu

`eval/evaluate.py`:

```python
rec["dogru"] = _normalize(pred.rows) == _normalize(gold.rows)
```

`_normalize` satırı **bütün olarak** kümeye atar. Üretilen sorgu gold'un
istediği her kolonu doğru döndürse bile yanına bir kolon daha koyduysa küme
eşit çıkmaz — cevap **yanlış**, dahası `asama=sonuc_farkli` olduğu için
**sessiz yanlış** sayılır.

| # | Soru | Üretilen kolonlar | Gold |
|---|------|-------------------|------|
| 56 | En ucuz işlem hangisi? | `ad, ucret` | `ad` |
| 100 | En çok hasta kaydı olan şehir hangisi? | `sehir, hasta_sayisi` | `sehir` |
| 81 | Hangi bölümün doktorları en çok muayene yapmış? | `ad, muayene_sayisi` | `ad` |
| 67 | Her doktorun kaç randevusu var? | `doktor_id, ad, soyad, randevu_sayisi` | `doktor_id, COUNT(...)` |

"En ucuz işlem hangisi?" sorusuna `(ad, ucret)` dönmek gold'un `(ad)`'ından
**daha kötü bir cevap değildir.** Cetvel onu sessiz yanlış yazıyor.

## Ölçüm (`tools/izdusum_denetimi.py`)

Gold'un satır kümesi, üretilen sonucun bir kolon alt kümesine eşit mi?

| Koşum | Yanlış sayılan | Bunun **yalnız fazla kolon** olanı |
|-------|----------------|-------------------------------------|
| 2026-08-27 | 31 | **8** |
| 2026-08-28 | 29 | **9** |

Dokuzunun tamamı kolon adlarıyla elle doğrulandı; tesadüfi eşleşme yok.
Ayrıca **#38** ters yönde: gold `(sehir, COUNT)` istiyor, soru
"Hipertansiyon tanısı konan hastalar hangi **şehirlerden**?" diyor —
üretilen `(sehir)` sorunun cevabıdır, gold fazladan kolon istiyor.

## Sayılar ne oluyor

| Ölçü | Bugünkü cetvel | Kolon-toleranslı |
|------|----------------|------------------|
| Execution accuracy | %71,3 (72/101) | **%80,2 (81/101)** |
| Sessiz yanlış | 29 | **20** |
| Sessiz yanlışın bayraklananı (B-7) | 6/29 = **%21** | 6/20 = **%30** |

**Aşırı okumaya karşı üç uyarı:**

1. **G-11 "karşılandı" DEĞİLDİR.** 81/101 Wilson %95 GA ≈ **%71–87**;
   eşik aralığın içinde. Değişen şey hükmün kendisi değil, hedefe olan
   mesafe: dokuz soruluk değil, sıfır-bir soruluk.
2. **#61 toleranslı sayımda bile sorunludur.** `SELECT *` doğru satırları
   döndürüyor ama içinde `tckn` var — bu bir doğruluk değil **G-16**
   meselesi. Toleranslı cetvel bunu "doğru" yazarsa yeni bir sessiz yanlış
   sınıfı doğar. Bu vaka gizlilik bayrağı adayıdır.
3. **17 vaka gerçekten yanlış** ve orada model gerçekten hata yapıyor
   (tarih sınırları, isim yerine id, ortalama tanımı). Bu bulgu onları
   temize çıkarmaz.

## Neden önemli — İP-23'ün tekrarı

İP-23 "cetvel çürümesi"ni takvim tarafında yakalamıştı. Bu, aynı ailenin
kolon tarafı. Ve zararı ölçümde değil **kararda**: B-7 projenin en büyük
riski olarak izleniyor, ADR-5'in "güvenilirlik API ile kötüleşti" tespiti
bu paydaya dayanıyor. Payda %31 şişikse o tespit de yeniden ölçülmelidir.

Daha kötüsü: bu dokuz vakayı yakalamak için güven kontrolü yazsaydık,
**doğru cevapları bayraklayan** kontroller yazmış olurduk — gereksiz bayrak
oranını kendi elimizle bozardık. İP-34'ün ilk işi bu yüzden kontrol yazmak
değil, paydayı doğrulamaktır.

## Öneri (nöbetin; karar İhsan'ın)

**Cetveli değiştirme — ikinci bir cetvel ekle.** `dogru` olduğu gibi kalsın
(tarihsel karşılaştırılabilirlik), yanına `dogru_toleransli` ölçülsün ve
rapor **iki sayıyı birden** yazsın. B-7 karnesi paydasını toleranslı olandan
alsın: "sessiz yanlış" demek *yönetime yanlış sayı gitti* demektir, fazladan
bir kolon o sayıyı yanlış yapmaz.

Reddedilen alternatifler:

| Seçenek | Neden değil |
|---------|-------------|
| Cetveli toleranslıyla değiştir | 08-16'dan bu yana her ölçüm karşılaştırılamaz hâle gelir |
| Gold'u elle düzelt | 101 soruda elle düzenleme; ayrıca gold'un kendi hataları var (#19: "2020'den sonra" için `>= 2020-01-01`) |
