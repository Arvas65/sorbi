# BULGU-24 — Gece koşumu dal körüydü; bir sonraki koşum v4'ü ölçüm dalına taşıyacaktı

**Bulan:** bulut nöbeti, 2026-09-02 · **Ağırlık:** ağır (gerçekleşmedi, önlendi)
**Durum:** **KAPANDI** — `eval/kanit_it.py` + 13 test · `gece-kosum.bat` § 4
**İlgili:** BULGU-13 (aynı betikte sıra hatası), BULGU-16 (aynı betikte git kilidi)

## Belirti

Henüz bir belirti yoktu. Bulgu, kanıt gelmeyen dört gecenin sebebi
aranırken **kod okunarak** çıktı — koşum gelseydi zararı o gece verecekti.

## Kök sebep

`gece-kosum.bat` § 4 şunu yapıyordu:

```bat
git add docs/kanit docs/is-hatti/GUNLUK.md
git commit -m "olcum: gece kosumu ..."
git push origin HEAD:refs/heads/olcum-otomatik
```

Üç varsayım vardı ve üçü de yazıldığı gün (2026-08-21) doğruydu:

1. HEAD bir ölçüm dalıdır,
2. çalışma ağacında ölçümden başka iş yoktur,
3. HEAD'i itmek yalnız kanıtı taşır.

**2026-08-29 22:19'da üçü birden düştü.** İhsan `ip-46-cekirdek` dalını açtı
(v4 çekirdeği; `olcum-otomatik`'in ucu `e168113`'e göre **68 dosya /
10.296 satır**). O dal ölçüm dalının **torunu**:

```
$ git merge-base --is-ancestor e168113 origin/ip-46-cekirdek && echo FF
FF
```

Yani bir sonraki başarılı gece koşumu:

- kanıt commit'ini İhsan'ın **özellik dalına** atacak,
- `HEAD:refs/heads/olcum-otomatik` push'unu **hızlı-ileri sarma** olarak
  **başarıyla** tamamlayacak,
- yarım kalmış v4 çalışmasının tamamını ölçüm dalına taşıyacaktı.

Push **reddedilmezdi.** Git tam olarak söyleneni yapardı. Bu, ürünümüzde
kovaladığımız sessiz yanlışın hat hâli: temiz çıktı, yanlış sonuç.

## Etkisi (ölçülmüş)

| | |
|---|---|
| Sızacak dosya | **68** |
| Sızacak satır | **10.296** (`docs/kanit` hariç) |
| Push'un reddedilme olasılığı | **yok** — hızlı-ileri sarma |
| Bulut nöbetinin fark etme yolu | dalı okurken v4 dosyalarını görmek — yani **sonradan** |

Yan etki: kanıt commit'i özellik dalının geçmişine karışır ve İhsan'ın
hazırladığı indeks (`git add` edilmiş yarım iş) commit'e girerdi.

### Bağımsız doğrulama (2026-09-03, yamayı uzlaştıran oturum)

İddia kabul edilmeden önce eski yol birebir kurulup koşuldu: çıplak uzak
depo, `olcum-otomatik` dalı, sonra ondan türeyen `ip-46-cekirdek` üzerinde
eski `git add + commit + push HEAD:refs/heads/olcum-otomatik` dizisi.

```
push cikis kodu : 0     <- reddedilmedi
kanit gitti mi  : True
V4 KODU SIZDI MI: True  <- app/cekirdek/anlam.py olcum dalinda
```

Sızma gerçek, sessiz ve `push`un çıkış koduna hiç yansımıyor.

## Çözüm

Dal **kontrol edilmedi** — bu yine bir varsayım olurdu ("beklediğim dal
listesi doğrudur"). Bunun yerine kanıt commit'i çalışma ağacının dalıyla
hiç ilişkilendirilmiyor. `eval/kanit_it.py`:

- ayrı indeks dosyası (`GIT_INDEX_FILE`) — İhsan'ın indeksine dokunulmaz,
- ağaç `origin/olcum-otomatik`'in **güncel tepesinden** okunur, HEAD'den değil,
- commit `commit-tree` ile doğrudan o tepeye çocuk yazılır,
- itilen şey commit'in **kendisidir**, HEAD değil.

Sonuç: HEAD nerede olursa olsun itilen şey yalnız kanıttır; push her zaman
hızlı-ileri sarmadır; çalışma ağacı, indeks ve HEAD **okunmaz bile**.

## Testler (13, `tests/test_kanit_it.py`)

Taklit git yok — kusur git'in gerçek hızlı-ileri sarma davranışından
doğmuştu, taklit edilen bir git bunu gösteremezdi. Her test çıplak bir
uzak depo + iki klon kurar ve gerçek `git push` çalıştırır.

Belirleyici olan: `test_ozellik_dalindaki_kod_uzak_dala_SIZMAZ` — eski kod
bu testi geçemez (yukarıda ölçüldü).

**Testin yakaladığı ikinci kusur:** ilk sürüm `git add <dizin>` kullanıyordu.
Git 2.0'dan beri bu **silmeyi de işler**; taban uzak daldan okunduğu için
yerelde bulunmayan her eski kanıt "silinmiş" görünüp uzaktan düşecekti —
kanıtın ekle-only olma kuralını (CLAUDE.md § 3.5) tam olarak onu koruyan
kod bozuyordu. `--ignore-removal` ile kapatıldı; `test_yerelde_silinen_
kanit_uzaktan_dusurulmez` bekçisi.

## Ders

**Bir betiğin "hangi dalda olduğumu bilmiyorum" hâli, yanlış dalda olmaktan
iyidir.** Doğru soru "doğru dalda mıyım" değil, "bu iş dala bakmadan
yapılabilir mi" idi — yapılabiliyordu.

CLAUDE.md § 7'ye satır olarak eklendi.
