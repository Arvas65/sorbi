# Oturum günlüğü

Her oturum **en üste** bir giriş ekler. Amaç: bir sonraki oturumun nereden
devraldığını bilmesi. Silinmez, düzenlenmez — yalnız eklenir.

Biçim: ne yapıldı · ne ölçüldü · ne açık kaldı · sıradaki.

---

## 2026-08-29 — v4 başladı: Kapı 1 onaylandı, İP-46 (çekirdek) yazıldı

**Kim:** bulut oturumu · **Kapı:** KAPI 1 geçildi (İhsan: ONAY).

### Yön değişikliği — kısa gerekçe

İhsan ürünü yeniden tarif etti: SorBı bir soruya bir tablo veren sistem değil,
**salt-okunur bir veritabanına yalnız şemasıyla bakıp Türkçe iş isteğini panoya
çeviren** bir motor olacak. Tetikleyen gözlem onun: *her veritabanı aynı
şablonda değil* — boy bir yerde kolon, başka yerde satır. Bu, text-to-SQL'in
tanımı gereği çözemeyeceği bir problem; çözüm **anlam katmanı**.

Belgeler: `docs/is-hatti/v4/` altında SPEC.md · PLAN.md · MIMARI.md ·
ADR-8 (model SQL yazmaz, seçim yapar) · ADR-9 (anlam modelinin saklanması).

### Yapıldı — İP-46

Yeni saf katman `app/cekirdek/`:

| Dosya | Ne | Satır |
|---|---|---|
| `tipler.py` | ortak değer tipleri, `Karar` enum'ı, `Toplama.yeniden_toplanabilir` | 169 |
| `anlam.py` | `AnlamModeli` + `dogrula()` + `yukle()` (kapalı devre) | ~360 |
| `secim.py` | `Secim.kur()` — sözlüğe karşı doğrulama; `to/from_json` (G-1) | ~240 |
| `portlar.py` | 6 Protocol: SemaKaynagi · Yurutucu · AnlamDeposu · Esleyici · Onbellek · Cizer | 140 |

Testler: `tests/cekirdek/` — **38 test, 0,11 sn, LLM'siz ve DB'siz.** Cetvel
Katman 1'in (SPEC F-1) altyapısı budur. `ruff` temiz.
Şema: `docs/is-hatti/v4/anlam-modeli.schema.json` (draft-2020-12; örnek model
şemaya karşı doğrulandı).

### Tasarım kararı — "cevaplanmadı" ile "cevabı yok" ayrı kodlanır

`gecerlilik = None` tek başına iki farklı anlama gelirdi: "bu tabloda iptal
kaydı yok" ya da "kimse sormadı". İkincisi eksen 8'in sessiz yanlışıdır. Bu
yüzden `Karar` enum'ı (`SORULMADI | VAR | YOK`) eklendi ve `SORULMADI` modeli
**geçersiz** yapıyor. Aynı ayrım değer sözlüğünde de uygulanıyor.

### Ölçüldü

`app/executor.py` ve `app/validator.py` okundu (İP-43 hazırlığı):
- `validator.py` gerçekten saf — yalnız `sqlglot` + `dataclass`. Çekirdeğe
  **tek satır değişmeden** taşınabilir. Kapalı devre sözleşmesi v4 mimarisinin
  şablonu oldu.
- `executor.py`: G-A doğrulandı (zaman aşımı ve salt-okunurluk yalnız SQLite'ta
  gerçek) **ve iki yeni bulgu:** (a) her çağrıda `create_engine` — Postgres'te
  pahalı, havuzlanmalı; (b) `MAX_ROWS` istemci tarafında (`fetchmany`), sunucuda
  `LIMIT` yok — 10M satırlık bir sorgu sunucuda yine de koşar. İkisi de İP-43
  kapsamına eklendi.

### Düzeltildi

