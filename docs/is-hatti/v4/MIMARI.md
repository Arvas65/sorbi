# SorBı v4 — Mimari

**Sürüm:** taslak 1.0 · **Tarih:** 2026-08-28 · **Karar sahibi:** İhsan Arvas
**Durum:** PLAN'ın eki — onay Kapı 1'de · **İlgili:** ADR-8, ADR-9, v4 SPEC

> Bu belge "nasıl yazılacağını" tanımlar. Ne yazılacağı SPEC'te, hangi sırayla
> yazılacağı PLAN'da. Buradaki her kural, bu depoda **gerçekten olmuş** bir
> hataya dayanıyor; soyut ilke yok.

---

## 1. Tasarım sürücüleri

Üç tane. Sıralamaları önem sırasıdır ve çatıştıklarında üstteki kazanır.

| # | Sürücü | Nereden geliyor |
|---|--------|-----------------|
| 1 | **Sessiz yanlış üretilemesin** | Ölçüm: yanlışların %95–100'ü sessiz. Ürünün varlık sebebi bu |
| 2 | **Değiştirilebilirlik** — "bir yeri atlarsak güncelleyip değiştirebilelim" | İhsan, 2026-08-28. Birinci sınıf gereksinim, sonradan eklenen bir güzellik değil |
| 3 | **Ölçülebilirlik** — her katman tek başına, LLM'siz sınanabilsin | SPEC F-1: cetvel Katman 1 saniyeler içinde koşmalı |

Üçü de aynı yapısal cevabı veriyor: **stokastik parçayı küçült, etrafını saf ve
deterministik yap, sınırları Protocol ile çiz.**

---

## 2. Katmanlar ve bağımlılık yönü

Altıgen (ports & adapters) yerleşimi. **Bağımlılık oku her zaman içeri bakar.**

```
             ┌──────────────────────────────────────────────┐
             │  ARAYÜZ    Streamlit sihirbaz · pano ekranı  │
             └───────────────────┬──────────────────────────┘
                                 │
             ┌───────────────────▼──────────────────────────┐
             │  AKIŞ (use-case)   etiketle() · sor()        │
             │  bağlama burada yapılır, açıkça              │
             └───┬───────────────┬──────────────┬───────────┘
                 │               │              │
        ┌────────▼─────┐ ┌───────▼──────┐ ┌─────▼────────┐
        │  ÇEKİRDEK    │ │  ÇEKİRDEK    │ │  ÇEKİRDEK    │   saf:
        │  anlam       │ │  derleyici   │ │  pano+güven  │   IO yok
        │  secim       │ │  validator   │ │              │   LLM yok
        └──────────────┘ └──────────────┘ └──────────────┘   DB yok
                 ▲               ▲              ▲
                 │      portlar (Protocol)      │
        ┌────────┴───────────────┴──────────────┴───────────┐
        │  BAĞLANTI (adapters)                              │
        │  SqliteSemaKaynagi · PostgresSemaKaynagi          │
        │  SqliteYurutucu · PostgresYurutucu · MysqlYurutucu│
        │  DosyaAnlamDeposu · BellekOnbellegi               │
        │  OllamaEsleyici · ApiEsleyici                     │
        └───────────────────────────────────────────────────┘
```

**Kural:** `app/cekirdek/**` hiçbir şey import etmez — stdlib, `dataclasses`,
`typing` ve `sqlglot` dışında. `sqlglot` istisnası bilinçli: saf bir ayrıştırıcı,
IO yapmaz. Bu kural bir **testle zorlanır** (§6, D maddesi).

---

## 3. Portlar

Bir soyutlamanın port olması için ölçüt: **ikinci uygulaması ya bugün var, ya
SPEC'te yazılı.** "Her ihtimale karşı arayüz" aşırı mühendisliğin en yaygın
biçimidir; aşağıdaki her portun gerekçesi yanında.

