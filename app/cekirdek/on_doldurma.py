"""Şemadan ön-doldurma (SPEC A-2) — sihirbazın doldurulmuş formu.

Kullanıcıya "bu kolon ne demek?" diye açık uçlu sorulmaz; cevap alınamaz.
Sistem şemadan **tahmin eder**, insan onaylar ya da düzeltir. Bu modül o
tahmini üretir.

## Taşıyıcı kural: öneri GEÇERLİ BİR MODEL DEĞİLDİR

`oner()` her tabloyu `olay_tarihi=None` + `gecerlilik_karari=SORULMADI`, her
boyutu `sozluk_karari=SORULMADI` ve her ilişkiyi `kardinalite=OLCULMEDI` ile
döndürür — yani ürettiği model `dogrula()`'dan GEÇMEZ.

Bu bir eksiklik değil, tasarımın kendisi. Ön-doldurma bir öneridir; sihirbazın
işi öneriyi KARARA çevirmektir. Model geçerli doğsaydı, kimse hiçbir şey
onaylamadan kaydedilebilir ve eksen 6/7/8'in tamamı sessizce tahmine kalırdı —
tam olarak kaçındığımız şey.

## Neyi tahmin edebiliriz, neyi edemeyiz

Tahmin edilebilir (şemada iz var):  ad kalıpları, tipler, FK'ler, kardinalite.
Tahmin EDİLEMEZ (şemada iz yok):    tane, hangi tarihin "olay" tarihi olduğu,
                                    hangi satırların sayılmayacağı.

İkinci grup için ön-doldurma **yalnız sıralı aday** üretir (`Oneri.tarih_adaylari`
vb.); seçimi insan yapar. Bu ayrım v4 SPEC §2'nin sekiz ekseninin doğrudan
sonucudur.

## Neden alan doldurulmuyor da aday veriliyor

İlk taslak `olay_tarihi`'ni en güçlü adayla DOLDURUYORDU. Gerçek şema üzerinde
denendiğinde `hasta` tablosuna `olay_tarihi = dogum_tarihi` yazdı: hastalar
doğum tarihine göre sayılırdı ve `acik_sorular()` bunu SORMAZDI, çünkü alan
dolu görünüyordu. Dolu bir alan, alınmış bir karar gibi okunur. Eksen 7 için
"doldur ve sor" diye bir kip yok; ya karar insanındır ya değildir.

Modül saftır: girdisi `TabloSemasi`/`Iliski` listeleri ve ölçüm sonuçları,
çıktısı bir `Oneri`. Veritabanı görmez — ölçümleri `SemaKaynagi` yapar ve
buraya değer olarak verir.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from app.cekirdek.anlam import AnlamModeli, Boyut, Olcu, TabloAnlami
from app.cekirdek.tipler import (
    Iliski,
    Karar,
    Kardinalite,
    KolonSemasi,
    TabloSemasi,
    Toplama,
    Tur,
)

# --------------------------------------------------------------------------- #
#  Ad kalıpları
# --------------------------------------------------------------------------- #

# Olay tarihi adayları — SIRA ÖNEMLİ, ilk sıradaki en güçlü aday.
_TARIH_ONCELIK = (
    r"^tarih$", r"^islem_tarihi$", r"^giris_tarihi$", r"^baslangic",
    r"_tarihi$", r"_tarih$", r"^date$", r"_date$", r"_at$",
)

# Bunlar da tarihtir ama olayın OLDUĞU tarih değildir: kaydın açıldığı,
# kişinin doğduğu, satırın güncellendiği tarih. Hepsi `_TARIH_ONCELIK`teki
# genel `_tarihi$` kalıbına da uyar; bu yüzden ÖNCE burada aranır — yoksa
# `kayit_tarihi` genel kalıba takılıp en güçlü aday olarak öne çıkardı ve
# eksen 7'nin sessiz yanlışını üretirdi.
_TARIH_GEC = (
    r"^kayit_tarihi$", r"^dogum_tarihi$", r"^olusturma", r"^guncelleme",
    r"^ise_baslama", r"^created", r"^updated", r"^modified",
)
_GEC_TABAN = 100          # geç sıra adayların puan tabanı
_TIPTEN_TABAN = 200       # adı hiçbir kalıba uymayan, yalnız tipi tarih olan

# Geçerlilik (eksen 8) adayları: bu kolonlar "bu satır sayılmalı mı" sorusunu
# taşıyor olabilir. Öneri bir KOŞUL değil, bir SORU üretir.
_GECERLILIK_DESEN = re.compile(
    r"^(iptal|silindi|silinmis|aktif|pasif|durum|statu|status|deleted|"
    r"is_deleted|is_active|cancelled|iptal_mi|test|taslak)$", re.IGNORECASE)

# Kişisel veri — GÜÇLÜ imler: tek başına o kolonu maskeler.
_KISISEL_GUCLU = re.compile(
    r"(tckn|tc_kimlik|kimlik_no|^soyad$|ad_soyad|adsoyad|telefon|gsm|"
    r"^cep$|email|eposta|e_posta|^adres|dogum_tarihi|iban|kart_no)", re.IGNORECASE)

# ZAYIF im: `ad` bir kişinin adı da olabilir, bir bölümün adı da. Yalnız
# tabloda güçlü bir im daha varsa kişisel sayılır. Bu ayrım olmadan
# `bolum.ad` ve `islem.ad` maskelenir; şemanın okunabilir tek etiketleri
# yok olur ve model işe yaramaz hâle gelir — gizlilik değil, körlük olurdu.
_KISISEL_ZAYIF = re.compile(r"^(ad|isim|name)$", re.IGNORECASE)

# Ölçü ya da boyut adayı OLMAYAN kolonlar: anahtarlar ve kodlar.
_ANAHTAR = re.compile(r"(_id$|^id$|_no$|_kodu$|^kod$)", re.IGNORECASE)

# Boyut olamayacak serbest metin: benzersize yakın, gruplanamaz.
_SERBEST_METIN = re.compile(
    r"^(notlar?|aciklama|açıklama|yorum|mesaj|metin|detay|description|note[s]?)$",
    re.IGNORECASE)

# Aynı adla birden çok tabloda geçen, tek başına anlamsız kolon adları.
# Boyut adı olarak nitelenir: `ad` değil `bolum_ad`.
_GENEL_AD = frozenset({"ad", "isim", "name", "kod", "tur", "tip", "durum", "adi"})

_SAYISAL_TIP = re.compile(r"(int|real|float|double|decimal|numeric|money)",
                          re.IGNORECASE)
_TARIH_TIP = re.compile(r"(date|time|timestamp)", re.IGNORECASE)


def _tarih_puani(k: KolonSemasi) -> int | None:
    """Kolonun olay-tarihi adaylığı; küçük puan = güçlü aday. Yoksa None."""
    for sira, desen in enumerate(_TARIH_GEC):
        if re.search(desen, k.ad, re.IGNORECASE):
            return _GEC_TABAN + sira
    for sira, desen in enumerate(_TARIH_ONCELIK):
        if re.search(desen, k.ad, re.IGNORECASE):
            return sira
    return _TIPTEN_TABAN if _TARIH_TIP.search(k.tip or "") else None


def _tarih_mi(k: KolonSemasi) -> bool:
    return _tarih_puani(k) is not None


def _sayisal_mi(k: KolonSemasi) -> bool:
    return bool(_SAYISAL_TIP.search(k.tip or "")) and not _ANAHTAR.search(k.ad)


def tarih_adaylari(t: TabloSemasi) -> tuple[str, ...]:
    """Olay tarihi adayları, güçlüden zayıfa sıralı.

    Sihirbaz bunu bir açılır listeye koyar; ilk sıradaki ön-SEÇİLİ olabilir
    ama karar kaydedilmeden model geçerli olmaz. `kayit_tarihi`,
    `dogum_tarihi` ve `ise_baslama` bilerek sonda: kaydın/kişinin tarihi,
    olayın tarihi değildir.
    """
    puanli = [(p, k.ad) for k in t.kolonlar
              if (p := _tarih_puani(k)) is not None]
    return tuple(ad for _, ad in sorted(puanli))


def gecerlilik_adaylari(t: TabloSemasi) -> tuple[str, ...]:
    return tuple(k.ad for k in t.kolonlar if _GECERLILIK_DESEN.match(k.ad))


def maskeli_adaylari(t: TabloSemasi) -> tuple[str, ...]:
    """Kişisel veri taşıdığı düşünülen kolonlar, `tablo.kolon` biçiminde.

    Güçlü imler tek başına yeter. Zayıf im (`ad`) yalnız tabloda güçlü bir
    im daha varsa sayılır: `hasta.ad` maskelenir (yanında `tckn`, `soyad`
    var), `bolum.ad` maskelenmez.
    """
    guclu = tuple(k.ad for k in t.kolonlar if _KISISEL_GUCLU.search(k.ad))
    zayif = tuple(k.ad for k in t.kolonlar if _KISISEL_ZAYIF.match(k.ad))
    secilen = guclu + (zayif if guclu else ())
    return tuple(f"{t.ad}.{ad}" for ad in dict.fromkeys(secilen))


# --------------------------------------------------------------------------- #
#  Olay / varlık ayrımı
# --------------------------------------------------------------------------- #

def tur_tahmini(t: TabloSemasi, iliskiler: list[Iliski]) -> Tur:
    """Tek tabloya bakan yerel tahmin.

    Sinyaller, güçlüden zayıfa:
      * iki ya da daha çok dışa FK  -> işlem/bağlantı tablosu, OLAY
      * içeri işaret var, dışarı yok -> başkaları bunu tanımlıyor, VARLIK
      * dışa FK + tarih             -> OLAY
      * yalnız tarih                -> OLAY (zayıf)

    "İçeri var, dışarı yok -> VARLIK" kuralı olmadan `hasta` OLAY sanılıyordu:
    doğum tarihi olan, kimseye işaret etmeyen bir tablo. Bir varlığı olay
    sanmanın maliyeti ucuz DEĞİL — ona bir olay tarihi atanır ve tüm zaman
    filtreleri sessizce yanlış kolona düşer.
    """
    disari = sum(1 for i in iliskiler if i.kaynak == t.ad)
    iceri = sum(1 for i in iliskiler if i.hedef == t.ad)
    tarihi_var = bool(tarih_adaylari(t))
    if disari >= 2:
        return Tur.OLAY
    if iceri and not disari:
        return Tur.VARLIK
    if disari and tarihi_var:
        return Tur.OLAY
    return Tur.OLAY if tarihi_var else Tur.VARLIK


def turleri_tahmin_et(tablolar: list[TabloSemasi],
                      iliskiler: list[Iliski]) -> dict[str, Tur]:
    """Yerel tahminler + yayılım.

    Yerel tahmin `muayene`yi kaçırıyor: tarihi yok, tek FK'si var. Ama o FK
    bir OLAY tablosuna (`randevu`) gidiyor ve bir olaya işaret eden şey
    genellikle olaydır. Sabit noktaya kadar yayarız; yayılım tek yönlü
    (VARLIK -> OLAY) olduğu için döngüde takılmaz.

    Ters yön kasten yok: bir OLAY'ı VARLIK'a çeviren hiçbir kural yok, çünkü
    o yön az önce anlatılan pahalı hatayı geri getirirdi.
    """
    tur = {t.ad: tur_tahmini(t, iliskiler) for t in tablolar}
    while True:
        degisti = False
        for i in iliskiler:
            if (tur.get(i.kaynak) is Tur.VARLIK
                    and tur.get(i.hedef) is Tur.OLAY):
                tur[i.kaynak] = Tur.OLAY
                degisti = True
        if not degisti:
            return tur


# --------------------------------------------------------------------------- #
#  Kardinalite — TAHMİN DEĞİL, ÖLÇÜM
# --------------------------------------------------------------------------- #

def kardinalite_belirle(kaynak_benzersiz: bool, hedef_benzersiz: bool) -> Kardinalite:
    """Ölçülmüş benzersizliklerden kardinalite.

    `SemaKaynagi` her iki kolon için `COUNT(*) == COUNT(DISTINCT kolon)`
    ölçer; buradaki iş yalnız yorumdur, dolayısıyla saf ve testlenebilir.

    hedef benzersiz  ->  kaynak -> hedef yönünde her satır TAM BİR eş bulur
    kaynak da benzersizse -> 1:1
    hedef benzersiz DEĞİLSE -> iki yön de çoğaltır (n:n)
    """
    if not hedef_benzersiz:
        return Kardinalite.COK_COK
    return Kardinalite.BIR_BIR if kaynak_benzersiz else Kardinalite.COK_BIR


@dataclass(frozen=True)
class OlcumGirdisi:
    """Sihirbazın veritabanından topladığı ölçümler.

    Bu nesne `SemaKaynagi` tarafından doldurulur; `oner()` onu yalnız okur.
    Ayrım sayesinde ön-doldurma mantığı DB'siz test edilebiliyor.
    """

    # (tablo, kolon) -> o kolon tabloda benzersiz mi
    benzersiz: dict[tuple[str, str], bool]
    # (tablo, kolon) -> farklı değer sayısı (düşük kardinalite = boyut adayı)
    farkli_sayisi: dict[tuple[str, str], int]


@dataclass(frozen=True)
class Oneri:
    """Ön-doldurmanın çıktısı: geçersiz bir model + insanın seçeceği adaylar.

    `model` tek başına kaydedilemez (`dogrula()` reddeder). Aday listeleri
    sihirbazın açılır kutularını doldurur; hiçbiri karar değildir.
    """

    model: AnlamModeli
    tarih_adaylari: dict[str, tuple[str, ...]]
    gecerlilik_adaylari: dict[str, tuple[str, ...]]


AZAMI_BOYUT_KARDINALITESI = 50      # bunun üstü boyut değil, serbest metindir


# --------------------------------------------------------------------------- #
#  Öneri
# --------------------------------------------------------------------------- #

def _miras_adaylari(tablo: str, kendi: dict[str, tuple[str, ...]],
                    komsu: dict[str, list[str]]) -> tuple[str, ...]:
    """Kendi tarihi olmayan bir olay tablosu için nitelenmiş aday listesi.

    `muayene_islem`in tarihi yok, komşusu `muayene`nin de yok; olay zamanı
    iki sıçrama ötede, `randevu.tarih`te. Yalnız kendi kolonlarına bakan bir
    öneri buraya boş bir liste koyar ve insana "başka tablodan miras
    alabilir" deyip yalnız bırakır — cevabı bilmeyen kullanıcı da sihirbazı
    geçemez. Genişlik-öncelikli arama en yakın tarihi bulur.

    Yol GÜVENLİĞİ burada denetlenmez; kardinalite henüz ölçülmemiş olabilir.
    Bu bir aday listesidir, derleyici birleştirmeyi ayrıca reddedebilir.
    """
    gorulen = {tablo}
    sira = [tablo]
    bulunan: list[str] = []
    while sira:
        katman = sira
        sira = []
        for t in katman:
            for hedef in komsu.get(t, ()):
                if hedef in gorulen:
                    continue
                gorulen.add(hedef)
                sira.append(hedef)
                if kendi.get(hedef):
                    bulunan.append(f"{hedef}.{kendi[hedef][0]}")
        if bulunan:
            return tuple(bulunan)       # en yakın katman kazanır
    return ()


def _boyut_adi(tablo: str, kolon: str, alinmis: set[str]) -> str:
    ad = f"{tablo}_{kolon}" if kolon.lower() in _GENEL_AD else kolon
    return ad if ad not in alinmis else f"{tablo}_{kolon}"


def oner(baglanti: str, tablolar: list[TabloSemasi], iliskiler: list[Iliski],
         olcum: OlcumGirdisi | None = None) -> Oneri:
    """Şemadan doldurulmuş bir anlam modeli ÖNERİSİ üretir.

    Dönen model kasten GEÇERSİZDİR (bkz. modül başlığı): her karar alanı
    `SORULMADI` / `OLCULMEDI` / `None` durumundadır. Sihirbaz onları karara
    çevirir.
    """
    olcum = olcum or OlcumGirdisi({}, {})
    sema = {t.ad: t for t in tablolar}
    adlar = set(sema)
    turler = turleri_tahmin_et(tablolar, iliskiler)

    # İlişkileri ölçülmüş kardinaliteyle zenginleştir
    zengin: dict[str, list[Iliski]] = {ad: [] for ad in adlar}
    for i in iliskiler:
        if i.kaynak not in adlar or i.hedef not in adlar:
            continue                      # şemada olmayan tabloya köprü kurulmaz
        kb = olcum.benzersiz.get((i.kaynak, i.kaynak_kolon))
        hb = olcum.benzersiz.get((i.hedef, i.hedef_kolon))
        k = (Kardinalite.OLCULMEDI if kb is None or hb is None
             else kardinalite_belirle(kb, hb))
        zengin[i.kaynak].append(replace(i, kardinalite=k))

    anlam_tablolari: dict[str, TabloAnlami] = {}
    olculer: dict[str, Olcu] = {}
    boyutlar: dict[str, Boyut] = {}
    maskeli: set[str] = set()
    tarih_ad: dict[str, tuple[str, ...]] = {}
    gecerlilik_ad: dict[str, tuple[str, ...]] = {}

    for t in sema.values():
        maskeli |= set(maskeli_adaylari(t))

    # Kendi tarih adayları — maskeli kolonlar aday olamaz (doğum tarihi bir
    # olay tarihi değil, kişisel veridir).
    kendi_tarih = {ad: tuple(a for a in tarih_adaylari(t) if f"{ad}.{a}" not in maskeli)
                   for ad, t in sema.items()}
    komsu: dict[str, list[str]] = {ad: [] for ad in adlar}
    for i in iliskiler:
        if i.kaynak in adlar and i.hedef in adlar:
            komsu[i.kaynak].append(i.hedef)

    for ad, t in sorted(sema.items()):
        tur = turler[ad]
        if tur is Tur.OLAY:
            tarih_ad[ad] = kendi_tarih[ad] or _miras_adaylari(ad, kendi_tarih, komsu)
        gecerlilik_ad[ad] = gecerlilik_adaylari(t)

        anlam_tablolari[ad] = TabloAnlami(
            ad=ad, tur=tur,
            # Tane şemadan çıkarılamaz; bu yalnız bir başlangıç metnidir ve
            # sihirbaz insana DÜZELTTİRİR.
            tane=f"bir satır = bir {ad}",
            kolonlar=tuple(k.ad for k in t.kolonlar),
            olay_tarihi=None,                        # eksen 7 — İNSAN seçer
            gecerlilik_karari=Karar.SORULMADI,       # eksen 8 — İNSAN cevaplar
            gecerlilik=None,
            iliskiler=tuple(zengin.get(ad, ())),
        )

        # Sayım ölçüsü: hem olay hem varlık için anlamlı ("kaç randevu",
        # "kaç doktor"). Anahtar varsa BENZERSIZ_SAYIM — birleştirme
        # çoğaltsa bile sayı şişmez.
        anahtar = next((k.ad for k in t.kolonlar if k.ad == f"{ad}_id"), None)
        if anahtar or tur is Tur.OLAY:
            olculer[f"{ad}_sayisi"] = Olcu(
                ad=f"{ad}_sayisi", tablo=ad,
                ifade=f"{ad}.{anahtar}" if anahtar else "1",
                toplama=(Toplama.BENZERSIZ_SAYIM if anahtar else Toplama.SAYIM),
                birim="adet", gosterim=f"{ad.capitalize()} sayısı")

        for k in t.kolonlar:
            nitelenmis = f"{ad}.{k.ad}"
            if nitelenmis in maskeli:
                continue                            # maskeli kolon boyut olamaz
            if _sayisal_mi(k):
                olcu_ad = (f"toplam_{k.ad}" if f"toplam_{k.ad}" not in olculer
                           else f"toplam_{ad}_{k.ad}")
                olculer[olcu_ad] = Olcu(
                    ad=olcu_ad, tablo=ad, ifade=nitelenmis,
                    toplama=Toplama.TOPLAM, gosterim=f"Toplam {k.ad}")
                continue
            if _ANAHTAR.search(k.ad) or _SERBEST_METIN.match(k.ad):
                continue        # anahtar gruplanmaz, serbest metin gruplanamaz
            if _tarih_mi(k):
                # Tarih boyutları HER ZAMAN nitelenir: `tarih` adı şemada
                # tekrar eder ve çıplak hâli eşleyiciye hangi tablonun
                # tarihi olduğunu söylemez.
                b_ad = f"{ad}_{k.ad}"
                boyutlar[b_ad] = Boyut(
                    ad=b_ad, tablo=ad, kolon=k.ad,
                    gosterim=f"{ad} {k.ad}", sozluk_karari=Karar.SORULMADI,
                    tarih_mi=True)
                continue
            n = olcum.farkli_sayisi.get((ad, k.ad))
            if n is not None and n > AZAMI_BOYUT_KARDINALITESI:
                continue                    # ölçüldü: gruplanamayacak kadar çok
            b_ad = _boyut_adi(ad, k.ad, set(boyutlar))
            boyutlar[b_ad] = Boyut(
                ad=b_ad, tablo=ad, kolon=k.ad, gosterim=b_ad.replace("_", " "),
                sozluk_karari=Karar.SORULMADI)       # eksen 4 — İNSAN onaylar

    model = AnlamModeli(baglanti=baglanti, surum=1, onaylayan="",
                        tablolar=anlam_tablolari, olculer=olculer,
                        boyutlar=boyutlar, maskeli=frozenset(maskeli))
    return Oneri(model=model, tarih_adaylari=tarih_ad,
                 gecerlilik_adaylari=gecerlilik_ad)


def acik_sorular(oneri: Oneri) -> dict[str, list[str]]:
    """Sihirbazın soracağı sorular — tablo başına.

    `dogrula()` neyin eksik olduğunu zaten söylüyor; bu fonksiyon onu
    SIHIRBAZ EKRANINA uygun biçimde gruplar. İkisinin aynı kaynaktan
    beslenmesi, "doğrulama bir şey ister ama sihirbaz sormaz" boşluğunu
    imkânsız kılar.

    Tür ve maskeleme soruları, `dogrula()` şikâyet ETMESE bile sorulur:
    ikisi de sessizce yanlış olabilecek, üstelik ön-doldurmanın kendi
    tahminine dayanan alanlar. Doğrulamanın susması, insanın görmemesi
    için gerekçe değil.
    """
    model = oneri.model
    sorular: dict[str, list[str]] = {}
    for ad, t in sorted(model.tablolar.items()):
        liste: list[str] = []
        etiket = "olay (bir şey oldu)" if t.olay_mi else "varlık (bir şey var)"
        liste.append(f"Bu tablo ne? (öneri: {etiket})")
        liste.append(f"Bir satır neyi temsil ediyor? (öneri: {t.tane})")
        if t.olay_mi and not t.olay_tarihi:
            adaylar = oneri.tarih_adaylari.get(ad, ())
            ek = f" (adaylar: {', '.join(adaylar)})" if adaylar else \
                 " (bu tabloda tarih kolonu yok — başka tablodan miras alabilir)"
            liste.append(f"'Ne zaman oldu' sorusunun cevabı hangi kolon?{ek}")
        if t.gecerlilik_karari is Karar.SORULMADI:
            adaylar = oneri.gecerlilik_adaylari.get(ad, ())
            ek = f" (bakılacak kolonlar: {', '.join(adaylar)})" if adaylar else ""
            liste.append(f"Hangi satırlar sayılmamalı? (iptal, silinmiş, taslak){ek}")
        for i in t.iliskiler:
            if i.kardinalite is Kardinalite.OLCULMEDI:
                liste.append(f"'{i.hedef}' ilişkisinin kardinalitesi ölçülmedi.")
        gizli = sorted(m for m in model.maskeli if m.startswith(f"{ad}."))
        if gizli:
            liste.append("Şu kolonlar kişisel veri sayıldı, boyut olamazlar: "
                         f"{', '.join(gizli)}. Doğru mu?")
        sorular[ad] = liste
    for ad, b in sorted(model.boyutlar.items()):
        if b.sozluk_karari is Karar.SORULMADI and not b.tarih_mi:
            sorular.setdefault(b.tablo, []).append(
                f"'{ad}' hangi değerleri taşıyor? (sözlük onayı)")
    return sorular
