# BULGU-27 — Bulut oturumunun karne koşumu üretim kanıtına yazıyor

**Bulan:** bulut nöbeti, 2026-09-02 (kendi çalışma ağacını temizlerken)
**Ağırlık:** orta · **Durum:** **AÇIK — düzeltilmedi** (kanıt biçimine dokunur)
**Nerede:** `eval/guven_olcum.py:319` `_gecmise_yaz` · `docs/kanit/KARNE-GECMIS.log`
**İlgili:** İP-33 (testin üretim kanıtını kirletmesi), BULGU-19, CLAUDE.md § 3.5 / § 10

## Belirti

Nöbet, LLM'siz denetimin bir parçası olarak `python3 eval/guven_olcum.py`
koştu. Sonrasında klonun çalışma ağacında:

```
$ git diff docs/kanit/KARNE-GECMIS.log
+KARNE_OZET gun=2026-08-31 gold=101 alarm=1 mutant=239 yakalanan=199 zbos=0
+KARNE_OZET gun=2026-08-31 gold=101 alarm=1 mutant=239 yakalanan=199 zbos=0
```

Bu satırlar **İhsan'ın makinesinin** karne geçmişine ait bir dosyaya,
**başka bir makineden** yazıldı. (Geri alındı, hiçbir yere itilmedi.)

## Kök sebep

`_gecmise_yaz` yalnız **kısmi** koşumları eliyor:

```python
if r["gold_sayisi"] < TAM_SET:
    ...  # geçmişe yazılmaz
```

Docstring'in kendi dersi bunu zaten söylüyor — ama yanlış eksende:

> Testin üretim kanıtını kirletmesi başlı başına bir kusurdur.

Elenen şey **koşumun boyutu**. Elenmeyen şey **koşumun makinesi**. Tam
101 soruluk, tamamen geçerli bir karne, bambaşka bir veri kümesi ve
referans günü üzerinde koşulup aynı ekle-only günlüğe düşüyor. `İP-23`'ün
diliyle: cetvel değişmiş ama günlük bunu bilmiyor.

## Etkisi — ölçüldü, ve korktuğumdan hafif

`ip-46-cekirdek` üzerindeki `eval/karne_gecmisi.py` son iki kaydı
karşılaştırıyor. Yapay iki günlükle koşturuldu:

```
$ python3 eval/karne_gecmisi.py /tmp/kg-bulut.log
KARNE_GECMIS durum=kiyas_yok gold=101 mutant=239 yakalanan=199 (83.3%)
      mutant havuzu 306 -> 239 değişti; yakalama oranları doğrudan kıyaslanamaz.
cikis=0

$ python3 eval/karne_gecmisi.py /tmp/kg-ayni-havuz.log
KARNE_GECMIS durum=DUSUS gold=101 mutant=306 yakalanan=210 (68.6%)
cikis=1
```

Yani yabancı satır **yanlış alarm üretmiyor** — mutant havuzu farklı
olduğu için denetleyici `kiyas_yok` diyor ve çıkış kodu 0.

Bu iyi haber değil, sadece farklı bir kötü haber: **alarm yanlış ötmüyor,
hiç ötmüyor.** İhsan'ın bir sonraki koşumu kendi geçmişiyle değil yabancı
bir tabanla kıyaslanır, sessizce `kiyas_yok` alır ve o koşum için
regresyon nöbetçisi devre dışı kalır. Bir sonraki koşum yine kendi
çizgisine döner — yani zarar **tam olarak bir koşumluk kör nokta**.

Bu projenin sözlüğünde bunun adı var: her koşumda ateşleyen alarm alarm
değildir; **hiç ateşlemeyen alarm da alarm değildir.**

Kirlenmenin dala ulaşma yolu hayali değil: 2026-08-28'de bulut nöbeti
`docs/kanit`'i işleyip itmişti (`df0c989`). Aynı oturum karneyi koşsaydı
o satırlar da giderdi.

## Öneri (karar İhsan'ın — kanıt satırı biçimi § 3.5'e dokunur)

**Ö-a (önerilen).** `KARNE_OZET` satırına dayanıklı bir kaynak damgası
ekle (`makine=<kısa parmak izi>` ya da `veri=<olcum_gunu>+<mutant havuzu
özeti>`), ve `karne_gecmisi.py` **aynı damgalı son kayıtla** kıyaslasın.
Yabancı satırlar günlükte kalır (ekle-only bozulmaz) ama kıyası ele
geçirmez.

Maliyet düşük ve **ölçüldü**: `karne_gecmisi.ayristir()` bilinmeyen
alanları genel `anahtar=deger` döngüsüyle okuyup dizge olarak saklıyor —
yeni bir alan eklemek ayrıştırıcıyı **bozmuyor**.

**Ö-b.** `SORBI_KANIT_YAZMA=0` ortam değişkeni; bulut oturumları ve CI
bunu ayarlar. Basit, ama koruma yine bir ayarın hatırlanmasına bağlanır —
İP-30'da tam olarak bunun bedeli ödendi.

**Ö-c (bugünden itibaren geçerli, kararı beklemez).** Bulut nöbeti
`docs/kanit` altındaki hiçbir değişikliği işlemez ve oturum sonunda
`git checkout -- docs/kanit` ile geri alır. Bu oturumda yapıldı.

## Ders

**Bir kirlenme kaynağını kapatırken, aynı dosyaya yazan öteki kapıları
say.** İP-33 test kapısını kapattı ve doğru dersi yazdı; ama elediği şey
"küçük koşum"du, "yabancı koşum" değil. Ekle-only bir günlüğe yazma
hakkı, koşumun boyutuna değil **kime ait olduğuna** bakmalı.
