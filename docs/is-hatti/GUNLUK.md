# Oturum günlüğü

Her oturum **en üste** bir giriş ekler. Amaç: bir sonraki oturumun nereden
devraldığını bilmesi. Silinmez, düzenlenmez — yalnız eklenir.

Biçim: ne yapıldı · ne ölçüldü · ne açık kaldı · sıradaki.

---

## 2026-08-23 (gece nöbeti) — İkinci Gemini koşumu: fark yok, ama belirlenim de yok

**Koşum:** bulut, planlı görev · **Ölçüm okundu mu:** EVET · **Push yetkisi: YOK** (git proxy 403, üçüncü gece)
**Üç kapıya dokunulmadı.** Plan onayı, Review triyajı, Ship kararı İhsan'ındır.

### Önce bir düzeltme: bu ilk Gemini koşumu değil

Gece görevinin notu "bu gece ilk Gemini ölçümü" diyordu. Kanıt aksini söylüyor:
`gece-20260822-0300.log` → *"Standart kosum zaten API modunda - ikinci Gemini
olcumu atlandi."* Yani **08-22 koşumu da Gemini'ydi.** Bugünkü **ikinci** koşumdur.
Bunun iyi tarafı var: ADR-5 taslağının Ö-4 önkoşulu ("tekrarlanmış olmalı — tek
koşum gürültüdür") bu gece **kapandı.** G-12'nin ilk kez karşılanması da bu gece
değil; zaten dün gece de p95 3,76 sn'ydi.

### Ne ölçüldü — Gemini, api modu, 101 soru

| | 08-22 | 08-23 | hüküm |
|---|---|---|---|
| Doğruluk | %71,3 (72/101) | **%70,3 (71/101)** · Wilson GA **%60,8–78,3** | G-11 (%80) **karşılanmadı**, hedef aralığın dışında |
| p50 / p95 | 2,30 / 3,80 sn | **2,30 / 4,80 sn** | G-12 hakkında **hüküm yok** (aşağıya bak) |
| En yavaş soru | 7,90 sn | **12,40 sn** | 1 soru 10 sn'nin üstünde |
| Sessiz yanlış | 29 (%100) | **30/101 (%29,7), yanlışların %100'ü** | 0 soru reddedildi/patladı |
| Güven karnesi (gerçek hata) | 5/29 (%17) | **6/30 (%20)** · GA %9,5–37,3 | beklenen >%50 idi |
| Kota | aşılmadı | **aşılmadı** (çıkarımla) | ölçülmedi — aşağıya bak |

**Eşli karşılaştırma (ilk kez yapıldı).** `kontrol-*.log` soru bazlı satır taşıyor;
iki koşumun eşli tablosu oradan kuruldu. **7 soru cevap değiştirdi:** 4'ü
doğru→yanlış (#28, #39, #40, #100), 3'ü yanlış→doğru (#11, #36, #85).
**McNemar exact p = 1,000.** Net −1 soruluk fark **ölçülebilir bir fark değildir.**
Raporun yazdığı "−1,0 puan (gerileme)" ifadesi yanlıştır.

`olcum-denetci` hükmü: doğruluk sayısı **KOŞULLU GEÇERLİ**, "gerileme" nitelemesi
**GEÇERSİZ** · gecikme G-12 kanıtı olarak **GEÇERSİZ** · tekrarlanabilirlik
**GEÇERSİZ** · güven karnesi aritmetiği **GEÇERLİ**, mutasyon karnesinin öngörü
değeri **GEÇERSİZ** · kota **KOŞULLU GEÇERLİ**.

**Bulut klonunda LLM'siz denetim:** `git diff 884f8d9 HEAD -- ':(exclude)docs'`
**boş** — iki gecedir depoya tek satır kod girmedi. Dolayısıyla dün gecenin denetim
sonucu aynen geçerli; yeniden koşmak yeni bilgi vermezdi. Yeni yazılan 10 test
yeşil, ruff temiz.

### Bulgular

**[BULGU-08] api modunda belirlenim diye bir şey yok — damga aksini söylüyor. (ağır)**
`app/generator.py:160` `generate_api` isteği **yalnız `temperature` taşıyor;
`seed` ve `num_ctx` hiç gönderilmiyor** (ikisi de sadece Ollama yolunda). Ama damga
her koşumda `seed=42`, `num_ctx=8192` yazıyor. `config.py`'nin kendi yorumu
"A/B karşılaştırması yapabilmek için üretim önce TEKRARLANABİLİR olmalı" diyor;
api modunda o önkoşul **hiç sağlanmıyor** ve damga sağlanıyormuş gibi gösteriyor.
7 soruluk oynama bunun ölçülmüş sonucudur. Bu, "ADR'yi yazıp koda indirmemek"
hatasının aynası: **ayar koda inmiş ama isteğe inmemiş.**
*Yapıldı:* damgaya `belirlenim` alanı eklendi; api modunda "UYGULANMADI" yazıyor (2 test).

**[BULGU-09] Rapor gürültüyü "gerileme" diye etiketliyor. (orta — düzeltildi)**
`_fark_satiri` sıfırdan farklı her deltayı mekanik olarak iyileşme/gerileme diye
adlandırıyor. Kanıt raporun kendi içinde: p50 için **"+0.0 sn (gerileme)"**.
Sıfır puanlık farka gerileme diyen bir etiketleyici, bir puanlık farka dediğinde de
bir şey söylemiyor. *Yapıldı:* basılan hassasiyette sıfıra yuvarlanan fark artık
"değişmedi" diyor (2 test). **Kalan iş:** doğruluk farkı için eşli McNemar kapısı —
bu bir tasarım kararı, nöbet tek başına koymadı.

**[BULGU-10] SPEC A-4'ün regresyon kapısı gürültü tabanının altında. (orta)**
A-4 "3 puandan fazla düşerse CI kırmızı" diyor. Ölçülen api gürültü tabanı: koşumlar
arası **7 ayrık soru**. Saf gürültüde |net| ≥ 3 soru çıkma olasılığı ≈ **%45**.
Kapı, hiçbir şey olmadan ateşlenecek biçimde kalibre. Ya eşik ≥8 soruya çekilmeli
ya da tek koşum yerine aynı gece n≥3 koşumun soru bazlı oy çokluğu alınmalı.

**[BULGU-11] Dün gecenin BULGU-05'i yanlıştı — McNemar yapılabiliyor. (düzeltme)**
"`eval/results.json` gitignore'da, bulut nöbeti iki koşumu hiç eşli kıyaslayamaz"
denmişti. Soru bazlı veri **`docs/kanit/kontrol-*.log` içinde zaten var**
(`[nn/101] +/- (zorluk, join, sn) soru [asama]`) ve bu gece oradan kuruldu.
Damgalı bir `sonuclar-*.json` yine de iyi olur ama **engel değildi.**
Kendi bulgumu düzeltiyorum: eksik olan veri değil, veriyi arama işiydi.

**[BULGU-12] Test süiti kanıt günlüğünü kirletiyor. (küçük — İhsan'ın ağacında zaten düzeltilmiş)**
`tests/test_guven_olcum.py` her koşuşunda `docs/kanit/KARNE-GECMIS.log` dosyasına
`gold=0 alarm=0 mutant=0` diye sahte bir satır ekliyordu; depodaki `gold=3 mutant=3`
satırı da böyle oluşmuş. Karne "kendi geçmişiyle" karşılaştırıldığı için bu satırlar
referansa karışıyor — kanıt ekle-only olduğundan da temizlenemiyor.
*Durum:* İhsan'ın işlenmemiş ağacında `tmp_path`'e yazacak biçimde düzeltilmiş;
nöbetin yaması bu dosyaya dokunmadı.

**[BULGU-13] `SON-GECE-KOSUMU.txt` bir koşum geriden geliyor — kök sebep. (küçük — düzeltildi)**
Dün "bayat" denmişti (BULGU-07); sebebi bulundu. Dosya `gece-kosum.bat`'in **en
sonunda**, `git add`'den *sonra* yazılıyor. Diskte doğru, **itilen kopya her zaman
bir koşum geride.** Bulut nöbeti dün geceyi bu gece sanabilirdi.
*Yapıldı:* yazma adımı `git add`'in önüne alındı.

**[BULGU-14] Rapor başlığı "50 soruluk" diyor, ölçüm 101 soruluk. (küçük — düzeltildi)**
`eval/evaluate.py` sabit metin. *Yapıldı:* `ozet['n']` yazıyor (1 test).

**[BULGU-03 — düzeltmesi ikinci kez yazıldı ve bu kez uygulandı]**
Gecikme raporu bu gece de "Hedef (p95) 10 sn — **KARŞILANDI**" yazdı. G-12'nin metni
ve v3 SPEC A-3 hedefi *yerel çıkarım modu* içindir; bu koşum `mod=api`, yani ölçülen
şey Google'ın altyapısı + İhsan'ın ağı. Ayrıca gereksinim "**en geç** 10 sn" der;
1 soru 12,4 sn sürdü. **G-12 hâlâ ölçülmedi.** Geçerli tek sayı yerel koşumun
p95'i: 21,2–32,8 sn.
*Yapıldı:* `g12_kapsam_disi()` yazıldı — api modunda "KAPSAM DIŞI", hüküm
yok, sayılar yerinde; hedefi aşan tek tek sorular da yazılıyor (5 test).

**[BULGU-01/02 — üçüncü gece, hâlâ açık]**
Kod hâlâ itilmedi. `mask_context` (İP-30), kota koruması (İP-31), İP-26'nın
`karsilastirilamaz()` genişletmesi ve ~33 test **tek diskte.** Depodaki
`karsilastirilamaz()` yalnız `n` ve `olcum_gunu` denetliyor; raporun ürettiği
"farklı model" metni bu koddan çıkamaz — **koşan kod ile depodaki kod kanıtlanmış
biçimde farklı.** İki koşumun damgası da `(+islenmemis degisiklikler)`; o iki yığının
birbirinin aynı olduğunu gösteren hiçbir kanıt yok, dolayısıyla "iki gece aynı kodla
koştu" **doğrulanmamış bir varsayımdır.**

**[Düzeltme — "push yetkisi yok" teşhisi eksikti (2026-08-23, gündüz oturumu)]**
Nöbet raporları üç gecedir push'un engellendiğini yazdı. Bu yalnız *bulut kabı* için
doğru (git proxy 403). İhsan'ın makinesinde push çalışıyor: `gece-kosum.bat` her iki
gece de `[gece] push tamam: olcum-otomatik dali` yazdı ve `origin/olcum-otomatik`
güncel. Yani BULGU-01'in sebebi bir yetki sorunu değil — **kod hiç commit edilmemiş.**
`git status` 16 değişmiş + 5 takip edilmeyen dosya gösteriyor. Teşhis yanlış yere
bakıyordu; engel teknik değil, işlem.

### Ne açık kaldı

- **Kod hâlâ itilmedi (üçüncü gece).** Yama bu oturumda uygulandı ve testleri yeşil.
- İP-03c Review triyajı (8 madde) + BULGU-01…14 triyajı — İhsan'ın kapısı
- ADR-5 (İP-32) — Ship kapısı, karar bölümü boş
- ADR-3/ADR-4 dosyaları hâlâ yok; `config.py` yorumu "ADR-1/5" diyor ama ADR-5 depoda yok
- CI'ın ilk yeşil koşumu hâlâ doğrulanmadı

### Sıradaki

1. **İhsan:** `git add` + commit + push. Üç gecedir tek engel bu.
2. **İhsan — Ship kapısı:** ADR-5. Ö-4/Ö-5 kapandı; Ö-1, Ö-2, Ö-3 push ile kapanır; Ö-6, Ö-7 açık.
3. **Nöbette:** kod gelirse İP-30/31 doğrulanacak; mutant havuzunun gerçek hata
   dağılımına göre yeniden ağırlıklandırılması için öneri hazırlanacak.

---

## 2026-08-22 (akşam) — API modu hazırlandı, gizlilik açığı kapandı

**Neden:** yerel 7B modelin p95'i 32,8 sn (G-12 hedefi 10 sn) ve İhsan'ı yordu.
Ücretsiz Gemini anahtarı var. Karar değil, **ölçüm** yapılacak.

**En ağır bulgu — İP-30, gizlilik**
`generate_api` soruyu maskeliyordu ama **bağlamı olduğu gibi gönderiyordu.**
Bağlam, `ORNEK_DEGERLER` açıkken gerçek kolon değerlerini taşır: ünvanlar,
bölüm adları, şehirler. Docstring "veri değeri asla gitmez" diyordu; bunu
sağlayan tek şey bir ayarın hatırlanmasıydı. **Ürünün ana vaadi bir ayara
bağlıydı.** `mask_context()` yapısal hale getirdi. Gerçek bağlamla
doğrulandı: 868 → 612 karakter, sızan değer yok, şema duruyor.

**İP-31 — kota aşımı doğruluk kaybı gibi görünmeyecek**
Ücretsiz katmanda 429 normaldir. 101 sorunun 40'ı takılsa doğruluk %20
görünürdü. `KotaHatasi` ayrı tür; 429'da artan aralıklarla 4 deneme;
tükenirse `kota_asildi` diye ayrı sayılıyor ve rapor "karşılaştırma için
kullanılamaz" diyor. Yerel moda düşerek de gizlenmiyor.

**Yapılan**
- Gemini uyumluluk katmanı varsayılan: `generativelanguage.googleapis.com/v1beta/openai`,
  model `gemini-3.7-flash` (Ağustos 2026 itibarıyla güncel adlar doğrulandı)
- `--doctor` artık API modunda da **gerçek bir çağrı** yapıyor
- `SORBI_API_BEKLEME` — soru başına bekleme, hız sınırına takılmamak için
- `gece-gorev/02-gemini-olcumu.bat` kuyruğa alındı; anahtar yoksa atlıyor

**Ölçüldü**
- 351 test, ruff temiz
- Gerçek koşum yok — anahtar İhsan'da, ölçüm bu gece

**Açık**
- **İP-32: API modu ADR gerektiriyor.** Taban modeli API'ye taşımak "veri
  makineden çıkmaz" vaadini ürün düzeyinde değiştirir. Demo için sorun yok
  (veri sentetik), gerçek hastane müşterisi için ayrı karar — **Ship kapısı.**
- Köprü hâlâ düşük; kanıt kanalı git üzerinden yürüyor
- İP-03c Review triyajı, İP-28 num_ctx deneyi, İP-20/21/22

**Ek — gece koşumundaki tuzak (aynı akşam)**
İhsan Ollama'yı **bilerek** kapattı (Gemini kullanılsın diye). Bu,
`01-numctx-deneyi.bat`'te bir tuzağı ortaya çıkardı: doctor kontrolü yoktu,
Ollama kapalıyken 101 sorunun hepsi bağlantı hatası verip **sahte bir
çöküş** raporlayacaktı. Kapatıldı — num_ctx yalnız Ollama parametresidir,
yerel model yoksa ya da mod api ise deney kendini atlıyor. `02-gemini`
görevi de standart koşum zaten api modundaysa atlıyor (çift kota harcamasın).
`gemini-kur.bat` eklendi: anahtarı bir kez sorar, modu ayarlar, **gerçekten
çağırıp** doğrular.

**Sıradaki**
Bu gece üç koşum: standart yerel, num_ctx=4096, Gemini. Üçü de aynı cetvel
ve aynı test setiyle; farkları karşılaştırma kapısı denetleyecek.

---

## 2026-08-22 — İlk temiz ölçüm geldi, koruma sınavını geçti

**Ne oldu**
- `yedekle.bat` çalıştı: `ip-01-02-altyapi` dalı GitHub'da. Altı haftalık iş
  artık tek diskte değil. İP-25 kapandı.
- **Gece koşumu gerçekten çalıştı** (`GECE_KOSUMU zaman=20260821-2318 cikis=0`).
  Zincirin tamamı ilk kez uçtan uca döndü: zamanlayıcı → ölçüm → kanıt → push.

**İlk temiz ölçüm — 2026-08-22**

| | değer |
|---|---|
| Doğruluk | **%56,4** (57/101) |
| Sessiz yanlış | 42/101, yanlışların **%95,5**'i |
| p50 / p95 | 21,7 / 32,8 sn |
| Referans gün | `2026-07-23` (İhsan'ın verisinden türetildi) |
| num_ctx | 8192 |

**Koruma çalıştı.** Rapor 16 Ağustos'la karşılaştırmayı **reddetti**: "önceki
koşumda referans günü kayıtlı değil". Yani %62 → %56 bir gerileme olarak
raporlanmadı — çünkü öyle olduğunu bilmiyoruz. Bu koşum **yeni taban**.

**Üç yeni bulgu**
- **İP-26 — `karsilastirilamaz()` belgelenen kuralın yarısını uyguluyordu.**
  `olcum-al` skill'i model/sıcaklık/seed/num_ctx/değer-örnekleme farkını da
  karşılaştırma engeli sayıyor; kod yalnız `n` ve referans günü denetliyordu.
  İki koşum arasında num_ctx 4096→8192 değişmişti ve bu görünmüyordu. Referans
  günü de değişmeseydi 6 puanlık fark **gerçek bir gerileme gibi** raporlanacaktı.
  ADR-1'in koda inmemesiyle aynı aile: kural belgede, denetim kodda değil.
  Kapatıldı, 4 test.
- **İP-27 — commit damgası yalan söylüyordu.** İki koşum da `ffe5db3` damgası
  taşıyor, aralarında altı haftalık iş var — hiçbiri işlenmemişti. Damga artık
  çalışma ağacı kirliyse `(+islenmemis degisiklikler)` yazıyor.
- **İP-28 — gecikme %50 arttı** (p50 14,4→21,7). num_ctx 4096→8192 ile aynı
  koşuma denk geliyor ama iki değişken birden oynadığı için **nedensellik
  kurulamaz.** Tek değişkenli deney kuyruğa bırakıldı.

**Yeni mekanizma: gece görev kuyruğu**
`gece-gorev/` altına konan her `.bat` gece bir kez koşup `bitti/` altına
taşınıyor. Böylece bir deney için İhsan'dan bir şey çalıştırması istenmiyor;
iş gecenin sırasına bırakılıyor. İlk görev: `01-numctx-deneyi.bat` — aynı gün,
aynı model, aynı seed, yalnız num_ctx 4096.

**Açık**
- İP-03c Review triyajı (8 madde) — hâlâ İhsan'ın kapısı
- num_ctx deneyi (bu gece koşacak)
- BULGU-06: CI artık her dalda koşuyor; ilk yeşil koşum push ile tetiklenmiş
  olmalı — **doğrulanmadı**
- İP-20, İP-21, İP-22

**Ek — aynı akşam, İP-29**
`kur.bat` "gecti, ama DİKKAT edilecek noktalar var" dedi. Sebep: `kontrol.bat`
içindeki `BEKLENEN_TEST=320` sabiti; aynı gün 6 test eklenmiş, sayı 326 olmuştu.
Uyarı doğru çalışıyordu, **beklenti yanlıştı.** Bu hafta dördüncü kez aynı kalıp
(sabit referans günü, sabit karne sayıları, ADR'nin koda inmemesi, şimdi bu).
Sabit silindi; test sayısı artık kendi geçmişine karşı denetleniyor ve yalnızca
**düşüş** uyarı sayılıyor — artış ilerlemedir.

**Sıradaki**
Bu gece: standart koşum + num_ctx deneyi. Yarın sabah ikisi karşılaştırılabilir
olacak, çünkü tek değişken oynayacak.

---

## 2026-08-21 (sabah) — Uzak depo boş çıktı

**Yapıldı**
- Gece koşumunun sonucu arandı. Köprü iki kez cevap vermedi; tasarlanan ikinci
  kanal denendi: `git clone https://github.com/Arvas65/sorbi`.
- **Uzak depo 2026-07-25'ten beri hiç güncellenmemiş.** Yalnız `master` var ve
  içinde v3 işinin hiçbiri yok: `app/guven.py`, `eval/tarih_sabitle.py`,
  `eval/guven_olcum.py`, `CLAUDE.md`, `.claude/`, `.github/workflows/ci.yml`
  ve 12 test dosyası eksik. `olcum-otomatik` dalı da yok.
- **İP-25** açıldı. Bu benim tasarım hatam: git'i taşıyıcı kanal olarak
  kurgularken ön koşulunu (deponun itilmiş olması, kimlik doğrulamanın
  çalışması) hiç doğrulamadım. Bugünün beşinci "bir yerde geçerli olan başka
  yerde de geçerlidir" varsayımı.
- `yedekle.bat` yazıldı: tek çift tıklama ile yerel işi GitHub'a iter.
  Takılmış `.git/index.lock`'u temizler, kimlik doğrulama eksikse ne
  yapılacağını söyler.
- CI artık **her dalda** koşuyor (`branches: ["**"]`). Dal listesini daraltmak,
  ilk yeşil CI koşumunu "doğru dala push etmeyi hatırlamak" şartına
  bağlıyordu.
- Gece koşumunun push hatası artık sessiz değil: `docs/kanit/PUSH-SORUNU.txt`
  yazılıyor ve açılış kapısı onu basıyor.
- `.gitignore`: `_yedek/` ve `*.tar.gz` eklendi — kurulum yedeği depoya girmesin.

**Ölçüldü**
- 320 test, ruff temiz
- Gece koşumunun gerçekten çalışıp çalışmadığı **öğrenilemedi** — köprü kapalı,
  uzak depo boş. İki kanal da kapalıyken bunu bilmenin yolu yok.

**Açık**
- **İhsan'da tek iş: `yedekle.bat`.** O çalışana kadar hiçbir kanıt dışarı
  çıkamaz ve CI koşamaz.
- Gece koşumu gerçek Windows'ta hâlâ doğrulanmadı
- İP-03c Review triyajı (8 madde)
- İlk temiz ölçüm — qwen ile, sabit cetvelle
- İP-20, İP-21, İP-22

**Sıradaki**
`yedekle.bat` → depo dışarı çıkar → CI ilk kez koşar → BULGU-06 kapanabilir.

---

## 2026-08-21 (gece) — Komut yazma zorunluluğu kaldırıldı

**Yapıldı**
- İhsan: *"her seferinde ben komut yazmak istemiyorum"*. Döngü kuruldu:
  - `gece-kosum.bat` — kimsenin başında olmadığı koşum. Tuş beklemez,
    Notepad açmaz, sonucu `docs/kanit` altına yazar.
  - `otomatik.bat` — Windows Görev Zamanlayıcı'ya her gece 03:00 kaydı.
    `/durum`, `/simdi`, `/kaldir` alt komutları var. Yönetici hakkı gerekmez.
  - `kontrol.bat /sessiz` — etkileşimsiz mod. İnteraktif bir adım,
    zamanlanmış koşumu sonsuza kadar bekletirdi.
  - `kur.bat` artık otomatiği de kuruyor (adım 6/7) — İhsan'ın zaten çift
    tıklayacağı betik bu; ayrıca bir şey çalıştırması gerekmiyor.
- Sonuç `olcum-otomatik` dalına itiliyor. Yalnız `docs/kanit` ve `GUNLUK.md`
  işleniyor; yarım kalmış çalışmaya ve `master`'a dokunulmuyor.
- CI artık `olcum-**` dallarında da koşuyor → gece push'u yeşil/kırmızı
  sinyal üretiyor. **BULGU-06'nın (ilk yeşil CI koşumu) kapanması artık
  İhsan'ın bir şey yapmasına bağlı değil.**
- Bulut nöbeti (07:00) o dalı çekip geceki ölçümü okuyacak şekilde yazıldı.
- Açılış kapısı son gece koşumunu da basıyor.

**Bulgu — İP-24 (aynı gün açıldı ve kapandı)**
Teslim paketi `docs/kanit/KARNE-GECMIS.log` taşıyordu; kurulumda hedef
makinenin ölçüm geçmişini ezecekti — karnenin karşılaştırma tabanı tam olarak
o dosya. Bugünün diğer üç bulgusuyla aynı aile. İki yerden kapatıldı:
paketleme kuralı (`CLAUDE.md` §10) ve `kur.bat` içindeki kanıt koruması
(pakete güvenmez, `docs/kanit`'i açılan kopyadan siler).

**Ölçüldü**
- 320 test, ruff temiz, kapsam %80
- Kurulum ve kanıt koruması simüle edildi: eski `KARNE-GECMIS.log` ve
  `accuracy-*.md` yerinde kaldı, yeni katman tam geldi
- Kapılar bozuk dosya ve bozuk ADR ile ayrı ayrı denendi, ikisi de durdurdu

**Açık**
- **Doğrulanmadı:** gece koşumu gerçek Windows'ta hiç çalışmadı. `schtasks`
  kaydı, `/sessiz` modun gerçekten beklemediği ve `git push` yetkisi
  ilk gerçek koşumda görülecek. Bunlar bu kutuda test edilemez.
- İP-03c Review triyajı (8 madde) — İhsan'ın kapısı
- İlk temiz ölçüm — qwen ile, sabit cetvelle
- İP-20, İP-21, İP-22

**Sıradaki**
İhsan `kur.bat`'a bir kez çift tıklar. Gerisi kendiliğinden yürür.

---

## 2026-08-21 — Çalışma düzeni kuruldu, üç bulgu kapandı

**Yapıldı**
- İhsan'ın ilk temiz koşum log'u okundu, **üç bulgu** çıktı:
  - `config.LOCAL_MODEL` hâlâ `llama3.2:3b`'ydi; ADR-1 rev.2 qwen demişti.
    Ölçüm alınsaydı 24 puanlık hayali gerileme raporlanacaktı.
  - Referans gün sabit kodlanmıştı ve **benim** veritabanımdan geliyordu;
    İhsan'ın kopyasında 4 gereksiz bayrak üretti.
  - `kontrol.bat` de sabit sayı bekliyordu — aynı hata.
- Referans gün artık veriden türetiliyor (`veri_gunu()`), koşum zamana bağlı
  soruların boş dönüp dönmediğini kendisi denetliyor (`zbos`).
- `tests/test_adr_uyumu.py`: ADR-1'in "Karar" bölümü ile `config.LOCAL_MODEL`
  karşılaştırılıyor. Karar koda inmezse CI kırılıyor.
- Karne kendi geçmişiyle karşılaştırılıyor (`docs/kanit/KARNE-GECMIS.log`).
- **Çalışma düzeni kuruldu:** `CLAUDE.md`, üç skill, iki alt ajan, üç kapı,
  günlük nöbet. Ayrıntı: `docs/is-hatti/CALISMA-DUZENI.md`.

**Ölçüldü**
- Güven karnesi: yakalama %83,3 (199/239), gereksiz uyarı %1,0, `zbos=0`
- 320 test, ruff temiz, kapsam %80
- Doğruluk ve gecikme **ölçülmedi** — Ollama bu kutuda yok

**Açık**
- İP-03c Review triyajı (8 madde) — İhsan'ın kapısı
- Ollama'lı temiz koşum — qwen ile, ilk kez doğru modelle
- İP-20 (bayraklar denetim izine), İP-21 (sıfatla daraltılan sorular),
  İP-22 (İ düzeltmesinin ölçüm tekrarı)
- BULGU-06 **BLOK**: ilk yeşil CI koşumu olmadan `v2.4.0` yok

**Sıradaki**
`kontrol.bat tam` — artık doğru modelle ve sabit cetvelle koşuyor.
