# Bulgu kaydı

**Bir bulgu numarası YALNIZ burada verilir.** Başka hiçbir yerde numara
atanmaz; GUNLUK, BACKLOG, İP klasörleri ve nöbet raporları buraya bakar.

Neden var (BULGU-26, 2026-09-02): numaralar iki ayrı yerde, birbirinden
habersiz veriliyordu. `e168113`'ten sonra dallar ayrıldı ve **BULGU-21, 22
ve 24 aynı gün iki farklı şeye verildi.** Kaydedilen ama adı başkasının
olan bulgu, kaybolmuş bulgudur.

Kural: yeni bulgu → bu tablonun **sonuna** bir satır, sonra yaz.
Silinmez, numara geri dönüştürülmez.

| # | Konu | Durum | Nerede |
|---|------|-------|--------|
| 01–12 | v2/v3 erken bulguları | kapandı | `CHANGELOG.md`, BACKLOG |
| 13 | `SON-GECE-KOSUMU` damgası `git add`'den sonra yazılıyordu | kapandı | `gece-kosum.bat` |
| 14 | rapor dürüstlüğü | kapandı | `tests/test_rapor_durustlugu.py` |
| 15 | kimlik deposu ve araç çıktıları takip ediliyordu | kapandı | `edddb7c` |
| 16 | takılı `.git/index.lock` — hat beş gün sessizce kopuktu | kapandı | GUNLUK 2026-08-28 |
| 17 | *(kullanılmadı)* | — | — |
| 18 | cetvel fazla kolon döndüren doğru cevabı yanlış sayıyor | **açık — Review** | `v3/IP-34/BULGU.md` |
| 19 | dal/disk ayrışması (59 test yalnız diskteydi) | kapandı | `7472a5f` |
| 20 | nöbet raporunda ölçülmemiş sayı (`pytest 422`) | kapandı | GUNLUK 2026-08-31 |
| 21 | tazelik alarmı izlediği sürecin içinde | **açık** | `36-yama-2026-08-31.patch` (uygulanmadı) |
| 22 | süit iki özdeş koşumda farklı hüküm veriyor | kapandı | `36-yama-2026-08-31.patch` |
| 23 | *(boşaldı — çakışma çözümünde BULGU-30'a taşındı)* | — | — |
| 24 | gece koşumu dal körü — bir sonraki koşum v4'ü ölçüm dalına taşıyacaktı | kapandı | `bulgu/BULGU-24-gece-kosumu-dal-koru.md` |
| 25 | altın çiftlerde takvim çürümesi — `zaman-hafta` kendiliğinden kırmızı | kapandı | `bulgu/BULGU-25-altin-ciftlerde-takvim-curumesi.md` |
| 26 | bulgu numaraları iki yerde bağımsız veriliyordu | kapandı (bu dosya) | burası |
| 27 | bulut koşumu `KARNE-GECMIS.log`'a yazıyor — bir koşumluk kör nokta | **açık — Review** | `bulgu/BULGU-27-bulut-kosumu-karne-gecmisini-kirletiyor.md` |
| 28 | A-2 ön-doldurma: dolu alan, sorulmamış soru (`hasta.olay_tarihi = dogum_tarihi`) | kapandı | GUNLUK 2026-08-30 (öğleden sonra) |
| 29 | A-2: aşırı maskeleme körlük üretir (`bolum.ad`, `islem.ad` maskeleniyordu) | kapandı | GUNLUK 2026-08-30 (öğleden sonra) |
| 30 | A-2: anahtar kolonları boyut oldu (32 boyutun yarısı `*_id`) | kapandı | GUNLUK 2026-08-30 (öğleden sonra) |
| 31 | test kendi ön koşulunu yok ediyordu; çöp `.gitignore`'a eklenerek susturulmuştu | kapandı | GUNLUK 2026-08-30 (akşam) |
| 32 | süit nöbetçisinin kapsamı tek dizinde kalmış; `tests/cekirdek/` altındaki 6 `skipif` görünmüyordu | kapandı | GUNLUK 2026-09-02 (gece) |

## Çakışma nasıl çözüldü (2026-09-03, karar İhsan'ın)

Çakışan numaralar 21, 22 ve 24'tü: bir yanda `ip-46-cekirdek` üzerindeki
A-2/temizlik bulguları, öte yanda bulut nöbetinin hat bulguları.

**Karar: nöbet hattının numaraları kaldı, `ip-46-cekirdek` hattınınkiler
28–31'e kaydı.** Gerekçe kronoloji değil **maliyet** — nöbetin numaraları
yamaya, bu dosyaya ve dört proje belgesine gömülüydü; öbürleri iki GUNLUK
girişi ile bir proje belgesindeydi. Ucuz olan taraf taşındı.

| Eski | Yeni | Konu |
|---|---|---|
| 21 | **28** | A-2 dolu alan |
| 22 | **29** | A-2 aşırı maskeleme |
| 23 | **30** | A-2 anahtar boyutlar |
| 24 | **31** | test çöpü |

23 boşaldı ve boş kalıyor: numara geri dönüştürülmez.

> Bu dosya var olmadan önce numara vermek, iki dalın aynı anda aynı adı
> koyması demekti. Kayıt merkezîleşince çakışma **imkânsız** hâle gelmiyor
> — yalnız **görünür** hâle geliyor. Görünür olması yeterli: bir sonraki
> numara alınırken tablonun sonuna bakılır.