SPEC taslak 1.0 anlam modelini `.sorbi/` altına koyuyordu. **Yanlıştı:** orası
sır dizini ve `.gitignore`'da (BULGU-15 mirası); sürümlenebilir olması gereken
bir belge oraya konamaz. ADR-9 §2a gerekçesiyle `anlam/` olarak düzeltildi;
SPEC revizyon 1.1 aldı.

İP sınırı notu: `Secim`in **veri tipi** İP-46'ya alındı (portlar ona tip olarak
ihtiyaç duyuyor, aksi hâlde döngüsel bağımlılık). Derleyici ve 40 altın çift
İP-47'de kaldı — kapsam değil, sıralama değişti.

### Aynı gün, ikinci tur — `kontrol.bat` kırmızıydı, sebebi İP-46 değildi

İhsan İP-46'yı `ip-46-cekirdek` dalına aldı ve `kontrol.bat` koştu:
`pytest 422 -> 460` (+38, yeni çekirdek testleri), gold 101/101. **ruff
BASARISIZ** çıktı ama 16 hatanın 16'sı da `tools/izdusum_denetimi.py`'de —
dün gece BULGU-18 için yazılan betikte. Çekirdek, İhsan'ın kendi ruff
ayarlarıyla (line-length 110, E/F/W/I/B/UP/S) temiz.

**Düzeltildi:** `tools/izdusum_denetimi.py` — E401/E701/E702/E402/I001
temizliği. Ayrıca bir belge-kod uyuşmazlığı: docstring `[sonuclar.json]`
argümanını anlatıyordu, kod dosya adını sabit tutuyordu. Artık gerçekten
argümandan okunuyor.

### BULGU-19 (ağır) — karne kontrolü her koşumda sahte alarm üretiyordu

`kontrol.bat:164` beklenen satırı şu sabitlerden kuruyor:
`BEKLENEN_GUN`, `BEKLENEN_ALARM`, `BEKLENEN_MUTANT`, `BEKLENEN_YAKALAMA`.
**Dördü de hiçbir yerde atanmıyor** (yalnız `BEKLENEN_GOLD=101` var ve o da
satıra sabit gömülü). Kurulan beklenen satır:

    KARNE_OZET gun= gold=101 alarm= mutant= yakalanan=

Gerçek satırla eşleşmesi **iki bağımsız sebeple** imkânsız: değişkenler boş,
ve şablonda `zbos=` alanı hiç yok. Yani kontrol 2026-08-24'ten beri her
koşumda "DIKKAT: beklenenden farkli" bastı. Her koşumda ateşleyen bir alarm
alarm değildir; okuyanı ona bakmamaya alıştırır.

Bu, 08-22 (ölü kod) ve 08-24 ("gerçek kontrole çevrildi") ile aynı kontrolün
**üçüncü** turu. Çare ise zaten yazılıydı: `eval/kosum_gecmisi.py`'nin
docstring'i *sabit karne sayılarını* aynı kalıbın örneği olarak sayıyor ve
çareyi söylüyor — "sabiti sil, ölçülen değeri kendi geçmişiyle karşılaştır."
Çare yazılmış, iki yerden yalnız birine (test sayısı) uygulanmıştı.
Dahası `docs/kanit/KARNE-GECMIS.log` her koşumda **yazılıyor** ve
`kontrol.bat` tarafından hiç **okunmuyordu**.

**Çare:** `eval/karne_gecmisi.py` (+ `tests/test_karne_gecmisi.py`, 10 test).
Karne kendi geçmişiyle karşılaştırılır; yalnız `yakalanan` DÜŞÜŞÜ uyarıdır.
Duman koşumları (gold=3) tam koşumla (gold=101) kıyaslanmaz — naif "son iki
satır" karşılaştırması her duman koşumundan sonra sahte alarm üretirdi.
Mutant havuzu değişince (239 -> 306 gerçekten oldu) sonuç "kıyas yok"tur,
gerileme değil.

