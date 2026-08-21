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

from app.preprocess import keywords, light_stem

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

TUM_KODLAR = (BOS_SONUC, BOS_SONUC_FILTRELI, BILINMEYEN_DEGER, BICIM_SAYI,
              BICIM_LISTE, BICIM_ADET, TOPLAMA_UYUMSUZ, SEMA_ORTUSMEZ,
              SIFIR_TOPLAMA, FILTRESIZ, ATLANAN_KOLON)


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

    for kolon, deger in ciftler:
        degerler = bilinen_degerler.get(kolon.name.lower())
        if not degerler or deger in degerler:
            continue
        yakin = [d for d in degerler if _sade(d) == _sade(deger)]
        if yakin:
            ipucu = f" Veritabanındaki yazım: {yakin[0]!r}."
        else:
            ipucu = (" Bu kolondaki değerler: "
                     f"{', '.join(repr(d) for d in sorted(degerler)[:6])}.")
        sonuc.bayrak(BILINMEYEN_DEGER,
                     f"'{kolon.name}' kolonu {deger!r} değeriyle filtrelendi ama bu "
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

    Daraltma işareti üç yerden gelir: sorudaki bir sayı (LIMIT olarak
    harcanmamış), cümle başında olmayan büyük harfli bir sözcük (özel ad),
    ya da doğrudan şemada bilinen bir değer.
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

    # Bilinen bir değer aynı zamanda sorgunun kullandığı TABLONUN adıysa,
    # daraltma değil konu belirtmesidir: "muayene" hem islem.ad değeri hem
    # muayene tablosudur ve "en çok muayene yapan bölüm" WHERE istemez.
    tablo_kokleri = {_kok(t) for t in _sql_tablolari(agac)}
    bilinen = {_sade(d) for degerler in (bilinen_degerler or {}).values() for d in degerler}
    isaretler += [w for w in kelimeler
                  if _sade(w) in bilinen and not _kok_ortusur({_kok(w)}, tablo_kokleri)]

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


def _soru_sema_ortusmesi(sonuc: GuvenSonucu, soru: str, tablolar,
                         sozluk: dict) -> None:
    """Sorudaki iş terimleri, sorgunun dokunduğu tablolarla hiç örtüşmüyorsa şüphe."""
    if not tablolar:
        return
    kokler = {_kok(w) for w in keywords(_sade(soru))} - _DURAK
    if not kokler:
        return
    sema = set()
    for t in tablolar:
        sema |= {_kok(p) for p in re.split(r"[_\W]+", str(t)) if p}
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
        _soru_sema_ortusmesi(sonuc, soru, tuple(tablolar or ()) or _sql_tablolari(agac),
                             sozluk or {})
    except Exception as e:      # noqa: BLE001 - sözleşme: asla fırlatma
        sonuc.bayraklar.append(
            Bayrak("kontrol_hatasi", f"(güven kontrolü tamamlanamadı: {type(e).__name__})"))
    if kapali:
        sonuc.bayraklar = [b for b in sonuc.bayraklar if b.kod not in kapali]
        sonuc.guvenli = not sonuc.bayraklar
    return sonuc
