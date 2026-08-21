# Oturum günlüğü

Her oturum **en üste** bir giriş ekler. Amaç: bir sonraki oturumun nereden
devraldığını bilmesi. Silinmez, düzenlenmez — yalnız eklenir.

Biçim: ne yapıldı · ne ölçüldü · ne açık kaldı · sıradaki.

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