```python
# app/cekirdek/portlar.py
from typing import Protocol

class SemaKaynagi(Protocol):
    """Ham şema okuma — SİHİRBAZIN girdisi.
    Gerekçe: sqlite + postgres (SPEC H-1).
    Not: `farkli_degerler` veri DEĞERİ döndürür ve bu değerler yalnız
    sihirbaz ekranına, yani İNSANA gider (SPEC A-4). Bu portu Yurutucu'dan
    ayrı tutmak kozmetik değil — Sınır 1'i arayüz düzeyinde uygular."""
    def tablolar(self) -> list[TabloSemasi]: ...
    def iliskiler(self) -> list[Iliski]: ...
    def farkli_degerler(self, tablo: str, kolon: str, limit: int) -> list[str]: ...
    def satir_sayisi(self, tablo: str, kosul: str | None = None) -> int: ...

class Yurutucu(Protocol):
    """Salt-okunur çalıştırma.
    Gerekçe: sqlite + postgres + mysql + mssql (SPEC E-3).
    SÖZLEŞME (LSP): her uygulama zaman aşımını VE salt-okunurluğu GERÇEKTEN
    uygular. Uygulayamayan bir sürücü için uygulama yazılmaz — v3'ün G-A
    hatası tam olarak bu sözün sessizce zayıflatılmasıydı."""
    def calistir(self, sql: str, zaman_asimi_sn: int, azami_satir: int) -> Sonuc: ...
    def yazma_denemesi(self) -> bool: ...    # True = hesap yazabiliyor → riskli

class AnlamDeposu(Protocol):
    """Anlam modelinin kalıcılığı (ADR-9).
    Gerekçe: bugün tek uygulama (dosya), ama ADR-9 §6 başka bir deponun
    çağıran kodu değiştirmeden devralabilmesini gerektiriyor."""
    def oku(self, baglanti: str) -> AnlamModeli | None: ...
    def yaz(self, model: AnlamModeli) -> int: ...      # yeni sürüm numarası
    def gecmis(self, baglanti: str) -> list[int]: ...

class Esleyici(Protocol):
    """soru + sözlük -> Secim. Hattın TEK stokastik parçası (ADR-8).
    Gerekçe: ollama + openai-uyumlu api (ADR-5 = B).
    SÖZLEŞME: istisna fırlatmaz; başarısızlık `EslemeSonucu.hata` ile döner."""
    def esle(self, soru: str, sozluk: Sozluk) -> EslemeSonucu: ...

class Onbellek(Protocol):
    """Sonuç önbelleği — Sınır 2'nin tek meşru veri barınağı.
    Gerekçe: bellek içi bugün; test için sahte uygulama zorunlu."""
    def al(self, anahtar: str) -> Sonuc | None: ...
    def koy(self, anahtar: str, sonuc: Sonuc, ttl_sn: int) -> None: ...
    def bosalt(self) -> None: ...

class Cizer(Protocol):
    """PanoPlani -> ekran.
    Gerekçe: streamlit bugün; SPEC kapsam dışı bölümü ileride başka bir
    çizerin gelebileceğini söylüyor, ama port bugün de gerekli: çizersiz
    test koşabilmek için."""
    def ciz(self, plan: PanoPlani, sonuclar: dict[str, Sonuc]) -> None: ...
```

**Port olmayanlar ve neden:** `audit` (tek uygulama, IO'su dosya, değişmesi
beklenmiyor) · `preprocess` (saf fonksiyonlar, doğrudan çağrılır) · `config`
(veri, davranış değil).

---

## 4. Çekirdek veri tipleri

Hepsi `frozen=True`. Bu bir stil tercihi değil: **bir anlam modeli sürümü bir
değerdir, değiştirilebilir bir nesne değil.** Sürümleme (ADR-9) ancak
değişmezlikle güvenilir olur.

```python
@dataclass(frozen=True)
class Olcu:
    ad: str; ifade: str; birim: str
    toplama: str                       # sayim | toplam | ortalama | benzersiz
    kaynak: str | None = None          # ör. "olcum WHERE tip='BOY'"  (eksen 2+3)
    uyari: str | None = None           # ör. "ortalamanın ortalaması alınamaz"

@dataclass(frozen=True)
class TabloAnlami:
    ad: str
    tur: str                           # olay | varlik
    tane: str                          # eksen 6 — insan söyler
    olay_tarihi: str | None            # eksen 7 — insan söyler
    gecerlilik: str | None             # eksen 8 — insan söyler
    iliskiler: tuple[Iliski, ...] = ()

@dataclass(frozen=True)
class AnlamModeli:
    baglanti: str; surum: int; onaylayan: str
    tablolar: Mapping[str, TabloAnlami]
    olculer:  Mapping[str, Olcu]
    boyutlar: Mapping[str, Boyut]
    maskeli:  frozenset[str]
    def dogrula(self) -> list[str]: ...     # boş = geçerli. ASLA fırlatmaz.

@dataclass(frozen=True)
class Secim:
    olculer: tuple[str, ...]
    boyutlar: tuple[str, ...]
    filtreler: tuple[Filtre, ...]
    zaman: Zaman | None
    sirala: str | None; limit: int | None
    model_surumu: int                  # SPEC F-5: damga bunu taşır
    gecersiz: tuple[str, ...] = ()     # doluysa hat burada durur (kapalı devre)
```

