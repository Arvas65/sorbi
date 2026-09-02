# v3 arşivi — tek seferlik betikler

Buradaki dosyalar **koşulmaz.** Bir kez işe yaradılar, işleri bitti, ama
silinmediler: her biri bir bulgunun kanıtı ve bir dersin kaynağı.

## `it.bat` · `it2.bat` — diskte bekleyen işi commit'lere bölen betikler

Yazıldıkları gün (2026-08-23, 2026-08-24) doğru şeyi yaptılar. Sorun,
**bittikten sonra hâlâ kök dizinde durmalarıydı.**

**BULGU-20 (2026-08-29):** `it.bat` yeniden çalıştırıldı. İçindeki dal adı
`ip-01-02-altyapi` olarak sabitti; o sırada çalışılan dal `ip-46-cekirdek`
idi. Adım 3'te hata verip durmasaydı `git push origin ip-01-02-altyapi`
komutunu çalıştıracaktı — **sessizce yanlış dala itiş.**

İki ayrı kusur:

1. **Pathspec'siz `git commit -m`.** Tamamen hazırlanmış bir indeksi
   olduğu gibi süpürdü ve 66 dosyalık, adı içeriğini anlatmayan bir
   commit üretti (`bf39faa`). İhsan `git reset --soft` ile açıp 7 temiz
   commit'e böldü.
2. **Kendini idempotent sanmak.** Başlığı "tekrar çalıştırılabilir" diyor
   ama 3–6. adımlar `|| goto :hata` ile bağlı; yarıda kalırsa geriye
   dönmüyor.

## Ders

> Tek seferlik bir betik, tek seferlik olduğunu **kendi başına bilmez.**

Bir dahaki sefere: tek seferlik iş `gece-gorev/` altına yazılır, koşulduktan
sonra `gece-gorev/bitti/` klasörüne taşınır. Kök dizin yalnız **tekrar tekrar
koşulan** betikleri taşır (`kontrol.bat`, `kur.bat`, `gece-kosum.bat`,
`otomatik.bat`, `gemini-kur.bat`, `parola.bat`, `yedekle.bat`).

Kök dizinde duran bir betik, bir gün yeniden çalıştırılır.