`kontrol.bat`'ın 157–172 arası bloğu bunu çağıracak biçimde değiştirilmeli —
Windows batch bulut oturumunda sınanamadığı için İhsan'a snippet olarak
verildi, kör yazılmadı.

### İP-48 — pano derleyici (SPEC D-1)

`app/cekirdek/pano.py`: grafik tipini model seçmez, **seçimin şekli** seçer.
Şekil bilgisi sonucun kolon tiplerinden geri türetilmiyor — `Secim`de zaten
beyan edilmiş durumda (hangi ölçü, hangi boyut, hangisi tarih). Sonuçtan
alınan tek şey satır sayısı.

Kural sırası (özelden genele; ilk eşleşen kazanır):
boyutsuz tek sayı -> KPI · zaman+ölçü -> çizgi · zaman+kırılım -> çoklu çizgi
ya da küçük katlar · kategori+ölçü -> çubuk (>25 kategoride ilk 15 + diğer) ·
geri kalan -> tablo. **"Emin değilsem tablo"** bilinçli varsayılan: yanlış bir
grafik tablodan kötüdür, çünkü yanlış bir hikâye anlatır.

19 test; çekirdek toplamı 57, hâlâ 0,14 sn. Erişim testi `pano.py`'nin LLM
serbest metin alanlarına (`ham_cikti`, `netlestirme_sorusu`, `onerilen_olcu`)
hiç dokunmadığını AST üzerinden zorluyor; testin docstring'i neyi garanti
ETMEDİĞİNİ de yazıyor.

**SPEC'ten bilinçli sapma:** `claude/26` §04 ">200 satır -> tablo" diyordu.
Bu kural yalnız KATEGORİK tarafa uygulandı: üç yıllık günlük seri 1000
noktadır ve çizgi onu sorunsuz gösterir; tabloya düşürmek bilgi kaybı olurdu.
Kategorik tarafta sınır zaten "ilk 15 + diğer" ile kapanıyor.
Ayrıca çoklu çizgi eşiği bir **vekildir** (satır ≈ seri × zaman noktası);
modül veriye bakmadığı için seri sayısını bilemez. Yanıldığında bedeli
"çoklu çizgi yerine küçük katlar" — okunabilirlik tercihi, yanlış sayı değil.

### `kontrol.bat` — BULGU-19 çaresi uygulandı

157–172 arası blok, `python eval\karne_gecmisi.py` çağırıp çıkış koduna
bakacak biçimde değiştirildi. Ölü `set BEKLENEN_GOLD=101` kaldırıldı (hiçbir
yerde kullanılmıyordu). CRLF korundu (269/269 satır; `.gitattributes`
`*.bat text eol=crlf`).

Not: karne betiği (`eval/guven_olcum.py`) zaten "ÖNCEKİ KARNE: birebir aynı."
diye kendi karşılaştırmasını basıyormuş. Yani kapı, çalışan İKİ ayrı
karşılaştırmayı birden görmezden gelip hiç atanmamış sabitlere bakıyordu.

### İP-44 — oturum bağlamı (SPEC E-4, BLOK)

`app/akis/baglam.py`: `OturumBaglami` (değişmez değer) + `IndeksDeposu`
(anahtara göre önbellek, iş parçacığı güvenli, LRU sınırlı). Bağlantı artık
bir YAN ETKİ değil, bir DEĞER olarak taşınıyor.

Anahtar `db_url|lehce|v<anlam_surumu>` — **anlam sürümü anahtarın parçası.**
Sürümü dışarıda bırakmak, İP-23'ün cetvel çürümesinin önbellek tarafını
üretirdi: aynı anahtar, değişmiş anlam.

`baglam.py` `app/akis/` altında ama yalnız stdlib import ediyor: indeks üretimi
enjekte edilen bir fabrika (DIP). Bu sayede `sqlalchemy`/`chromadb` olmadan test
edilebiliyor — indeks kurmak pahalı olduğu için testin onu gerçekten kurmaması
zaten şart. 12 test; çekirdek toplamı 69, 0,18 sn.