---

## 5. Akış — tek yönlü

```
soru
 → preprocess.resolve_dates          (saf)
 → Esleyici.esle(soru, sozluk)       (stokastik — TEK yer)
 → Secim                              (değişmez değer)
 → derleyici.derle(Secim, AnlamModeli) → SQL     (deterministik)
 → validator.validate_and_transpile(SQL)         (kapalı devre kapı)
 → Yurutucu.calistir(SQL)             → Sonuc
 → pano.plan(Sonuc)                   → PanoPlani (deterministik)
 → guven.degerlendir(Secim, Sonuc)    → bayraklar
 → Cizer.ciz(plan, sonuclar)
 → audit.yaz(soru, Secim, surum, SQL, satir_sayisi, süre, bayraklar)
```

Geriye yazma yoktur. Bunun iki somut kazancı var: denetim izi düz bir çizgidir,
ve **Sınır 2 tek bir boğazda sınanabilir** — `Sonuc` nesnesinin `Onbellek`
dışında hiçbir yere gitmediği tek noktada gösterilir.

---

## 6. SOLID — bu depodaki karşılıkları

### S · Tek sorumluluk

**Bugünkü ihlal ölçülebilir:** `guven.py` 760 satır ve depodaki en büyük modül.
Büyümesinin sebebi kalitesizlik değil **konumu**: her şeyi aynı anda görebilen
tek yer orasıydı, o yüzden her yeni sinyal oraya eklendi. `pipeline.ask()` da
aynı sınıfta: ön işleme, bağlam, üretim, güven, doğrulama, yürütme, kayıt.

**Ölçüt** — "bu modülü değiştirmek için kaç ayrı sebep var?"

| Modül | Bugün | v4'te |
|---|---|---|
| `guven.py` | 3 (yeni kontrol · SQL AST yorumu · terim eşleşmesi) | 1 (yeni kontrol) — AST yorumu ADR-8 ile ortadan kalkar |
| `pipeline.ask` | 6 | akış adımlarına bölünür, her biri 1 |

### O · Açık/kapalı — İhsan'ın şartının kod hâli

"Bir yeri atlarsak güncelleyebilelim" cümlesinin somut karşılığı, **genişleme
noktalarının önceden belli olması**:

| Ne eklenir | Nereye | Neye DOKUNULMAZ |
|---|---|---|
| Yeni SQL lehçesi | yeni `Yurutucu` + sqlglot `write` | derleyici, çekirdek, akış |
| Yeni grafik türü | `pano.py`'deki şekil→grafik tablosuna bir satır | eşleyici, derleyici |
| Yeni LLM sağlayıcı | yeni `Esleyici` | çekirdeğin tamamı |
| Yeni güven kontrolü | `guven.py`'ye bir fonksiyon + bir kod | hiçbir şey |
| **Yeni ölçü / boyut** | **anlam modeline bir giriş — kod yok** | **hiçbir şey** |

Son satır asıl kazanç: müşteri şemasına özgü her ihtiyaç, kod değişikliği değil
**veri** değişikliğidir. Ürünün kurulabilirliği buradan gelir.

### L · Liskov — v3'ün G-A hatası bir ilke ihlali olarak

`executor.run()` zaman aşımını yalnız `hasattr(raw, "interrupt")` doğruysa kurar;
`_readonly_url()` salt-okunurluğu yalnız `sqlite:///` için uygular ve
docstring'i şöyle der: *"diğer DB'lerde salt-okunur hesap kullanılması kurulum
önkoşuludur."*

Yani **alt tür, üst türün sözünü sessizce zayıflatıyor.** Tanımıyla LSP ihlali.
Ve bu projede bilinen en pahalı hata sınıfı: söz belgede, uygulama yok.

