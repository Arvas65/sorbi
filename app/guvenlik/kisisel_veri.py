"""Kişisel veri algılayıcıları — Türkiye'ye özgü ve DOĞRULAMALI (ADR-10 § 3.3).

İki tür bulgu vardır:

- **doğrulanmış** (`dogrulandi=True`): biçimi VE sağlama hanesi/algoritması tutan
  bulgu. TCKN, VKN, TR IBAN, kart numarası (Luhn), e-posta, telefon. Çıkış kapısı
  YALNIZ bunlarla engeller: yanlış alarm vermeyen bir kapı, kapatılmayan kapıdır.
- **şüpheli** (`dogrulandi=False`): kişi adı, plaka, IP, URL, tarih, uzun sayı.
  Anonimleştirici bunları da jetonlar — dışarı gitmesi gerekmeyen bir şeyi
  jetonlamanın bedeli yok, kaçırmanın bedeli var.

Kişi adı algılama bir sınıflandırıcı değil, bir **izin listesi** meselesidir
(bkz. `anonimlestirici`): burada yalnız güçlü işaretler aranır — unvan kalıbı
("Dr. Ayşe Kaya"), hitap kalıbı ("Ayşe Hanım"), yaygın Türkçe ad listesi.

Hiçbir işlev istisna fırlatmaz; bozuk girdi boş liste döner.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------- doğrulayıcılar


def tckn_gecerli(s: str) -> bool:
    """T.C. Kimlik No: 11 hane, ilk hane 0 değil, iki sağlama hanesi."""
    if len(s) != 11 or not s.isdigit() or s[0] == "0":
        return False
    d = [int(c) for c in s]
    h10 = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
    h11 = sum(d[:10]) % 10
    return d[9] == h10 and d[10] == h11


def vkn_gecerli(s: str) -> bool:
    """Vergi Kimlik No: 10 hane, GİB sağlama algoritması."""
    if len(s) != 10 or not s.isdigit():
        return False
    toplam = 0
    for i in range(9):
        tmp = (int(s[i]) + 9 - i) % 10
        toplam += 9 if (tmp != 0 and tmp * (2 ** (9 - i)) % 9 == 0) else (tmp * (2 ** (9 - i))) % 9
    return (10 - (toplam % 10)) % 10 == int(s[9])


def iban_gecerli(s: str) -> bool:
    """TR IBAN: 'TR' + 24 hane, ISO 13616 mod-97 = 1."""
    s = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"TR\d{24}", s):
        return False
    yeniden = s[4:] + s[:4]
    sayi = "".join(str(int(c, 36)) for c in yeniden)
    return int(sayi) % 97 == 1


def luhn_gecerli(s: str) -> bool:
    rakam = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(rakam) <= 19:
        return False
    toplam = 0
    for i, r in enumerate(reversed(rakam)):
        if i % 2:
            r *= 2
            if r > 9:
                r -= 9
        toplam += r
    return toplam % 10 == 0


# --------------------------------------------------------------- sözcük listeleri
# Kaynak: genel kullanım. Liste bir tavandır, taban değil — eksik ad, kesme
# işareti ve büyük harf kalıbıyla (anonimleştirici) yine yakalanır.

AD_LISTESI = frozenset("""
ahmet mehmet mustafa ali hüseyin hasan ibrahim ismail osman yusuf murat ömer ramazan halil
süleyman abdullah mahmut recep salih fatih kadir emre hakan kemal yaşar orhan metin serkan
burak onur volkan cem can mert kaan eren berk emir arda deniz efe baran kerem yiğit furkan
enes emirhan ahmetcan umut uğur tolga tuncay erkan erdem erol ercan engin cengiz cihan
coşkun levent sinan tamer tarık tayfun yavuz yunus zafer selim sercan serdar sezer şahin
şükrü tahsin taner tuna turgut ufuk vedat veli yakup yıldırım yücel zeki bülent barış
batuhan bilal doğan ekrem fikret gökhan göktuğ hamza harun hikmet ilker ilhan kenan koray
korkut necati nihat oğuz özgür rıza sadık sami savaş şenol tevfik tuğrul ihsan
fatma ayşe emine hatice zeynep elif meryem şerife zehra sultan hanife merve özlem yasemin
esra hülya aysel leyla derya gamze gül gülsüm hacer havva kübra melek nur pınar rabia
seda sevgi sibel songül tuba tuğba yeter zeliha zübeyde ebru dilek aslı buse büşra cansu
ceren damla dilara duygu ece ecem eda ela elçin esin ezgi funda gizem gökçe hande ilknur
irem kader melike melis nazlı nesrin nilay nurcan özge rana selin sena serap sevda sinem
şeyma şule tülay ümran yağmur yeliz yıldız zerrin aylin aynur azra beril berna betül burcu
canan çiğdem defne dilan ebru ela feyza gülay gülşen hilal ipek işıl lale meltem mine
müge nalan nermin neslihan oya öykü perihan reyhan saadet sabriye semra sevim şebnem şükran
tülin ülkü yonca zuhal
""".split())

IL_LISTESI = frozenset("""
adana adıyaman afyonkarahisar ağrı amasya ankara antalya artvin aydın balıkesir bilecik
bingöl bitlis bolu burdur bursa çanakkale çankırı çorum denizli diyarbakır edirne elazığ
erzincan erzurum eskişehir gaziantep giresun gümüşhane hakkari hatay ısparta mersin istanbul
izmir kars kastamonu kayseri kırklareli kırşehir kocaeli konya kütahya malatya manisa
kahramanmaraş mardin muğla muş nevşehir niğde ordu rize sakarya samsun siirt sinop sivas
tekirdağ tokat trabzon tunceli şanlıurfa uşak van yozgat zonguldak aksaray bayburt karaman
kırıkkale batman şırnak bartın ardahan iğdır yalova karabük kilis osmaniye düzce türkiye
""".split())

TAKVIM = frozenset("""
ocak şubat mart nisan mayıs haziran temmuz ağustos eylül ekim kasım aralık
pazartesi salı çarşamba perşembe cuma cumartesi pazar
""".split())

_UNVAN = r"(?:Prof\.\s*Dr\.|Doç\.\s*Dr\.|Dr\.\s*Öğr\.\s*Üyesi|Uzm\.\s*Dr\.|Op\.\s*Dr\.|Dr\.|Av\.|Müh\.|Hemşire|Ebe|Bay|Bayan|Sayın)"
_BUYUK = r"[A-ZÇĞİÖŞÜ][a-zçğıöşü]+"
_AD = rf"{_BUYUK}(?:\s+{_BUYUK}){{0,2}}"

# --------------------------------------------------------------- kalıplar

_KALIPLAR: list[tuple[str, re.Pattern, bool]] = [
    # (tür, kalıp, doğrulama gerekir mi)
    ("EPOSTA", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), False),
    ("IBAN", re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE), True),
    ("KART", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), True),
    ("TELEFON", re.compile(r"(?<!\d)(?:\+90[\s-]?|0)?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"), False),
    ("TELEFON", re.compile(r"(?<!\d)(?:\+90[\s-]?|0)\(?[2-4]\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"), False),
    ("TCKN", re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)"), True),
    ("VKN", re.compile(r"(?<!\d)\d{10}(?!\d)"), True),
    ("URL", re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE), False),
    ("IP", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"), False),
    ("PLAKA", re.compile(r"\b(?:0[1-9]|[1-7]\d|8[01])\s?[A-Z]{1,3}\s?\d{2,4}\b"), False),
    ("TARIH", re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b|\b(?:19|20)\d{2}-\d{2}-\d{2}\b"), False),
    ("TARIH", re.compile(r"\b\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(?:19|20)\d{2}\b", re.IGNORECASE), False),
    ("SAYI", re.compile(r"(?<!\d)\d{6,}(?!\d)"), False),
]

_DOGRULAYICI = {"TCKN": tckn_gecerli, "VKN": vkn_gecerli, "IBAN": iban_gecerli, "KART": luhn_gecerli}

# Biçimi tek başına yeterince ayırt edici olan ve doğrulayıcısı olmayan türler
# çıkış kapısı için "doğrulanmış" sayılır.
_BICIM_YETER = frozenset({"EPOSTA", "TELEFON"})

_UNVANLI_AD = re.compile(rf"{_UNVAN}\s+(?P<ad>{_AD})")
_HITAPLI_AD = re.compile(rf"(?P<ad>{_AD})\s+(?:Hanım|Bey|Hoca)\b")
_SOZCUK = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+")
_SOYAD_ADAYI = re.compile(r"\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)")

# Hitap ve unvan sözcükleri bir adın parçası değildir; ad genişletilirken durulur.
HITAP = frozenset("hanım bey hoca bay bayan sayın dr prof doç uzm op av müh hemşire ebe".split())


def tr_kucuk(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


@dataclass(frozen=True)
class Bulgu:
    tur: str
    bas: int
    son: int
    metin: str
    dogrulandi: bool


def bul(metin: str) -> list[Bulgu]:
    """Metindeki kişisel veri adaylarını bulur. Çakışanlardan önceliklisi kalır."""
    if not isinstance(metin, str) or not metin:
        return []
    adaylar: list[Bulgu] = []
    for tur, kalip, dogrulama in _KALIPLAR:
        for m in kalip.finditer(metin):
            parca = m.group(0)
            if dogrulama:
                if not _DOGRULAYICI[tur](re.sub(r"[\s-]", "", parca)):
                    continue
                adaylar.append(Bulgu(tur, m.start(), m.end(), parca, True))
            else:
                adaylar.append(Bulgu(tur, m.start(), m.end(), parca, tur in _BICIM_YETER))
    for kalip in (_UNVANLI_AD, _HITAPLI_AD):
        for m in kalip.finditer(metin):
            adaylar.append(Bulgu("KISI", m.start("ad"), m.end("ad"), m.group("ad"), False))
    for m in _SOZCUK.finditer(metin):
        if tr_kucuk(m.group(0)) in AD_LISTESI:
            # "Ahmet Yılmaz", "Ayşe Nur Demir": addan sonra gelen büyük harfli
            # sözcükler (en çok iki) soyadıdır — hitap sözcüğünde durulur.
            son = m.end()
            for _ in range(2):
                s = _SOYAD_ADAYI.match(metin, son)
                if not s or tr_kucuk(s.group(1)) in HITAP:
                    break
                son = s.end()
            adaylar.append(Bulgu("KISI", m.start(), son, metin[m.start():son], False))
    return _cakisma_coz(adaylar)


_ONCELIK = {t: i for i, t in enumerate(
    ["IBAN", "KART", "EPOSTA", "URL", "TCKN", "VKN", "TELEFON", "IP", "PLAKA",
     "TARIH", "KISI", "SAYI"])}


def _cakisma_coz(adaylar: list[Bulgu]) -> list[Bulgu]:
    """Doğrulanmış önce, sonra öncelik, sonra uzun olan. Kalanlar sırayla."""
    adaylar.sort(key=lambda b: (not b.dogrulandi, _ONCELIK.get(b.tur, 99), -(b.son - b.bas)))
    secilen: list[Bulgu] = []
    for b in adaylar:
        if all(b.son <= s.bas or b.bas >= s.son for s in secilen):
            secilen.append(b)
    return sorted(secilen, key=lambda b: b.bas)


def dogrulanmis(metin: str) -> list[Bulgu]:
    """Çıkış kapısının baktığı tek şey: yüksek güvenli bulgular."""
    return [b for b in bul(metin) if b.dogrulandi]