`app/pipeline.py` yamalandı: modül düzeyi `_index` tekili kaldırıldı;
`get_index(baglam)`, `reset_index(baglam)`, `ask(..., baglam=None)`. Lehçe ve
veritabanı artık bağlamdan geliyor (4 + 3 nokta).

**Geriye dönük uyum bilinçli:** bağlamsız çağrı `varsayilan_baglam()` ile
config'ten türetiliyor ve davranış v3 ile birebir aynı. Yalıtım, bağlamı
AÇIKÇA veren çağıran için devreye giriyor. Böylece E-4 tek hamlede her yeri
değiştirmeden kapanabiliyor — arayüz tarafı (ui/ortak.py, sayfalar) hâlâ
bağlamsız çağırıyor ve **BLOK bu haliyle kapanmış SAYILMAZ**; mekanizma hazır,
kablolama ayrı bir adım.

### Yamanın kendi hatası — kayda geçirilmesi gerekiyor

Toplu `config.TARGET_DIALECT -> b.lehce` değiştirmesi, aynı betikte az önce
EKLENEN `varsayilan_baglam()` gövdesini de vurdu:

    return OturumBaglami(db_url=config.DB_URL, lehce=b.lehce)   # NameError

Sayım kontrolü (`count == 4`) değiştirmeden ÖNCE koşmuştu, ekleme 5.'yi
üretti. Yakalayan şey test değil, yamadan sonra yapılan AST denetimiydi:
"ask() dışında `b` adını kullanan satır var mı?". Ders: **üreten ve
değiştiren adımlar aynı geçişte olduğunda, sayım kontrolü değiştirmeden
sonra tekrarlanmalı.** Bu bir uyarı olarak §7 hata tablosuna aday.

### BULGU-20 (ağır) — `it.bat` bugün koşarsa YANLIŞ DALI iter ve "başarılı" der

`it.bat` 2026-08-23 gecesi için yazılmış **tek kullanımlık** bir betik: commit
kırılımı, dosya yolları ve mesajları o geceye ait. Bugün koşuldu ve 3. adımda
düştü. Düşmesi iyi oldu — çünkü geçseydi son satırı şuydu:

    git push origin ip-01-02-altyapi

Yürürlükteki dal `ip-46-cekirdek`. `ip-01-02-altyapi` hem yerelde hem uzakta
DURUYOR, dolayısıyla bu komut hata vermez: eski dalı iter, "Everything
up-to-date" ya da benzeri bir başarı basar ve **İP-46/48/44 itilmemiş olarak
kalır.** BULGU-01'in (2026-08-23: "push yetkisi yok sanıldı, aslında commit
hiç yapılmamıştı") tam kardeşi: başarısız olmayan, hiç denenmeyen bir push.

İkinci kusur: betiğin kendi hata iletisi *"yapılmış adımlar 'commit edilecek
bir şey yok' deyip geçecek"* diyor, ama 3–6. adımlar `|| goto :hata`
kullanıyor, yalnız 2 ve 7 `|| echo`. **Metin idempotans vaat ediyor, kod
etmiyor.** Karne kontrolüyle aynı aile: söz belgede, uygulama yok.

Üçüncüsü: 1. adımın `git commit -m "gitattributes: ..."` komutu, bir önceki
turda `git add .` ile hazırlanmış TÜM indeksi süpürdü. Sonuç `bf39faa`: 66
dosya, 7065 satır — v4'ün çekirdeği, ADR'ler, SPEC, PLAN, MIMARI, daha önce
hiç commit edilmemiş 6 test dosyası ve `tools/` araçları, hepsi
"gitattributes" başlıklı tek bir commit'te. `git commit -m` yol belirtmezse
indeksin tamamını alır; adımın dar görünmesi onu dar yapmıyor.