**Çare — sözleşme test takımı.** `tests/sozlesme/test_yurutucu.py`, her
`Yurutucu` uygulaması üzerinde parametrik koşar:

```python
@pytest.mark.parametrize("yurutucu", TUM_YURUTUCULER)
def test_zaman_asimi_gercek(yurutucu):        # uzun sorgu 30 sn'de kesilir
def test_yazma_reddedilir(yurutucu):          # INSERT denemesi başarısız
def test_azami_satir_uygulanir(yurutucu):     # sunucu tarafında LIMIT
def test_yazma_denemesi_raporlar(yurutucu):   # yazabilen hesabı bildirir
```

**Yeni bir lehçe, bu takımı geçmeden dağıtılmaz.** Aynı kalıp `Esleyici`,
`AnlamDeposu` ve `SemaKaynagi` için de kurulur. Bu, §7'nin ortak çaresidir:
*varsayımı çalıştırılabilir bir kontrole çevir.*

### I · Arayüz ayrımı — burada bir gizlilik sınırı

`SemaKaynagi` ile `Yurutucu` tek bir `Baglanti` arayüzünde birleştirilmiyor.
Sebebi kozmetik değil: `farkli_degerler` **veri değeri** döndürür ve yalnız
sihirbaza aittir. Ayrı arayüzler, sorgu yolundaki kodun o metoda erişiminin
**hiç olmaması** demektir — Sınır 1 tip düzeyinde uygulanır, disiplinle değil.

### D · Bağımlılığın tersine çevrilmesi

Çekirdek, uygulamaları değil portları tanır. Zorlanma yöntemi bir test:

```python
YASAK = {"sqlalchemy", "requests", "streamlit", "chromadb", "pandas", "ollama"}
def test_cekirdek_disariya_bagimli_degil():
    for modul in _cekirdek_modulleri():
        assert not (_importlar(modul) & YASAK), f"{modul} dışarıya bağımlı"
```

Öncülü var: v3 SPEC C-2 zaten "bir içe aktarım denetimi testi" öngörüyordu;
burada amacı değişiyor, kendisi değil.

---

## 7. SOLID'in ötesinde — dört kural

1. **Kapalı devre her sınırda.** `validator.py`'nin sözleşmesi tüm portlara
   genelleşir: hiçbir istisna katman sınırını geçmez; başarısızlık bir sonuç
   nesnesinin `hata` alanıdır. *Saha kaydı:* yakalanmayan bir `TokenError`
   50 soruluk ölçümü 30. soruda düşürdü ve 29 sonucu kaybetti.
2. **Saf çekirdek.** Bütün IO kenarlarda. Cetvel Katman 1'in saniyeler içinde
   koşabilmesinin tek sebebi bu.
