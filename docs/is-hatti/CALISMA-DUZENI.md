# Çalışma düzeni — İhsan için

Bu belge teknik değil. Amacı: sen yokken neyin nasıl yürüdüğünü tek okumada
anlaman. Kurulan şey beş parçadan oluşuyor ve hepsi tek bir soruna çözüm:
**bilgi oturumlar arasında kayboluyordu.**

---

## Sorun neydi

Her yeni oturum sıfırdan başlıyordu. Hangi kararların alındığı, hangi
hataların zaten yapıldığı, sayıların ne anlama geldiği — hepsi ya sana
sorularak ya da yeniden keşfedilerek bulunuyordu. Bu hem zaman hem de risk:
bugün bulduğumuz "ADR yazıldı ama koda inmedi" hatası tam olarak böyle
oluştu.

---

## Kurulan beş parça

### 1. `CLAUDE.md` — kalıcı bellek

Depo kökünde. Her oturumun **ilk okuduğu** dosya. İçinde: projenin ne olduğu,
üç kapı, değişmezler, şu anki durum, alınmış kararlar ve **zaten yapılmış
hataların listesi**.

Bu son bölüm en değerlisi. Sekiz hata var ve hepsi gerçekten oldu. Yeni bir
oturum aynı tuzağa düşmeden önce onları okuyor.

### 2. Üç *skill* — "bu işi nasıl yaparız"

Belirli bir iş türü geldiğinde otomatik devreye giren yönergeler:

| Skill | Ne zaman | Ne yapar |
|-------|----------|----------|
| `olcum-al` | ölçüm, karne, "bu sayı ne demek" | Ölçüm öncesi kontrolleri, hangi sayının karşılaştırılabilir olduğunu, istatistiği doğru kullanmayı dayatır |
| `review-triyaj` | bir İP bitti | Senin triyaj edeceğin listeyi üretir — önerileriyle birlikte, boş tabloyla bırakmadan |
| `bulgu-ac` | plansız bir sorun | Bulgunun kaydedilmesini ve **tarifinin de doğrulanmasını** sağlar |

Üçüncüsü bir dersten doğdu: İP-16 haftalarca backlog'da yanlış tarifle durdu.

### 3. İki *alt ajan* — bağımsız göz

Bunlar ayrı çalışan, kendi bağlamı olan yardımcılar. İşi yapan kişi kendi
işini denetleyemediği için varlar.

- **`olcum-denetci`** — bir sayıya güvenmeden önce onu denetler. Sekiz
  kontrol: cetvel sağlam mı, doğru model mi koştu, GPU'da mıydı,
  karşılaştırma meşru mu, fark gürültü mü... Emin değilse **GEÇERSİZ** diyor.
- **`kirmizi-takim`** — güvenlik kapısını ve sessiz yanlış kontrollerini
  saldırgan gözle inceler. Kodun çalıştığını değil, nasıl kandırılabileceğini
  arar.

### 4. Üç *kapı* — otomatik denetim

Senin kararın: **kanıtı bozan şey durdursun, gerisi biriksin.**

| Kapı | Ne zaman | Ne yapar |
|------|----------|----------|
| Açılış | oturum başlarken | Son günlük girişini ve son karneyi ekrana basar — oturum yönünü bilerek başlar |
| Dosya | bir `.py` yazıldığında | `ruff` koşar, hata varsa **durdurur** |
| Kapanış | oturum biterken | ruff + değişmez testler; kırmızıysa **durdurur** |

Kapanış kapısı tam süiti koşmuyor, yalnız değişmez testleri: ADR-kod uyumu,
tarih sabitleme, doğrulama katmanı, güven kontrolleri. Sebebi basit —
60 saniyelik bir kapı, kapatılan bir kapıdır.

Bu kapılar bugün bulduğumuz üç hatanın **üçünü de** yakalardı.

### 5. Günlük nöbet — sen yokken

Her sabah otomatik bir oturum açılıyor, denetimi koşuyor, sapma varsa bulgu
açıyor ve `GUNLUK.md`'ye giriş bırakıyor. Sen açtığında birikmiş rapor seni
bekliyor.