Not: o 66 dosyanın içinde `tests/conftest.py`, `tests/test_audit_guven.py`,
`tests/test_guven_b7r.py`, `tests/test_regresyon_kapisi.py`,
`tests/test_suit_dururlugu.py`, `tests/test_depo_hijyeni.py` ve
`tools/parola_degistir.py` vardı — yani **çalışan ama depoda olmayan** testler.
Çalışma ağacı ile depo arasındaki kayma bir kez daha ölçüldü.

**Karar önerisi:** `it.bat` ve `it2.bat` tek kullanımlıktır ve işleri bitti;
`docs/is-hatti/v3/arsiv/` altına taşınmalı. Genel bir "it" betiği yazılacaksa
push hedefi **yürürlükteki daldan** alınmalı (`git rev-parse --abbrev-ref HEAD`),
sabit yazılmamalı.

### Açık kaldı

- **BULGU-15** — admin parolası hâlâ uzak depo geçmişinde. İhsan'ın işi.
- Bu oturumda yazılan dosyalar **commit edilmedi**: bulut oturumu bağlı klasörde
  git komutu çalıştırmıyor (§7). Dosyalar çalışma ağacında duruyor.
  `git checkout -b ip-46-cekirdek && git add app/cekirdek tests/cekirdek docs/is-hatti/v4`
- `pytest` bu makinenin Linux VM'inde kurulu değil; kabul kontrolleri düz Python
  3.10.12 ile koşturuldu, **7/7 geçti**. Tam süit İhsan'ın Windows venv'inde
  `kontrol.bat` ile koşulmalı.

### Sıradaki

- **İhsan:** İP-43 (yürütücü sözleşmesi) ve İP-47 (derleyici) — eleştirel yolda.
- **Claude:** İP-48 (pano derleyici) ve İP-44 (oturum bağlamı) — İP-46'ya bağlı,
  başlanabilir.

---

## 2026-08-28 — Hat beş gündür sessizce kopuktu: takılı `.git/index.lock`

**Kim:** bulut oturumu · **Kapı:** yok — onarım, yeni iş paketi değil.

### Bulgu (BULGU-16, ağır)

`.git/index.lock` **2026-08-23 16:06'dan** beri diskte duruyordu. Sonucu:
`gece-kosum.bat` her gece **ölçümü doğru koştu** ama `git add` adımı
`fatal: Unable to create ... index.lock` ile düştü, `[gece] islenecek yeni
kanit yok` yazıp çıktı. `olcum-otomatik` dalı **20260823-0300**'de dondu;
bulut nöbeti beş gün boyunca beş günlük eski bir dalı okuyordu ve bunu
fark edemedi — çünkü push hiç *başarısız* olmadı, hiç *denenmedi*.

`PUSH-SORUNU.txt` bayrağı yalnız push düşerse yazılıyor. Buradaki hata
push'tan önceydi; yani hattın kendi alarmı bu arızayı kapsamıyordu.

**Kök neden — ders:** kilidi bırakan büyük olasılıkla *bulut oturumunun
kendisiydi*. Bağlı klasörde `rm`/`unlink` yasak; git kendi kilit ve
`tmp_obj_*` dosyalarını **silemiyor**, "Operation not permitted" alıyor ve
kalıntıyı bırakıyor. Bu oturumda bir `git commit` + bir `git status` ile
34 kalıntı üretildi ve elle taşınarak temizlendi.

> Bu, §7'deki ortak paydanın bir örneği daha: *bir yerde geçerli olanın
> başka yerde de geçerli olduğunu varsaymak.* Git, Windows'ta çalıştığı
> gibi bağlı-klasör montajında çalışmıyor.

**Kural (bulut oturumları için):** bağlı klasörde yazan git komutu
çalıştırma. Okuma için `git --no-optional-locks <komut>`. Zorunluysa
komuttan sonra `find .git -name '*.lock' -o -name 'tmp_obj_*'` boş
dönene kadar temizle.

