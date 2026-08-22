# Oturum günlüğü

Her oturum **en üste** bir giriş ekler. Amaç: bir sonraki oturumun nereden
devraldığını bilmesi. Silinmez, düzenlenmez — yalnız eklenir.

Biçim: ne yapıldı · ne ölçüldü · ne açık kaldı · sıradaki.

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
