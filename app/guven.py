"""Sessiz yanlış tespiti (B-7) — modelin kendi güven beyanından BAĞIMSIZ sinyaller.

Neden gerekli (ölçüm, 2026-08-16, n=101):

| Yapılandırma | Doğruluk | Yanlışların içinde sessiz olanlar |
|--------------|----------|-----------------------------------|
| llama3.2:3b  | %30      | %63 |
| qwen 7b      | %62      | **%95** |

Doğruluk yükseldikçe doğrulama katmanının yakaladığı pay DÜŞTÜ. Sebebi yapısal:
zayıf model sözdizim ve şema hatası yapar (validator yakalar), güçlü model ANLAM
hatası yapar — sorgusu geçerlidir, şemaya uyar, çalışır, ama sorulan soruyu
cevaplamaz. 38 yanlış cevabın 36'sı kullanıcıya hatasız bir tablo olarak döndü.

G-03'ün güven eşiği bu iş için yetersiz: eşik modelin kendi beyanına bakıyor ve
model yanılırken de yüksek güven bildiriyor (--doctor denemesinde guven=1.0).

Buradaki kontroller kasten BASİT ve LLM'SİZDİR:
- ek gecikme getirmezler (üretimi ikiye katlamazlar)
- test edilebilirler
- yanıldıklarında nasıl yanıldıkları anlaşılır

Amaç yanlışı düzeltmek değil, **yanlış olabileceğini söylemek.** Kullanıcı
"şu sayı yanlış olabilir çünkü filtre değeri şemada yok" uyarısıyla yaşayabilir;
sessiz yanlış sayıyla yaşayamaz.

Her bayrağın bir KODU var; ölçüm koşucusu kod bazında isabet/yanlış alarm
oranı raporlar. Kontrolün kendisi ölçülmeden açılmaz.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from app.preprocess import keywords, light_stem, resolve_dates

# Kod listesi — ölçüm raporu bu adlarla kırılım verir.
BOS_SONUC = "bos_sonuc"
BOS_SONUC_FILTRELI = "bos_sonuc_filtreli"
BILINMEYEN_DEGER = "bilinmeyen_deger"
BICIM_SAYI = "bicim_sayi"
BICIM_LISTE = "bicim_liste"
BICIM_ADET = "bicim_adet"
TOPLAMA_UYUMSUZ = "toplama_uyumsuz"
SEMA_ORTUSMEZ = "sema_ortusmez"
SIFIR_TOPLAMA = "sifir_toplama"
FILTRESIZ = "filtresiz"
ATLANAN_KOLON = "atlanan_kolon"
# İP-33 (2026-08-23): mutasyon havuzuna gerçek model hatasına benzeyen aileler
# eklenince yakalama %83 → %72'ye düştü ve düşüşün nerede olduğu görüldü —
# dolu, makul, doğru biçimli tablo + yanlış sayı. Aşağıdaki iki kontrol tam
# olarak o aileyi hedefliyor; ikisi de biçime değil, SORU İLE SORGUNUN
# UYUMUNA bakıyor.
DEGER_UYUMSUZ = "deger_uyumsuz"
DISTINCT_EKSIK = "distinct_eksik"

TUM_KODLAR = (BOS_SONUC, BOS_SONUC_FILTRELI, BILINMEYEN_DEGER, BICIM_SAYI,
              BICIM_LISTE, BICIM_ADET, TOPLAMA_UYUMSUZ, SEMA_ORTUSMEZ,
              SIFIR_TOPLAMA, FILTRESIZ, ATLANAN_KOLON,
              DEGER_UYUMSUZ, DISTINCT_EKSIK)


@dataclass
class Bayrak:
    kod: str
    mesaj: str


@dataclass
class GuvenSonucu:
    """Bayraklar boşsa sistem cevaptan şüphe duymuyor demektir — doğru olduğu anlamına gelmez."""

    guvenli: bool = True
    bayraklar: list[Bayrak] = field(default_factory=list)

    def bayrak(self, kod: str, mesaj: str) -> None:
        self.bayraklar.append(Bayrak(kod, mesaj))
        self.guvenli = False

    @property
    def kodlar(self) -> list[str]:
        return [b.kod for b in self.bayraklar]

    @property
    def mesajlar(self) -> list[str]:
        return [b.mesaj for b in self.bayraklar]


# --------------------------------------------------------------------- yardımcı

_TR_ASCII = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def _sade(s: str) -> str:
    """Türkçe harfleri ASCII'ye katlar.

    Gerekçe: şema adları çoğunlukla ASCII yazılır (`islem`, `bolum`), soru ise
    Türkçe yazılır (`işlem`, `bölüm`). Katlamadan yapılan her karşılaştırma
    kendi ürettiği yanlış alarmla dolar. Nokta birleştirici de düşürülür:
    'İ'.lower() == 'i̇' (i + U+0307) — 'i' değil.
    """
    return s.lower().replace("̇", "").translate(_TR_ASCII)


def _kok(kelime: str) -> str:
    return _sade(light_stem(kelime))


def _kok_ortusur(a: set[str], b: set[str]) -> bool:
    """İki kök kümesi birbirine değiyor mu — ÖN EK toleranslı.

    `light_stem` tek geçişli bir soyucudur ve aynı kökü farklı çekimlerden
    farklı uzunlukta bırakır: 'randevusuna' → 'randevus', 'randevu' → 'randev'.
    Tam eşitlik aramak, kendi soyucumuzun hatasını kullanıcıya uyarı olarak
    geri veriyordu (mutasyon karnesi: 12 gereksiz bayrağın 12'si buradan).
    Üç harflik ön ek eşleşmesi bu asimetriyi kapatır ('has' ⊂ 'hastam').
    """
    if a & b:
        return True
    return any(len(x) >= 3 and len(y) >= 3 and (x.startswith(y) or y.startswith(x))
               for x in a for y in b)


def _on_ek_ortusur(kok: str, kokler: set[str], asgari: int) -> bool:
    """İki kök aynı `asgari` harfle mi başlıyor.

    `_kok_ortusur`'den iki farkı var ve ikisi de ölçümden geldi:

    1. **Eşik ayarlanabilir.** Üç harflik ön ek, ŞEMA adları arasında doğru bir
       tolerans ('has' ⊂ 'hastam'); DEĞER metinleri arasında gürültü. Ölçüldü:
       "Hangi katlarda bölüm var?" sorusunda 'kat' kökü 'Katarakt' değerine üç
       harfle bağlanıp doğru bir cevaba uyarı koyuyordu.

    2. **`startswith` değil, ilk N harf.** Türkçede fiilden türeyen sıfat ile
       kolondaki durum kodu ortak bir GÖVDEYİ paylaşır ama ikisi de birbirinin
       ön eki değildir: 'geciken' ↔ 'GECIKTI', 'gelmeyen' ↔ 'GELMEDI'.
       `startswith` bu çiftleri kaçırıyor, ilk beş harf yakalıyor.
    """
    if len(kok) < asgari:
        return False
    bas = kok[:asgari]
    return any(len(o) >= asgari and o[:asgari] == bas for o in kokler)


# --------------------------------------------------------------------- niyet

_SAYI_SORAN = re.compile(
    r"\b(kac|sayisi|adet|adedi|ne kadar|toplami|ortalamasi|orani|yuzde)\b")
# 'hangisi' KASTEN yok: tekildir. "En ucuz işlem hangisi?" tek satır ister ve
# liste beklentisi kurmak yanlış alarm üretiyordu (karne: 3/3 gereksiz bayrak).
_LISTE_SORAN = re.compile(
    r"\b(listele|kimler|hangileri|neler|nelerdir|goster|sirala|"
    r"bazinda|gore\s+(?:dagilim|kirilim)|her\s+bir)\b")
_ILK_N = re.compile(r"\b(?:ilk|en)\s+(?:\w+\s+)?(\d+)\b")

# SIRA ÖNEMLİ — özelden genele. "Ortalama yatış süresi kaç gün?" hem 'ortalama'
# hem 'kaç' içerir; niyet AVG'dir. COUNT'u önce sorarsak kendi yanlış alarmımızı
# üretiriz (bu tam olarak testte yakalandı). Aynı şekilde "ortalama fatura
# tutarı" içindeki 'tutarı' SUM desenine takılır; AVG önce sorulmalı.
_TOPLAMA = (
    ("avg", re.compile(r"\b(ortalama|ortalamasi)\b")),
    ("count", re.compile(r"\b(kac|sayisi|adet|adedi)\b")),
    ("sum", re.compile(r"\b(toplam|toplami|ne kadar|ciro|gelir|tutari)\b")),
)

# Soru sözcüğü olup şema terimi olmayanlar — örtüşme testinde sayılmazlar.
_DURAK = {
    "kac", "hangi", "hangis", "kim", "kimler", "nedir", "ned", "neler", "ne",
    "listel", "goster", "sirala", "bul", "getir", "ver", "var", "olan", "olar",
    "ile", "icin", "gore", "daha", "cok", "coku", "azi", "toplam", "ortalama",
    "sayis", "adet", "adedi", "yuzde", "oran", "orani", "tum", "tumu", "her",
    "bir", "bu", "son", "ilk", "yil", "yilinda", "ayin", "bazi", "bazin", "arasi",
    # 'kayıt' Türkçe BI sorularında 'satır' anlamında genel bir sözcüktür
    # ("kaç kayıt var"), `kayit_tarihi` kolonuna işaret etmez.
    "kayit", "kayitl", "kayitli",
}


def _agac(sql: str):
    try:
        return sqlglot.parse_one(sql, read="sqlite")
    except Exception:      # noqa: BLE001 - güven kontrolü asla akışı kesmez
        return None


def _metin_sabitleri(agac) -> list[str]:
    return [str(n.this) for n in agac.find_all(exp.Literal) if n.is_string]


def _sql_tablolari(agac) -> tuple:
    """Sorgunun GERÇEKTEN dokunduğu tablolar.

    Çağıranın elindeki 'getirilen tablolar' listesi değil bu: RAG altı tablo
    getirir, model birini kullanır. Örtüşme kontrolü kullanılanı sormalı.
    """
    if agac is None:
        return ()
    adlar = []
    for t in agac.find_all(exp.Table):
        ad = t.name
        if ad and ad not in adlar:
            adlar.append(ad)
    return tuple(adlar)


# --------------------------------------------------------------------- kontroller

def _bos_sonuc(sonuc: GuvenSonucu, satir_sayisi: int, agac) -> None:
    """Sıfır satır, sessiz yanlışın en sık görünen yüzü.

    Filtre değeri şemada olmayan bir dizeye eşitlenmişse sorgu hata VERMEZ,
    boş küme döner ve kullanıcı 'demek ki hiç yok' diye okur. Türkçede bu
    tuzak daha da sinsi: 'İPTAL' ile 'IPTAL' farklı dizelerdir.
    """
    if satir_sayisi != 0:
        return
    literaller = _metin_sabitleri(agac) if agac is not None else []
    if literaller:
        sonuc.bayrak(
            BOS_SONUC_FILTRELI,
            "Sorgu hiç satır döndürmedi ve bir metin filtresi içeriyor "
            f"({', '.join(repr(x) for x in literaller[:3])}). "
            "Filtre değeri veritabanındaki yazımla birebir aynı olmayabilir.")
    else:
        sonuc.bayrak(
            BOS_SONUC,
            "Sorgu hiç satır döndürmedi. Bu gerçekten 'kayıt yok' anlamına "
            "geliyor olabilir ama sorgunun yanlış olma ihtimali de var.")


def _takma_ad_haritasi(agac) -> tuple[dict[str, str], str | None]:
    """Sorgudaki takma ad → gerçek tablo eşlemesi ve (tekse) tek tablo adı.

    B7R-06'nın çözümü buradan başlıyor: `bilinen_degerler` artık hem
    `tablo.kolon` hem `kolon` anahtarı taşıyor, ama üretilen SQL'de kolon
    genellikle `r.durum` gibi bir TAKMA ADLA nitelenmiş oluyor. Doğru kümeyi
    seçebilmek için önce o takma adın hangi tabloya karşılık geldiğini bilmek
    gerekiyor.

    İkinci dönen değer, sorguda tek bir tablo varsa onun adı: o durumda
    niteliksiz bir kolon (`durum`) da kesin biçimde çözülebilir.
    """
    harita: dict[str, str] = {}
    tablolar: set[str] = set()
    if agac is None:
        return harita, None
    for t in agac.find_all(exp.Table):
        ad = (t.name or "").lower()
        if not ad:
            continue
        tablolar.add(ad)
        harita[ad] = ad
        takma = (t.alias or "").lower()
        if takma:
            harita[takma] = ad
    return harita, (next(iter(tablolar)) if len(tablolar) == 1 else None)


def _kolon_degerleri(kolon, bilinen_degerler: dict, harita: dict[str, str],
                     tek_tablo: str | None, nitelikli: set[str]):
    """Bir kolon için KESİN değer kümesini bulur; bulamazsa birleşiğe düşer.

    Dönen: (değerler, kesin_mi). `kesin_mi` False ise küme aynı adlı bütün
    kolonların birleşimidir — bayrak koymak hâlâ güvenlidir (değer hiçbirinde
    yoksa gerçekten yoktur), ama kaçırma olabilir.

    `nitelikli`, sözlükte `tablo.kolon` anahtarı bulunan tabloların kümesi.
    Bunun kontrol edilmesi şart: sözlük nitelikli anahtar taşımıyorsa (elle
    kurulmuş bir harita, eski bir kayıt) kolonun o tabloda örneklenmediğini
    değil, sözlüğün o biçimde olmadığını gösterir — o durumda susmak yerine
    birleşik kümeye düşmek doğrudur.
    """
    ad = kolon.name.lower()
    nitel = (kolon.table or "").lower()
    tablo = harita.get(nitel) if nitel else tek_tablo
    if tablo and tablo in nitelikli:
        kesin = bilinen_degerler.get(f"{tablo}.{ad}")
        if kesin:
            return kesin, True
        # Tablo çözüldü, o tablonun değerleri sözlükte var, ama BU kolon
        # örneklenmemiş: kolon sayısal, maskeli ya da yüksek kardinaliteli
        # demektir; yer gerçeğimiz yok. Birleşik kümeye DÜŞMEYİZ — başka bir
        # tablonun değerleriyle karşılaştırmak yanlış alarmın ta kendisidir.
        return None, True
    return bilinen_degerler.get(ad), False


def _filtre_degerleri(sonuc: GuvenSonucu, agac, bilinen_degerler: dict) -> None:
    """SQL'deki metin filtreleri, o kolonun GERÇEK değerleri arasında mı?

    Sessiz yanlışın en somut biçimi ve tamamen belirlenimci: `unvan = 'Profesör'`
    yazıldığında kolonda yalnız 'Prof. Dr.' varsa, sorgunun sıfır satır
    döneceğini çalıştırmadan biliriz.

    LIKE kasten dışarıda: `LIKE '%kardiyo%'` bilinen değerlerin hiçbirine eşit
    olmaz ama doğrudur. Yalnız eşitlik ve IN denetlenir.
    """
    if not bilinen_degerler or agac is None:
        return
    ciftler: list[tuple[exp.Column, str]] = []
    for esitlik in agac.find_all(exp.EQ, exp.NEQ):
        kolon = esitlik.find(exp.Column)
        sabit = esitlik.find(exp.Literal)
        if kolon is not None and sabit is not None and sabit.is_string:
            ciftler.append((kolon, str(sabit.this)))
    for ic in agac.find_all(exp.In):
        kolon = ic.this if isinstance(ic.this, exp.Column) else None
        if kolon is None:
            continue
        for sabit in ic.expressions:
            if isinstance(sabit, exp.Literal) and sabit.is_string:
                ciftler.append((kolon, str(sabit.this)))

    harita, tek_tablo = _takma_ad_haritasi(agac)
    nitelikli = {a.split(".", 1)[0] for a in bilinen_degerler if "." in a}
    for kolon, deger in ciftler:
        degerler, kesin = _kolon_degerleri(kolon, bilinen_degerler, harita,
                                           tek_tablo, nitelikli)
        if not degerler or deger in degerler:
            continue
        yakin = [d for d in degerler if _sade(d) == _sade(deger)]
        nitel = f"{kolon.table}.{kolon.name}" if kolon.table else kolon.name
        if yakin:
            ipucu = f" Veritabanındaki yazım: {yakin[0]!r}."
        else:
            ipucu = (f" {'Bu kolondaki' if kesin else 'Aynı adlı kolonlardaki'} değerler: "
                     f"{', '.join(repr(d) for d in sorted(degerler)[:6])}.")
        sonuc.bayrak(BILINMEYEN_DEGER,
                     f"'{nitel}' kolonu {deger!r} değeriyle filtrelendi ama bu "
                     f"değer veritabanında bulunmuyor.{ipucu}")


def _sonuc_bicimi(sonuc: GuvenSonucu, soru: str, satir_sayisi: int,
                  kolon_sayisi: int, agac) -> None:
    """Soru bir SAYI istiyorsa cevap tek hücre olmalı; liste istiyorsa çok satır."""
    s = _sade(soru)
    sayi_istiyor = bool(_SAYI_SORAN.search(s))
    liste_istiyor = bool(_LISTE_SORAN.search(s))
    # GROUP BY varsa çok satır beklenir; 'kaç' + gruplama meşru bir kırılımdır.
    grupli = agac is not None and agac.find(exp.Group) is not None

    if sayi_istiyor and not liste_istiyor and not grupli and satir_sayisi > 1:
        sonuc.bayrak(BICIM_SAYI,
                     f"Soru tek bir sayı istiyor gibi görünüyor ama {satir_sayisi} "
                     "satır döndü. Gruplama fazladan yapılmış olabilir.")
    if liste_istiyor and satir_sayisi == 1 and kolon_sayisi == 1 and not sayi_istiyor:
        sonuc.bayrak(BICIM_LISTE,
                     "Soru liste istiyor gibi görünüyor ama tek bir değer döndü.")

    m = _ILK_N.search(s)
    if m and satir_sayisi:
        beklenen = int(m.group(1))
        if 1 < beklenen <= 100 and satir_sayisi > beklenen:
            sonuc.bayrak(BICIM_ADET,
                         f"Soruda {beklenen} kayıt isteniyor ama {satir_sayisi} "
                         "satır döndü; LIMIT konmamış olabilir.")


def _toplama_uyumu(sonuc: GuvenSonucu, soru: str, agac) -> None:
    """'kaç' COUNT ister, 'toplam' SUM, 'ortalama' AVG. Uyumsuzluk anlam hatasıdır."""
    if agac is None:
        return
    kullanilan = {type(f).__name__.lower()
                  for f in agac.find_all(exp.Count, exp.Sum, exp.Avg)}
    if not kullanilan:
        return                      # toplama yok — bu kontrolün diyeceği bir şey yok
    s = _sade(soru)
    for ad, desen in _TOPLAMA:
        if not desen.search(s):
            continue
        if ad not in kullanilan:
            sonuc.bayrak(TOPLAMA_UYUMSUZ,
                         f"Soru {ad.upper()} istiyor gibi görünüyor ama sorgu "
                         f"{'/'.join(sorted(k.upper() for k in kullanilan))} kullanıyor.")
        return                      # ilk eşleşen niyet bağlayıcıdır


def _sifir_toplama(sonuc: GuvenSonucu, satirlar, kolon_sayisi: int, agac) -> None:
    """Boş küme üzerinde toplama, hata değil SIFIR döndürür.

    Bu, `bos_sonuc`un görünmez kardeşidir ve daha tehlikelidir: `COUNT(*)`
    hiçbir kayda uymayan bir filtreyle çalıştığında sorgu 0 satır DEĞİL,
    içinde 0 yazan tek satır döndürür. Kullanıcı temiz bir tabloda '0' görür
    ve "demek ki hiç yok" diye okur — oysa filtre yanlış yazılmıştır.

    Mutasyon karnesi bunu açıkça gösterdi: imkânsız filtre eklenen 101
    sorgunun 45'i hiç bayrak almıyordu, çünkü hepsi 'bir satır döndü'.
    """
    if agac is None or kolon_sayisi != 1 or not satirlar or len(satirlar) != 1:
        return
    if agac.find(exp.Group) is not None:
        return
    if agac.find(exp.Count, exp.Sum, exp.Avg) is None:
        return
    try:
        deger = list(satirlar[0])[0]
    except (TypeError, IndexError):
        return
    if deger not in (0, None) or isinstance(deger, bool):
        return
    if not _metin_sabitleri(agac):
        return          # filtre yoksa sıfır meşru olabilir; bir şey söyleyemeyiz
    sonuc.bayrak(
        SIFIR_TOPLAMA,
        "Sonuç sıfır (ya da boş) çıktı ve sorguda bir metin filtresi var. "
        "Bu 'gerçekten hiç yok' anlamına gelebilir, ama filtre değeri "
        "veritabanındaki yazımla tutmuyorsa da tam olarak böyle görünür.")


_SAYI_TOKEN = re.compile(r"\d+")


def _filtresiz(sonuc: GuvenSonucu, soru: str, agac, bilinen_degerler: dict) -> None:
    """Soru bir daraltma istiyor ama sorguda hiç koşul yok.

    'İstanbul'da yaşayan kaç hasta var?' sorusuna WHERE'siz bir COUNT dönerse
    cevap tüm hastalardır — sorgu çalışır, sayı makul görünür, yanlıştır.
    Mutasyon karnesinde WHERE'i düşürülen 54 sorgunun 45'i hiç bayrak almıyordu.

    Daraltma işareti beş yerden gelir: sorudaki bir sayı (LIMIT olarak
    harcanmamış), cümle başında olmayan büyük harfli bir sözcük (özel ad),
    kesme işaretiyle ek almış bir özel ad, doğrudan şemada bilinen bir değer,
    ya da **bir zaman ifadesi** ("geçen ay", "bu yıl", "bugün", "son 7 gün").

    Zaman ayağı B7R-03 ile eklendi (2026-08-23). Kaçırılan `where_dus`
    mutantlarının ölçülen dökümünde en büyük aile buydu: "Geçen ay kaç randevu
    oluşturuldu?", "Bu yıl kesilen faturaların toplam tutarı", "Bugün bekleyen
    kaç randevu" — üçünde de daraltma var ama ne sayı ne özel ad ne bilinen
    değer taşıyor, dolayısıyla hiçbir işaret uyanmıyordu. Oysa aynı ifadeleri
    `preprocess.resolve_dates` zaten tanıyor ve mutlak aralığa çeviriyor:
    istemde kullanılan bilgi, kontrolde kullanılmıyordu.
    """
    if agac is None or agac.find(exp.Where, exp.Having) is not None:
        return
    s = _sade(soru)
    # Sorudaki sayı LIMIT olarak harcanmışsa daraltma işareti değildir.
    # "En çok randevu alan 5 hasta kim?" — 5, LIMIT 5'tir; WHERE beklemek
    # yanlış alarmdı (karne: 7 gereksiz bayrağın 7'si bu kalıptan).
    harcanan = {str(n.this) for n in agac.find_all(exp.Limit)
                for n in [n.expression] if n is not None}
    ilk_n = _ILK_N.search(s)
    if ilk_n:
        harcanan.add(ilk_n.group(1))
    isaretler = [x for x in _SAYI_TOKEN.findall(s) if x not in harcanan]

    kelimeler = re.findall(r"\w+", soru)
    isaretler += [w for w in kelimeler[1:] if w[:1].isupper() and len(w) > 2]
    # Türkçede özel ada gelen ek kesme işaretiyle ayrılır: "İstanbul'da",
    # "Kardiyoloji'nin". Cümle başındaki özel adı büyük harften ayırt etmenin
    # tek güvenilir yolu bu — "İstanbul'da yaşayan kaç hasta" ilk sözcükte
    # daraltma taşır ve büyük harf kuralı onu kaçırıyordu.
    isaretler += re.findall(r"\b\w{3,}(?=['’][a-zçğıöşü]{1,4}\b)", soru)

    # Zaman daraltması (B7R-03). `resolve_dates` yalnız dize eşlemesi yapar;
    # veritabanına gitmez, LLM çağırmaz. Hata verirse kontrol susar — bir
    # yardımcı kontrolün kendisi cevabı düşüremez.
    try:
        _, zamanlar = resolve_dates(soru)
    except Exception:                          # noqa: BLE001 - kontrol susar, cevap düşmez
        zamanlar = []
    isaretler += [z["ifade"] for z in zamanlar]

    # Bilinen bir değer aynı zamanda sorgunun kullandığı TABLONUN adıysa,
    # daraltma değil konu belirtmesidir: "muayene" hem islem.ad değeri hem
    # muayene tablosudur ve "en çok muayene yapan bölüm" WHERE istemez.
    tablo_kokleri = {_kok(t) for t in _sql_tablolari(agac)}
    # `bilinen_degerler` aynı değeri iki anahtar altında taşır (`tablo.kolon`
    # ve `kolon` — B7R-06). Burada aranan şey "bu kelime şemada bir değer mi",
    # yani birleşik küme; noktalı anahtarlar atlanarak bir kez toplanır.
    bilinen = {_sade(d)
               for anahtar, degerler in (bilinen_degerler or {}).items() if "." not in anahtar
               for d in degerler}
    isaretler += [w for w in kelimeler
                  if _sade(w) in bilinen and not _kok_ortusur({_kok(w)}, tablo_kokleri)]

    # Durum sözcükleri (B7R-03, ikinci ayak). Yukarıdaki eşleşme TAM dizedir ve
    # Türkçede neredeyse hiç tutmaz: kolonda `GECIKTI` yazar, soru "geciken
    # fatura" der; kolonda `GELMEDI`, soruda "gelmeyen". Aynı gövde, farklı
    # türetme — ikisi de birbirinin ön eki DEĞİL. `_on_ek_ortusur` bunun için
    # ilk beş harfi karşılaştırıyor.
    #
    # Dar tutuluyor, çünkü gevşek eşleşme yanlış alarm üretir:
    #   - sözcük en az 5 harf, durak listesi ve tablo adları dışarıda
    #   - yalnız DEĞER kökleri; kolon/tablo adları değil
    deger_kokleri = {_kok(d) for d in bilinen if len(d) >= 4} - tablo_kokleri
    isaretler += [w for w in kelimeler
                  if len(w) >= 5 and _kok(w) not in _DURAK
                  and not _kok_ortusur({_kok(w)}, tablo_kokleri)
                  and _on_ek_ortusur(_kok(w), deger_kokleri, 5)]

    # Daraltma WHERE'de değil de bir CASE içinde ifade edilmiş olabilir:
    # "Randevusuna gelmeme oranı en yüksek 5 doktor" sorusunun DOĞRU sorgusu
    # WHERE taşımaz, `SUM(CASE WHEN durum='GELMEDI' ...)` taşır. Sorgu o
    # değeri zaten yazmışsa daraltma eksik değildir — işaret düşürülür.
    # (Ölçüldü: bu eleme olmadan yukarıdaki ayak 1 gereksiz bayrak üretiyordu.)
    if isaretler:
        sabit_kokleri = {_kok(x) for x in _metin_sabitleri(agac)}
        if sabit_kokleri:
            isaretler = [w for w in isaretler
                         if not _on_ek_ortusur(_kok(str(w)), sabit_kokleri, 5)]

    if isaretler:
        sonuc.bayrak(
            FILTRESIZ,
            f"Soruda bir daraltma var gibi görünüyor ({', '.join(sorted(set(isaretler))[:3])}) "
            "ama sorguda hiç koşul yok — sonuç tüm kayıtları kapsıyor olabilir.")


def _atlanan_kolon(sonuc: GuvenSonucu, soru: str, agac, kolonlar) -> None:
    """Soruda adı geçen bir kolon, sorguda hiç yok.

    `filtresiz` kontrolü sorudaki DEĞERE bakar; bu kontrol sorudaki KAVRAMA
    bakar. "Profesör unvanlı doktorlar kimler?" sorusunda 'Profesör' şemada
    bilinen bir değer değildir (kolonda 'Prof. Dr.' yazar), ama 'unvan' bir
    kolon adıdır ve sorgu ona hiç dokunmamışsa soru cevaplanmamıştır.

    Mutasyon karnesinde WHERE'i düşürülen sorguların yarısı tam olarak böyle
    kaçıyordu: değer tanınmıyor, ama kavram soruda açıkça duruyor.
    """
    if agac is None or not kolonlar:
        return
    sql_kokleri = set()
    for dugum in list(agac.find_all(exp.Column)) + list(agac.find_all(exp.Table)):
        if dugum.name:
            sql_kokleri |= {_kok(p) for p in re.split(r"[_\W]+", dugum.name) if len(p) >= 3}
    if not sql_kokleri:
        return
    # Kolon adları çok parçalı olabilir (`odeme_durumu`, `kayit_tarihi`) ve
    # soru parçayı tek başına anar ("ödeme durumlarına göre"). Bütün adı
    # aramak, doğru sorgulara uyarı koyuyordu (karne: 3/3 gereksiz bayrak).
    kolon_kokleri: dict[str, str] = {}   # kök → özgün kolon adı
    for k in kolonlar:
        for parca in re.split(r"[_\W]+", str(k)):
            # Beş harf alt sınırı: `light_stem` 'hastanede'yi 'has'a indiriyor
            # ve bu 'hasta_id' parçasına çarpıyor. Kısa köklerde eşleşme
            # tesadüfi hale geliyor — karnede 7 gereksiz bayrağın kaynağı.
            if len(parca) >= 5:
                kolon_kokleri.setdefault(_kok(parca), k)
    eksik = []
    for w in keywords(_sade(soru)):
        kok = _kok(w)
        if len(kok) < 5 or kok in _DURAK:
            continue
        # Ön ek toleransı burada da gerekli: 'unvanlı' → 'unvanl', kolon 'unvan'.
        eslesen = next((kolon_kokleri[c] for c in kolon_kokleri
                        if c.startswith(kok) or kok.startswith(c)), None)
        if eslesen is None:
            continue
        if not _kok_ortusur({kok}, sql_kokleri):
            eksik.append(eslesen)
    if eksik:
        sonuc.bayrak(
            ATLANAN_KOLON,
            f"Soruda geçen '{eksik[0]}' alanına sorgu hiç dokunmuyor — "
            "sorulan koşul ya da kırılım atlanmış olabilir.")


_FARKLI_SORAN = re.compile(r"\b(farkli|ayri|benzersiz|essiz|tekil)\b")

# Karşılaştırma yönü. "en az / en fazla" KASTEN yok: Türkçede hem eşik
# ("en az 3 randevusu olan" = >= 3) hem üstünlük ("en az randevu alan doktor"
# = MIN) anlamına geliyor ve ikisini ayırmak sayının varlığına bağlı —
# belirsiz bir işaretle yanlış alarm üretmektense susmak doğru.
_BUYUK_SORAN = re.compile(r"\b(uzerinde|ustunde|buyuk|fazlasi|asan|gecen|"
                          r"yukari|sonraki|sonrasinda)\b")
_KUCUK_SORAN = re.compile(r"\b(altinda|altindaki|kucuk|azi|dusuk|"
                          r"asagi|onceki|oncesinde)\b")


def _karsilastirma_yonu(sonuc: GuvenSonucu, soru: str, agac) -> None:
    """Soru "üzerinde" diyor, sorgu `<` yazmış (ya da tersi).

    Yön hatası sessiz yanlışın en sinsi biçimlerinden: sorgu çalışır, satır
    döner, tablo tam olarak beklenen biçimdedir — yalnız yanlış tarafı sayar.
    `karsilastirma` mutant ailesinde ölçüldü.

    KASTEN dar: yalnız SAYISAL bir eşikle yapılan karşılaştırmaya bakar ve
    soruda yön işareti tek yönlüyse konuşur. Tarih karşılaştırmaları dışarıda
    (metin sabitidir ve "geçen ay" gibi ifadeler `filtresiz`'in işidir).
    """
    if agac is None:
        return
    s = _sade(soru)
    buyuk, kucuk = bool(_BUYUK_SORAN.search(s)), bool(_KUCUK_SORAN.search(s))
    if buyuk == kucuk:                 # ikisi de yok ya da ikisi de var
        return
    for dugum in agac.find_all(exp.GT, exp.GTE, exp.LT, exp.LTE):
        sabit = dugum.expression
        if not isinstance(sabit, exp.Literal) or sabit.is_string:
            continue
        sql_buyuk = isinstance(dugum, (exp.GT, exp.GTE))
        if sql_buyuk != buyuk:
            beklenen, yazilan = (">", "<") if buyuk else ("<", ">")
            sonuc.bayrak(
                DEGER_UYUMSUZ,
                f"Soru '{beklenen}' yönünde bir eşik istiyor gibi görünüyor ama "
                f"sorgu '{yazilan}' yazmış. Sonuç dolu döner; sayılan taraf ters olabilir.")
            return


def _distinct_eksik(sonuc: GuvenSonucu, soru: str, agac) -> None:
    """Soru "kaç FARKLI" diyor, sorgu DISTINCT'siz sayıyor.

    Sessiz yanlışın ders kitabı örneği: "MR çektiren kaç farklı hasta var?"
    sorusuna `COUNT(*)` cevabı ÇEKİM sayısını verir, HASTA sayısını değil.
    Sayı büyür, tablo doğru görünür, hiçbir biçim kontrolü uyanmaz — ölçüldü:
    `distinct_dus` mutantlarının %100'ü kaçıyordu.
    """
    if agac is None:
        return
    s = _sade(soru)
    if not (_FARKLI_SORAN.search(s) and _SAYI_SORAN.search(s)):
        return
    sayimlar = [n for n in agac.find_all(exp.Count)]
    if not sayimlar:
        return
    # `COUNT(DISTINCT x)` ya da sorgunun kendisinde `SELECT DISTINCT` varsa
    # tekilleştirme yapılmıştır. `GROUP BY` de aynı işi görebilir.
    if any(n.find(exp.Distinct) for n in sayimlar):
        return
    if agac.find(exp.Distinct) is not None or agac.find(exp.Group) is not None:
        return
    sonuc.bayrak(
        DISTINCT_EKSIK,
        "Soru 'kaç farklı' diye soruyor ama sayım tekilleştirilmemiş "
        "(`COUNT(DISTINCT ...)` yok). Tekrar eden kayıtlar varsa sayı "
        "olduğundan büyük çıkar.")


def _deger_uyumsuz(sonuc: GuvenSonucu, soru: str, agac, bilinen_degerler: dict) -> None:
    """Soruda geçen değer, sorgunun filtrelediği değer DEĞİL.

    `bilinmeyen_deger` sorgunun yazdığı değerin şemada olup olmadığına bakar.
    Bu kontrol bir adım ötesini sorar: değer şemada VAR ama soru başka bir
    değeri istiyor. "İptal edilen randevu sayısı" sorusuna `durum='BEKLIYOR'`
    cevabı — sorgu çalışır, satır döner, tablo makul, sayı yanlıştır.

    Ölçüm sebebi: `deger_takasi` ailesi (gold'daki filtre değerini AYNI kolonun
    başka bir geçerli değeriyle değiştirmek) mevcut sekiz kontrolün hiçbirine
    takılmıyordu — %21 yakalama. Gerçek model hatalarının %20'lik saha
    karnesinin arkasındaki aile büyük ölçüde budur.
    """
    if agac is None or not bilinen_degerler:
        return
    kelime_kokleri = {_kok(w) for w in re.findall(r"\w+", soru) if len(w) >= 4}
    if not kelime_kokleri:
        return
    harita, tek_tablo = _takma_ad_haritasi(agac)
    nitelikli = {a.split(".", 1)[0] for a in bilinen_degerler if "." in a}
    for esitlik in agac.find_all(exp.EQ):
        kolon = esitlik.find(exp.Column)
        sabit = esitlik.find(exp.Literal)
        if kolon is None or sabit is None or not sabit.is_string:
            continue
        kullanilan = str(sabit.this)
        degerler, _ = _kolon_degerleri(kolon, bilinen_degerler, harita,
                                       tek_tablo, nitelikli)
        if not degerler or kullanilan not in degerler:
            continue        # bilinmeyen değer: öteki kontrolün işi
        # Sorgunun kullandığı değer soruda anılıyorsa uyum vardır.
        if _on_ek_ortusur(_kok(kullanilan), kelime_kokleri, 5) or \
                _sade(kullanilan) in {_sade(w) for w in re.findall(r"\w+", soru)}:
            continue
        # Soru, AYNI kolonun BAŞKA bir değerini anıyor mu?
        anilan = [d for d in degerler
                  if d != kullanilan and len(d) >= 4
                  and _on_ek_ortusur(_kok(d), kelime_kokleri, 5)]
        if anilan:
            nitel = f"{kolon.table}.{kolon.name}" if kolon.table else kolon.name
            sonuc.bayrak(
                DEGER_UYUMSUZ,
                f"Soru {anilan[0]!r} değerinden söz ediyor ama sorgu "
                f"'{nitel}' kolonunu {kullanilan!r} ile filtreliyor. "
                "Sonuç dolu ve makul görünür; sayı sorulan şeyin sayısı olmayabilir.")


def _soru_sema_ortusmesi(sonuc: GuvenSonucu, soru: str, tablolar,
                         sozluk: dict, agac=None) -> None:
    """Sorudaki iş terimleri, sorgunun dokunduğu şemayla hiç örtüşmüyorsa şüphe.

    B7R-01 (2026-08-23): kontrol yalnız TABLO adlarına bakıyordu ve bu yüzden
    kapalı geliyordu — ölçülen yanlış alarmın %83'ü buradandı. Örnek:
    "Gastrit tanısı alan kaç farklı hasta var?" sorgusu `muayene` tablosuna
    ve `tani` kolonuna dokunuyor; 'tanı' bir KOLON adıdır, tablo adı değil.
    Örtüşme vardı, kontrol göremiyordu.

    Kolon adları da şema tarafına yazılınca kontrol açılabilir hâle geldi.
    Ölçüm bu değişikliğin sonucudur, gerekçesi değil — `test_guven_karne.py`
    her iki yapılandırmanın sayısını kilitliyor.
    """
    if not tablolar:
        return
    kokler = {_kok(w) for w in keywords(_sade(soru))} - _DURAK
    if not kokler:
        return
    sema = set()
    for t in tablolar:
        sema |= {_kok(p) for p in re.split(r"[_\W]+", str(t)) if p}
    # Sorgunun GERÇEKTEN andığı kolonlar. Çok parçalı adlar parçalanır
    # (`odeme_durumu` → 'odeme', 'durumu'), çünkü soru parçayı tek başına anar.
    if agac is not None:
        for kolon in agac.find_all(exp.Column):
            if kolon.name:
                sema |= {_kok(p) for p in re.split(r"[_\W]+", kolon.name) if len(p) >= 3}
    # Terim sözlüğü iş terimini şema nesnesine bağlar (G-06). Terimin KENDİSİ de
    # şema tarafına yazılır: 'ciro' sözlükte tanımlıysa şemada 'ciro' kolonu
    # aranmaz — terim zaten karşılığına bağlanmıştır, örtüşme sağlanmış sayılır.
    for terim, karsilik in (sozluk or {}).items():
        if _kok(terim) in kokler:
            sema.add(_kok(terim))
            sema |= {_kok(w) for w in re.findall(r"\w+", str(karsilik))}
    if not _kok_ortusur(kokler, sema):
        sonuc.bayrak(SEMA_ORTUSMEZ,
                     "Sorudaki terimlerle sorgunun kullandığı tablolar "
                     f"({', '.join(str(t) for t in tablolar)}) örtüşmüyor.")


# --------------------------------------------------------------------- giriş noktası

def degerlendir(soru: str, sql: str, satir_sayisi: int, kolon_sayisi: int = 1,
                tablolar=(),
                satirlar=None,
                bilinen_degerler: dict | None = None,
                kolonlar=None,
                sozluk: dict | None = None,
                kapali: set[str] | None = None) -> GuvenSonucu:
    """Cevaptan şüphe etmek için sebep var mı?

    `kapali`: yanlış alarm oranı ölçülüp kabul edilemez bulunan kontroller
    kod adıyla kapatılabilir. Kontrolü silmek yerine kapatmak, ölçümün
    tekrarlanabilir kalmasını sağlar.

    SÖZLEŞME: asla istisna fırlatmaz. Güven kontrolü bir yardımcıdır; çökerse
    kullanıcı cevabı alamaz hale gelmemeli — yalnız uyarısız kalır.
    """
    sonuc = GuvenSonucu()
    try:
        agac = _agac(sql)
        _bos_sonuc(sonuc, satir_sayisi, agac)
        _filtre_degerleri(sonuc, agac, bilinen_degerler or {})
        _sonuc_bicimi(sonuc, soru, satir_sayisi, kolon_sayisi, agac)
        _sifir_toplama(sonuc, satirlar, kolon_sayisi, agac)
        _filtresiz(sonuc, soru, agac, bilinen_degerler or {})
        _atlanan_kolon(sonuc, soru, agac, kolonlar or ())
        _toplama_uyumu(sonuc, soru, agac)
        _distinct_eksik(sonuc, soru, agac)
        _karsilastirma_yonu(sonuc, soru, agac)
        _deger_uyumsuz(sonuc, soru, agac, bilinen_degerler or {})
        _soru_sema_ortusmesi(sonuc, soru, tuple(tablolar or ()) or _sql_tablolari(agac),
                             sozluk or {}, agac)
    except Exception as e:      # noqa: BLE001 - sözleşme: asla fırlatma
        sonuc.bayraklar.append(
            Bayrak("kontrol_hatasi", f"(güven kontrolü tamamlanamadı: {type(e).__name__})"))
    if kapali:
        sonuc.bayraklar = [b for b in sonuc.bayraklar if b.kod not in kapali]
        sonuc.guvenli = not sonuc.bayraklar
    return sonuc