### Yapıldı

- Takılı kilit ve 34 git kalıntısı `_to_delete/git-kalinti/` altına taşındı
  (silme izni yok; İhsan klasörü silebilir).
- **BULGU-15 kalıntısı:** `.sorbi/connections.json` hâlâ takip ediliyordu —
  `git rm --cached` ile çıkarıldı (`edddb7c`). Dosya **boş** (`{}`), sızan
  bir sır yok; kapatılan şey sızabileceği yer. `.sorbi/` zaten
  `.gitignore`'daydı ama takipteki dosyayı ignore kapsamaz.
  Bu, `test_depo_hijyeni`'nin 08-23'ten beri her gece raporladığı tek
  başarısız testti — süit yeşil değildi, kimse okuyamıyordu.
- 08-23/08-27/08-28 kanıtları işlendi (`df0c989`). **Push edilmedi**;
  bu gece 03:00 koşumu iter.

### Ölçüldü

Yeni ölçüm koşulmadı. Diskte duran ama işlenmemiş olan iki koşum:

| Gün | Model | Acc | Sessiz yanlış | p95 | Kapı |
|-----|-------|-----|---------------|-----|------|
| 08-27 | `gemini-3.7-flash` (api) | %69,3 (70/101) | 31 (%100) | 3,7 sn | — |
| 08-28 | `gemini-3.7-flash` (api) | %71,3 (72/101) | 29 (%100) | 4,2 sn | FARK YOK (McNemar p=0,688) |

08-24, 08-25, 08-26 gecelerinde **hiç koşum kaydı yok** (gece log'u
üretilmemiş) — makine kapalıydı sanılıyor, doğrulanmadı.

### Açık kalan

- **Ship kapısı: ADR-5 karar bölümü hâlâ boş.** Gece koşumu 08-22'den beri
  `mod=api` ile ölçüyor; yani karar verilmemiş bir moda ait sayılar
  birikiyor. Ayrıca bu modda **belirlenim mümkün değil** (uç nokta `seed`
  tanımıyor, HTTP 400) — kanıt damgası bunu yazıyor.
- Hattın "sessiz kopukluk" alarmı yok: push denenmediğinde hiçbir bayrak
  yazılmıyor. Öneri (İP adayı): `SON-GECE-KOSUMU.txt` damgası N gündür
  ilerlemiyorsa `kontrol.bat` açılışta bunu bağırsın.
- Çalışma ağacında 24 dosyalık işlenmemiş değişiklik duruyor (08-23
  oturumundan). Dokunulmadı.

### İP-34 açıldı (B-7) — ve ilk iş kontrol yazmak değil

İhsan B-7'yi seçti. İlk bakışta iş belliydi: sessiz yanlışın yalnız %21'i
bayraklanıyor, yeni kontrol yaz. Kaçan 22 vaka tek tek okununca cetvelde
bir şey çıktı — **BULGU-18**, ayrıntısı `v3/IP-34/BULGU.md`:

`_normalize` satırı sonucu bütün olarak karşılaştırıyor; fazladan bir kolon
koyan doğru cevap yanlış sayılıyor. 29 yanlışın **9'u** bu (08-27'de 8).
Kolon-toleranslı sayımla accuracy %71,3 → %80,2, sessiz yanlış 29 → 20,
B-7 %21 → %30.

**G-11 karşılandı demek değildir** (Wilson GA %71–87, eşik içeride) ve 17
vaka gerçekten yanlış. Ama şu kesin: o dokuz vakayı yakalayacak kontrol
yazsaydık **doğru cevabı bayraklayan** kontrol yazmış olurduk. Payda
doğrulanmadan kontrol yazılmaz.

Öneri § 6'da: cetveli değiştirme, `dogru_toleransli` diye ikincisini ekle,
rapor iki sayıyı birden yazsın. Karar İhsan'da — cetvel politikası SPEC'e
dokunur.