**Nöbet üç kapıya dokunmaz.** Plan onayın, Review triyajın, Ship kararın
sende kalır. Nöbet ölçer, denetler, kaydeder — karar vermez.

---

## Günlük yapı

```
CLAUDE.md                          kalıcı bellek
.claude/skills/                    iş türüne göre yönergeler
.claude/agents/                    bağımsız denetçiler
.claude/hooks/kapi.py              otomatik kapılar
.claude/settings.json              kapıların ne zaman koşacağı
docs/is-hatti/GUNLUK.md            oturum günlüğü (ekle-only)
docs/is-hatti/CALISMA-DUZENI.md    bu belge
docs/kanit/                        ölçüm çıktıları (silinmez)
docs/kanit/KARNE-GECMIS.log        karnenin kendi geçmişi
```

---

## Komut yazmama düzeni

2026-08-21'de eklendi. İstek netti: *"her seferinde ben komut yazmak
istemiyorum."*

Kurulan döngü şöyle işliyor ve içinde senin bir adımın yok:

```
  03:00  senin makinen        gece-kosum.bat kendiliğinden koşar
         ├─ ruff, testler, gold sağlık, güven karnesi
         ├─ 101 soruluk ölçüm (Ollama açıksa)
         ├─ sonucu docs\kanit altına yazar
         └─ olcum-otomatik dalına iter

  ~03:05 GitHub               push CI'ı tetikler, yeşil/kırmızı sinyal oluşur

  07:00  bulut oturumu        o dalı çeker, geceki ölçümü okur ve yorumlar
         ├─ şüpheliyse olcum-denetci'ye GEÇERLİ/GEÇERSİZ dedirtir
         ├─ sapma varsa bulgu açar, dar kapsamlıysa düzeltir
         ├─ GUNLUK.md'ye giriş bırakır
         └─ telefonuna kısa özet düşer
```

Ölçüm senin makinende koşuyor çünkü GPU ve Ollama orada. Sonucu bana `git`
taşıyor; senin bir şey göndermene gerek yok.

**Nasıl kuruluyor:** `kur.bat` çalıştırdığında kendiliğinden kuruluyor.
Ayrıca bir şey yapmıyorsun.

**Neye dokunmuyor:** gece koşumu yalnız `docs\kanit` ve `GUNLUK.md`'yi
işliyor. Yarım kalmış çalışmana dokunmuyor, `master`'a hiç dokunmuyor;
ittiği yer ayrı bir dal.

**Kontrol etmek istersen:**

```
otomatik.bat /durum     son koşum ne zaman, ne oldu
otomatik.bat /simdi     zamanı beklemeden bir kez koş
otomatik.bat /kaldir    tümden kapat
```

**Kaçarsa ne olur:** bilgisayar kapalıysa o gece koşum olmaz, ertesi gece
devam eder. Bulut nöbeti dalı boş bulursa bunu bulgu olarak not eder — yani
sessizce kaybolmaz.

---

## Sen ne yapacaksın

Aslında daha az şey. Somut olarak üç şey:

1. **Bir kez `kur.bat`'a çift tıkla.** Gece koşumunu da o kuruyor.
   Bundan sonra komut yok.
2. **Review kapısında triyaj et** — `REVIEW.md` tablolarındaki kutular.
   Önerim her satırda yazılı; katılmıyorsan üstünü çiz.
3. **Ship kararını ver.**

Birinci madde bir kereliktir. Kalan ikisi zaten senin kapıların.

Bunların dışında bir şey sormam gerekmiyor. Bir karar gerçekten senin
olmalıysa sorarım; olmamalıysa sormam.

---

## Değiştirmek istersen

- Nöbetin saati ya da tümden kapatılması: söyle, ayarlarım
- Kapı sertliği (şu an: kanıtı bozan durdurur): söyle, değiştiririm
- Otonomi seviyesi (şu an: üç kapı sende, gerisi bende): söyle, daraltırım

Hiçbiri kalıcı değil; hepsi senin ayarın.