3. **Tek yönlü akış.** §5. Denetim izi düz çizgi, Sınır 2 tek boğazda sınanır.
4. **Değiştirilebilirlik üç mekanizmayla** (İhsan'ın şartı):
   (a) **sürümlü anlam modeli** — yanlış bir etiketleme bir *göç* değil bir
   *yeni sürüm*tür; eskisi `anlam/gecmis/` altında durur;
   (b) **her genişleme noktası bir Protocol** — §6/O tablosu;
   (c) **davranış değiştiren her özelliğin bir yapılandırma anahtarı** —
   v3 SPEC §8'in geri alma kuralı korunur (`ANLAM_KATMANI=0` v3 davranışına döner).

---

## 8. Dosya yerleşimi

```
app/
  cekirdek/              # SAF — IO yok, LLM yok, DB yok
    portlar.py           # Protocol tanımları
    anlam.py             # AnlamModeli, Olcu, Boyut, TabloAnlami, dogrula()
    secim.py             # Secim, Filtre, Zaman, EslemeSonucu, to/from_json
    derleyici.py         # Secim + AnlamModeli -> SQL
    validator.py         # (v3'ten taşınır — zaten saf)
    pano.py              # Sonuc şekli -> PanoPlani (deterministik)
    guven.py             # Secim + Sonuc -> bayraklar (küçülmüş hâli)
  baglanti/              # ADAPTERS — IO burada
    sema_kaynagi.py      # Sqlite/Postgres SemaKaynagi
    yurutucu.py          # lehçe başına; sözleşme testi zorunlu
    anlam_deposu.py      # DosyaAnlamDeposu (anlam/ dizini — ADR-9)
    onbellek.py          # BellekOnbellegi (TTL, oturum sonunda boşalır)
    esleyici.py          # OllamaEsleyici, ApiEsleyici
  akis/                  # USE-CASE — bağlama burada, açıkça
    baglam.py            # OturumBaglami (E-4: süreç geneli durum yok)
    etiketle.py          # sihirbaz akışı
    sor.py               # soru -> pano
  audit.py  auth.py  config.py  preprocess.py  connections.py   # yerinde
ui/
  sihirbaz/              # etiketleme ekranları
  pano/                  # çizim
anlam/                   # anlam modelleri — KASTEN izlenir (ADR-9 §2a)
tests/
  cekirdek/              # LLM'siz, DB'siz — saniyeler
  sozlesme/              # her port için; LSP'nin uygulanabilir hâli
  sinir/                 # kanarya (SPEC E-1, E-2)
```

---

## 9. Mevcut modüller nereye gidiyor

| Bugün | Yarın | Not |
|---|---|---|
| `app/validator.py` | `cekirdek/validator.py` | Zaten saf: yalnız `sqlglot` + `dataclass`. **Tek satır değişmeden taşınır.** Kapalı devre sözleşmesi tüm mimarinin şablonu oldu |
| `app/executor.py` | `baglanti/yurutucu.py` | Bölünür ve **tamamlanır** (E-3). Ek bulgu: her çağrıda `create_engine` — Postgres'te pahalı, havuzlanmalı; `MAX_ROWS` istemci tarafında (`fetchmany`), sunucuda `LIMIT` yok |
| `app/guven.py` | `cekirdek/guven.py` | AST arkeolojisi (`_agac`, `_sql_tablolari`, `_takma_ad_haritasi`, `_metin_sabitleri`, `_kolon_degerleri`) gereksizleşir — o bilgi artık `Secim`'de beyan edilmiş hâlde duruyor. Kalan kontroller güçlenir |
| `app/schema_rag.py` | `baglanti/sema_kaynagi.py` + retrieval | Keşif kısmı porta; Chroma (ADR-3) **kalır** ama yükü değişir: tablo belgeleri yerine **ölçü/boyut sözlüğü** üzerinde arama (200 tablolu şemada sözlük de isteme sığmaz) |
| `app/generator.py` | `baglanti/esleyici.py` | Yeniden yazılır: "SQL üret" yerine "sözlükten seç". İP-15'in sessiz `except` düşüşü burada kapatılır |
| `app/pipeline.py` | `akis/sor.py` | Adımlara bölünür; modül düzeyi `_index` tekili kaldırılır (E-4) |
| `app/preprocess.py` | yerinde | Saf; `Secim.zaman` çözücüsüne bağlanır |
| `app/audit.py` | yerinde, genişler | `Secim` + model sürümü eklenir; satır asla girmez |
| `ui/pages/1_Dashboard.py` | silinir | Sabit sorgular derleyici çıktısına devreder |

---

## 10. Bilerek yapmadıklarımız

Aşırı mühendislik, bu projenin ölçüm tarafında zaten bir kez bedelini ödedi.
Aşağıdakiler **kasten** yok:

| Yok | Gerekçe |
|---|---|
| Bağımlılık enjeksiyon konteyneri | Tek yazar, tek dağıtım. Bağlama `akis/` içinde açıkça yapılır; konteyner tören olur |
| Olay veri yolu (event bus) | Akış tek yönlü ve senkron (§5). Veri yolu, izlenebilirliği azaltır |
| Eklenti kayıt defteri | Protocol + açık bağlama yeterli. Kayıt defteri, kimin ne uyguladığını gizler |
| Mikroservisler / FastAPI | v3 C-2 zaten ertelendi; kabul demosuna hiçbir şey katmıyor |
| "Her ihtimale karşı" soyut fabrikalar | Port ölçütü §3'te yazılı: ikinci uygulaması bugün var ya da SPEC'te yazılı olacak |
| ORM modelleri | Sorgular derleniyor; ORM araya girerse derleyicinin ürettiği SQL görünmez olur — G-02'yi bozar |