Eklenen: `tools/izdusum_denetimi.py` (ölçer, karar vermez).

### Sıradaki

Bu gece 03:00 koşumunun çıkış kodunu ve `olcum-otomatik` dalının
ilerlediğini doğrula.

---

## 2026-08-23 (gündüz) — İP-33: triyaj uygulandı, karne dürüstleşti

**Kim:** bulut oturumu · **Kapı:** yok — Review triyajı İhsan'da tamamlandı,
bu giriş onun kararlarının uygulanmasıdır.

### Karar

İhsan 24 maddelik triyajı verdi: 15'i zaten kapanmıştı, **açık 16 maddenin
tamamı DÜZELT.** Nöbetin önerdiği 6 KABUL/SONRA da DÜZELT'e çevrildi.

### Yapıldı

**Süit artık sessizce atlamıyor (BULGU-N4).** `tests/conftest.py` içe aktarma
anında tohumluyor; `skipif` ve koşullu `pytest.skip` üç dosyadan silindi.
`demo/*.db` silinmiş hâlde süit: **415 geçti, 0 atlandı.** Öncesinde çoğu test
atlanıyor ve pytest yine çıkış kodu 0 veriyordu — kovaladığımız sessiz yanlışın
cetveldeki hâli. `test_suit_dururlugu.py` geri gelmesini kilitliyor.

> 08-22 nöbeti bunu "kapandı" diye yazmıştı. Değildi: o yama kaybolan
> yamalardan biriydi. Kapandığı SÖYLENEN bir bulguyu depoya karşı
> doğrulamamak, bu turda iki kez karşımıza çıktı.

**Karne dürüstleşti (B7R-08 / BULGU-04).** Mutant havuzuna gerçek model
hatasına benzeyen dört aile eklendi — `deger_takasi` (filtreyi AYNI kolonun
BAŞKA geçerli değeriyle değiştir), `karsilastirma`, `distinct_dus`,
`join_ici_disi`. Havuz 239 → 306. Yakalama **%83,3'ten %72,5'e düştü** ve
düşüş iyi haberdir: %83'ün bir kısmı havuzun kolaylığından geliyordu.

Sonra iki yeni kontrolle yakalayarak geri çıkıldı:

```
başlangıç      199/239   %83,3    kolay havuz
B7R-03/06      212/239   %88,7    aynı havuz
havuz büyüdü   222/306   %72,5    DÜRÜST havuz
yeni kontrol   245/306   %80,1
```

Gereksiz bayrak **baştan sona 1/101 (%1,0)** — hiçbir düzeltme yanlış alarmla
ödenmedi.

**Yeni kontroller.** `deger_uyumsuz`: soru bir değerden söz ediyor, sorgu
başka bir geçerli değerle filtreliyor — sonuç dolu, tablo makul, sayı yanlış
(gerçek model hatasının şekli). `distinct_eksik`: "kaç FARKLI hasta"
sorusuna `COUNT(*)`. Sırasıyla %21 → %74 ve %0 → %36.

**Regresyon kapısı gürültünün dışına çıktı (BULGU-09/10).** SPEC A-4'ün
"3 puan" eşiği ölçülen gürültü tabanının altındaydı: saf gürültüde ateşleme
olasılığı ≈ %45. Kapı artık eşli McNemar kararına bağlı —
`bozulan - düzelen >= 3` **ve** `p < 0,05`. Ölçülen gerçek gürültü (4 bozuldu,
3 düzeldi) kapıyı açmıyor; 12/0 açıyor. Testlerle kilitli.

**Belirlenim (BULGU-08).** `seed` artık api isteğine gerçekten konuyor ve
damga metni **koddan türetiliyor** — isteğin alan listesi değişirse damga
kendiliğinden düzelir. Ama damga hüküm vermiyor: göndermek uygulanmış olmak
değildir, sunucu seed'i yok sayabilir. Bunu ancak tekrarlanmış koşum gösterir.

**[BULGU-17] `seed` eklemek API'yi kırdı — ve ADR-5'e kanıt oldu.**
BULGU-08 düzeltmesi (`seed` isteğe konuyor) itilmeden önce `kontrol.bat` ile
denendi ve uç nokta isteği **tümden reddetti:**

```
HTTP 400  Invalid JSON payload received.
          Unknown name "seed": Cannot find field.
```

Gemini'nin OpenAI uyumluluk katmanında `seed` diye bir alan yok. Yani api
modunda belirlenim "doğrulanmamış" değil — **bu sağlayıcıda mümkün değil.**
*Yapıldı:* `seed` gönderiliyor; uç nokta tanımıyorsa bir kez alansız tekrar
deneniyor ve bu oturum boyunca hatırlanıyor (her soruda kayıp istek yok).
Damga artık ne gönderdiğimizi değil, uç noktanın ne KABUL ETTİĞİNİ yazıyor.
`SORBI_API_SEED=0/1/auto` ile elle ayarlanabilir; varsayılan `auto`.
**ADR-5 Ö-7 artık "kısmen" değil, "bu uç noktada KAPANAMAZ".**

> Ders: düzeltmeyi ölçmeden itmek, düzelttiğini sandığın şeyi bozmak olabilir.
> Bu kez `kontrol.bat` yakaladı — çünkü İhsan onu koşturdu.

**Denetim izi (B7R-05).** Güven kodları `denetim.guven_kodlari`'na yazılıyor
(yerinde göç; ekleme-yalnız kayıt korunuyor). `audit.guven_karnesi()` ile
saha sayımı — B-7'nin saha karnesi artık tahmin edilmeyecek, sayılacak.

**Ayrıca:** damgalı `sonuclar-*.json` (BULGU-05) · "yakalanan" → "reddedilen"
terim ayrımı (BULGU-06) · soru bazlı mod kaydı (YENİ-C) · ADR-3/4 yazıldı,
ADR-5 taslağı depoya indi (YENİ-A) · `.gitignore` + depo hijyeni testleri
(BULGU-15) · CI'a LLM'siz B-7 karnesi.

### Ölçüldü

```
pytest tests/     415 geçti, 0 atlandı  (öncesi 363)   demo/*.db SİLİNMİŞ hâlde
ruff check .      temiz
kapsam            %79,0  (eşik %70)
guven_olcum.py    gold=101 alarm=1 mutant=306 yakalanan=245 (%80,1)
```

### Ölçülmedi — dolayısıyla iddia edilmiyor

- Yeni kontrollerin **gerçek model hatalarındaki** karnesi. %80,1 bir
  MUTASYON sayısıdır; saha sayısı bir sonraki 101'lik koşumda çıkar.
- `seed`'in sunucuda uygulanıp uygulanmadığı.
- Güvenlik kapılarının canlı doğrulaması (kapsam dışıydı).

### Açık — İhsan'da

1. **Admin parolasını döndür** (BULGU-15). Hash `884f8d9`'de, uzak depo
   geçmişinde. Takipten çıkarmak onu silmez. Depo açıksa bu **BLOK**.
2. **CI'ın ilk yeşil koşumu** (YENİ-B). Bu push CI'ı gerçek kodla tetikleyen
   ilk push.
3. **ADR-5 Ship kararı.** Ö-1/2/3 bu İP'te kapandı; Ö-6 ve Ö-7 açık.

### Sıradaki

Nöbette: bir sonraki 101'lik koşumda `deger_uyumsuz` ve `distinct_eksik`'in
saha karnesi raporlanacak; `join_ici_disi` ailesi için daha çok JOIN'li gold
sorgusu gerekiyor (havuzda 1 mutant üretiyor, o sayı bir şey ölçmüyor).

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
