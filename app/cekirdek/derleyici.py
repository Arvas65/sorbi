"""Derleyici (İP-47, SPEC B-2) — `Secim` + `AnlamModeli` -> SQL.

ADR-8'in kalbi: **model SQL yazmaz, seçim yapar; SQL burada derlenir.** Bu
modülün tamamı deterministiktir ve LLM görmez; dolayısıyla altın çiftlerle
saniyeler içinde sınanabilir (cetvel Katman 1).

Derleyicinin OTOMATİK ve ZORUNLU yaptıkları — hiçbiri unutulamaz, çünkü
hiçbiri istem disiplinine bırakılmamıştır:

1. **Geçerlilik filtresi eklenir** (eksen 8). Sorguya giren her tablonun
   `gecerlilik` ifadesi WHERE'e AND'lenir. İptal edilmiş randevular sayıma
   giremez.
2. **Doğru olay tarihi kullanılır** (eksen 7). Zaman kısıtı, tabloların
   `olay_tarihi` alanına uygulanır; model tarih kolonu SEÇEMEZ.
3. **JOIN yolu modelden gelir**, uydurulmaz — ve yalnız ÇOĞALTMAYAN yönde
   yürünür (aşağıya bak).
4. **Toplama kuralı uygulanır.** `ifade` yalnız toplanacak değeri taşır;
   fonksiyonu `toplama` belirler. Ortalamanın ortalaması reddedilir.
5. **Maskeli kolona dokunan seçim derleme anında reddedilir** (SPEC E-5).
6. Üretilen SQL sqlite lehçesinde yazılır ve `validator` tarafından hedef
   lehçeye çevrilir (ADR-4) — derinlemesine savunma: derlenmiş SQL de kapıdan
   geçer.

## Çoğaltma (fan-out) kuralı — ölçülmüş bir gerekçe

`demo/hospital.db` üzerinde ölçüldü (2026-08-30):

    Toplam ciro                                : 14.574.050
    Aynı ciro, muayene_islem ile birleştirilmiş: 34.222.000   (2,35x)

`muayene_islem` bir muayeneye birden çok işlem bağlar. "İşlem bazında ciro"
sorusu, saf bir JOIN ile ciroyu iki katından fazlasına çıkarır: sorgu çalışır,
tablo döner, sayı yanlıştır ve hiçbir güven kontrolü yakalayamaz.

Aynı şemada `randevu -> muayene -> fatura` ise gerçek bir 1:1 ZİNCİRDİR
(6000 -> 4182 -> 4182, birleştirme sonrası hâlâ 4182). Zinciri yasaklamak
bilgi kaybı olurdu.

Kural bu ikisini ayırır: **yalnız çoğaltmayan yönde yürü.**

    kaynak -> hedef    n:1 ya da 1:1  ->  serbest
    hedef -> kaynak    yalnız 1:1     ->  serbest
    diğer her durum                   ->  REDDET, sebebi yazılarak
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import sqlglot

from app.cekirdek.anlam import AnlamModeli, Olcu
from app.cekirdek.secim import Secim
from app.cekirdek.tipler import Iliski, Toplama, Tur, ZamanTanesi

# Toplama -> SQL fonksiyonu
_FONKSIYON = {
    Toplama.SAYIM: "COUNT",
    Toplama.BENZERSIZ_SAYIM: "COUNT",
    Toplama.TOPLAM: "SUM",
    Toplama.ORTALAMA: "AVG",
    Toplama.EN_AZ: "MIN",
    Toplama.EN_COK: "MAX",
}

# Zaman tanesi -> sqlite ifadesi. Model sqlite lehçesinde yazılır, hedef
# lehçeye `validator` çevirir (ADR-4). Lehçe farkı DERLEYİCİNİN işidir;
# çağıranın değil.
_TANE = {
    ZamanTanesi.GUN: "STRFTIME('%Y-%m-%d', {k})",
    ZamanTanesi.HAFTA: "STRFTIME('%Y-W%W', {k})",
    ZamanTanesi.AY: "STRFTIME('%Y-%m', {k})",
    ZamanTanesi.YIL: "STRFTIME('%Y', {k})",
    ZamanTanesi.CEYREK:
        "STRFTIME('%Y', {k}) || '-Q' || "
        "CAST((CAST(STRFTIME('%m', {k}) AS INTEGER) + 2) / 3 AS TEXT)",
}


@dataclass(frozen=True)
class DerlemeSonucu:
    sql: str = ""
    gecersiz: tuple[str, ...] = ()
    tablolar: tuple[str, ...] = ()
    uygulanan_gecerlilikler: tuple[str, ...] = ()
    notlar: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.sql) and not self.gecersiz


# --------------------------------------------------------------------------- #
#  Birleştirme grafiği — yalnız çoğaltmayan kenarlar
# --------------------------------------------------------------------------- #

def _kenarlar(model: AnlamModeli) -> dict[str, list[tuple[str, Iliski, bool]]]:
    """dugum -> [(komsu, iliski, ileri_mi)]. Çoğaltan yön HİÇ EKLENMEZ."""
    g: dict[str, list[tuple[str, Iliski, bool]]] = {ad: [] for ad in model.tablolar}
    for t in model.tablolar.values():
        for i in t.iliskiler:
            if i.kaynak not in g or i.hedef not in g:
                continue
            if i.kardinalite.ileri_guvenli:
                g[i.kaynak].append((i.hedef, i, True))
            if i.kardinalite.geri_guvenli:
                g[i.hedef].append((i.kaynak, i, False))
    return g


def _yol(g, baslangic: str, hedef: str) -> list[tuple[Iliski, bool]] | None:
    """En kısa çoğaltmayan yol. Yoksa None."""
    if baslangic == hedef:
        return []
    gorulen = {baslangic}
    kuyruk: deque[tuple[str, list[tuple[Iliski, bool]]]] = deque([(baslangic, [])])
    while kuyruk:
        dugum, yol = kuyruk.popleft()
        for komsu, iliski, ileri in g.get(dugum, ()):
            if komsu in gorulen:
                continue
            yeni = [*yol, (iliski, ileri)]
            if komsu == hedef:
                return yeni
            gorulen.add(komsu)
            kuyruk.append((komsu, yeni))
    return None


def _cogaltan_yol_var_mi(model: AnlamModeli, a: str, b: str) -> bool:
    """İki tablo arasında HERHANGİ bir ilişki yolu var mı (yön gözetmeksizin)?

    Güvenli yol bulunamadığında hata iletisini doğru yazabilmek için: yol
    hiç yoksa "ilişki tanımlı değil", varsa "çoğaltır" denir. İkisi çok
    farklı sorunlardır ve kullanıcıya farklı şey yaptırır.
    """
    tum: dict[str, set[str]] = {ad: set() for ad in model.tablolar}
    for t in model.tablolar.values():
        for i in t.iliskiler:
            if i.kaynak in tum and i.hedef in tum:
                tum[i.kaynak].add(i.hedef)
                tum[i.hedef].add(i.kaynak)
    gorulen, kuyruk = {a}, deque([a])
    while kuyruk:
        d = kuyruk.popleft()
        for k in tum.get(d, ()):
            if k == b:
                return True
            if k not in gorulen:
                gorulen.add(k)
                kuyruk.append(k)
    return False


# --------------------------------------------------------------------------- #
#  Parçalar
# --------------------------------------------------------------------------- #

def _olcu_ifadesi(o: Olcu) -> str:
    """Toplama fonksiyonunu ifadenin ETRAFINA koyar.

    `kaynak_kosulu` (eksen 2+3) CASE WHEN olarak fonksiyonun İÇİNE girer —
    dışına konsaydı bütün satırları filtreler ve diğer ölçüleri bozardı.
    """
    ic = o.ifade
    if o.kaynak_kosulu:
        ic = f"CASE WHEN {o.kaynak_kosulu} THEN {o.ifade} END"
    if o.toplama is Toplama.BENZERSIZ_SAYIM:
        return f"COUNT(DISTINCT {ic})"
    return f"{_FONKSIYON[o.toplama]}({ic})"


def _tirnak(deger: str) -> str:
    return "'" + str(deger).replace("'", "''") + "'"


def _ham_deger(model: AnlamModeli, boyut_adi: str, deger: str) -> str:
    """Gösterim değerini ham değere çevirir (eksen 4).

    Kullanıcı ya da model 'Kadın' der; kolonda 'K' vardır. Sözlük iki yönlü
    okunur; eşleşme yoksa değer olduğu gibi bırakılır — `Secim.kur()` zaten
    sözlük dışı değeri reddetmiştir.
    """
    b = model.boyutlar.get(boyut_adi)
    if not b or not b.sozluk:
        return deger
    if deger in b.sozluk:
        return deger
    for ham, gosterim in b.sozluk.items():
        if gosterim == deger:
            return ham
    return deger


def _filtre_kosulu(model: AnlamModeli, f) -> str | None:
    b = model.boyutlar.get(f.boyut)
    if b is None:
        return None
    kolon = f"{b.tablo}.{b.kolon}"
    degerler = [_tirnak(_ham_deger(model, f.boyut, d)) for d in f.degerler]
    if f.islec in ("esittir", "esit_degil") and degerler:
        islec = "=" if f.islec == "esittir" else "<>"
        return f"{kolon} {islec} {degerler[0]}"
    if f.islec == "icinde" and degerler:
        return f"{kolon} IN ({', '.join(degerler)})"
    if f.islec == "araliginda" and len(degerler) >= 2:
        return f"{kolon} BETWEEN {degerler[0]} AND {degerler[1]}"
    if f.islec in ("buyuk", "kucuk") and degerler:
        return f"{kolon} {'>' if f.islec == 'buyuk' else '<'} {degerler[0]}"
    if f.islec == "icerir" and degerler:
        icerik = degerler[0][1:-1]
        return f"{kolon} LIKE '%{icerik}%'"
    return None


# --------------------------------------------------------------------------- #
#  Derleme
# --------------------------------------------------------------------------- #

def derle(secim: Secim, model: AnlamModeli,
          lehce: str = "sqlite") -> DerlemeSonucu:
    """Seçimi SQL'e çevirir. İSTİSNA FIRLATMAZ — kapalı devre."""
    try:
        return _derle(secim, model, lehce)
    except Exception as e:                          # noqa: BLE001
        return DerlemeSonucu(gecersiz=(f"Sorgu derlenemedi "
                                       f"({type(e).__name__}: {e}).",))


def _derle(secim: Secim, model: AnlamModeli, lehce: str) -> DerlemeSonucu:
    if not secim.kurulabilir:
        return DerlemeSonucu(gecersiz=secim.gecersiz or ("Seçim kurulabilir değil.",))

    olculer = [model.olculer[a] for a in secim.olculer]
    boyutlar = [model.boyutlar[a] for a in secim.boyutlar]
    sorunlar: list[str] = []
    notlar: list[str] = []

    # E-5: maskeli kolona dokunan seçim SQL'e HİÇ dönüşmez.
    for b in boyutlar:
        if f"{b.tablo}.{b.kolon}" in model.maskeli:
            sorunlar.append(f"'{b.ad}' maskeli bir kolonu ({b.tablo}.{b.kolon}) "
                            "gösteriyor; bu sorgu üretilmez.")
    for o in olculer:
        for maskeli in model.maskeli:
            if maskeli.split(".")[-1] and maskeli in (o.ifade or ""):
                sorunlar.append(f"'{o.ad}' ölçüsü maskeli bir kolona ({maskeli}) "
                                "dayanıyor; bu sorgu üretilmez.")
    if sorunlar:
        return DerlemeSonucu(gecersiz=tuple(sorunlar))

    # Ortalamanın ortalaması: birden çok ölçü varsa ve biri yeniden
    # toplanamıyorsa, o ölçü başka bir tane (grain) üzerinde toplanamaz.
    for o in olculer:
        if not o.yeniden_toplanabilir and o.uyari:
            notlar.append(f"{o.ad}: {o.uyari}")

    g = _kenarlar(model)
    # Filtrelenen boyutun tablosu da GEREKLİDİR: gruplanmasa bile
    # birleştirilmezse WHERE'de birleştirilmemiş bir tabloya atıf kalır.
    # (Build hatası, 2026-08-30: `hasta.cinsiyet` filtresi üretiliyor ama
    #  `JOIN hasta` yoktu. Duman testi yakaladı, birim test değil.)
    filtre_tablolari = {model.boyutlar[f.boyut].tablo for f in secim.filtreler
                        if f.boyut in model.boyutlar}
    gerekli = ({o.tablo for o in olculer} | {b.tablo for b in boyutlar}
               | filtre_tablolari)

    # Taban seçimi: ölçü tablolarından, DİĞER her gerekli tabloya çoğaltmayan
    # yolu olan ilki. Ölçü hangi tablodaysa sorgunun tanesi odur.
    taban = None
    yollar: dict[str, list[tuple[Iliski, bool]]] = {}
    for aday in [o.tablo for o in olculer]:
        deneme = {}
        for hedef in gerekli:
            y = _yol(g, aday, hedef)
            if y is None:
                break
            deneme[hedef] = y
        else:
            taban, yollar = aday, deneme
            break

    if taban is None:
        ilk = olculer[0].tablo
        eksik = [h for h in sorted(gerekli) if _yol(g, ilk, h) is None]
        for h in eksik:
            if _cogaltan_yol_var_mi(model, ilk, h):
                sorunlar.append(
                    f"'{ilk}' ile '{h}' arasındaki tek yol ölçüyü ÇOĞALTIR "
                    f"(bir '{ilk}' satırı birden çok '{h}' satırıyla eşleşir). "
                    "Bu sorgu, sayıyı sessizce şişireceği için üretilmedi. "
                    f"'{h}' kırılımını istiyorsanız ölçünün '{h}' tarafında "
                    "tanımlanması gerekir.")
            else:
                sorunlar.append(f"'{ilk}' ile '{h}' arasında tanımlı bir ilişki yok.")
        return DerlemeSonucu(gecersiz=tuple(sorunlar))

    # ---------------------------------------------------------------- SELECT
    secilenler: list[str] = []
    gruplar: list[str] = []
    zaman = secim.zaman
    for b in boyutlar:
        kolon = f"{b.tablo}.{b.kolon}"
        ifade = kolon
        if b.tarih_mi and zaman is not None:
            ifade = _TANE[zaman.tane].format(k=kolon)
        secilenler.append(f"{ifade} AS {b.ad}")
        gruplar.append(ifade)
    for o in olculer:
        secilenler.append(f"{_olcu_ifadesi(o)} AS {o.ad}")

    # ------------------------------------------------------------------ FROM
    parcalar = [f"FROM {taban}"]
    katilan = {taban}
    for hedef in sorted(gerekli):
        for iliski, ileri in yollar[hedef]:
            yeni = iliski.hedef if ileri else iliski.kaynak
            if yeni in katilan:
                continue
            parcalar.append(
                f"JOIN {yeni} ON {iliski.kaynak}.{iliski.kaynak_kolon} "
                f"= {iliski.hedef}.{iliski.hedef_kolon}")
            katilan.add(yeni)

    # ----------------------------------------------------------------- WHERE
    kosullar: list[str] = []
    gecerlilikler: list[str] = []
    for ad in sorted(katilan):
        t = model.tablolar[ad]
        if t.gecerlilik:
            kosullar.append(f"({t.gecerlilik})")
            gecerlilikler.append(f"{ad}: {t.gecerlilik}")

    for f in secim.filtreler:
        k = _filtre_kosulu(model, f)
        if k:
            kosullar.append(k)

    if zaman is not None and (zaman.baslangic or zaman.bitis):
        tarih = None
        for ad in sorted(katilan):
            t_ = model.tablolar[ad]
            if t_.tur is not Tur.OLAY or not t_.olay_tarihi:
                continue
            if "." in t_.olay_tarihi:
                # Miras alınan tarih. Kaynak tablo sorguda yoksa GÜVENLİ bir
                # yolla eklenir — reddetmek yerine. Reddetmek "bu yıl kaç işlem
                # yapıldı" gibi meşru bir soruyu cevapsız bırakırdı; eklemek
                # ise yalnız çoğaltmayan yolla mümkün olduğu için sayıyı
                # bozamaz.
                kaynak = t_.olay_tarihi.split(".", 1)[0]
                if kaynak in katilan:
                    tarih = t_.olay_tarihi
                    break
                ek = _yol(g, ad, kaynak)
                if ek is not None:
                    for iliski, ileri in ek:
                        yeni_t = iliski.hedef if ileri else iliski.kaynak
                        if yeni_t in katilan:
                            continue
                        parcalar.append(
                            f"JOIN {yeni_t} ON {iliski.kaynak}.{iliski.kaynak_kolon} "
                            f"= {iliski.hedef}.{iliski.hedef_kolon}")
                        katilan.add(yeni_t)
                        gt = model.tablolar[yeni_t]
                        if gt.gecerlilik:
                            kosullar.append(f"({gt.gecerlilik})")
                            gecerlilikler.append(f"{yeni_t}: {gt.gecerlilik}")
                    tarih = t_.olay_tarihi
                    notlar.append(f"zaman için '{kaynak}' birleştirildi "
                                  f"({ad} kendi tarihini taşımıyor)")
                    break
            else:
                tarih = f"{ad}.{t_.olay_tarihi}"
                break
        if tarih is None:
            return DerlemeSonucu(gecersiz=(
                "Zaman filtresi istendi ama sorguda olay tarihi olan bir tablo yok.",))
        if zaman.baslangic:
            kosullar.append(f"{tarih} >= {_tirnak(zaman.baslangic)}")
        if zaman.bitis:
            kosullar.append(f"{tarih} <= {_tirnak(zaman.bitis)}")
        notlar.append(f"zaman kısıtı {tarih} üzerinden uygulandı")

    # ------------------------------------------------------------ birleştir
    sql = ["SELECT " + ", ".join(secilenler), *parcalar]
    if kosullar:
        sql.append("WHERE " + " AND ".join(kosullar))
    if gruplar:
        sql.append("GROUP BY " + ", ".join(gruplar))
    if secim.sirala:
        ad, _, yon = secim.sirala.rpartition(" ")
        sql.append(f"ORDER BY {ad or secim.sirala} "
                   f"{'DESC' if yon.lower().startswith('azal') else 'ASC'}")
    if secim.limit:
        sql.append(f"LIMIT {int(secim.limit)}")

    ham = "\n".join(sql)
    try:
        cikti = sqlglot.transpile(ham, read="sqlite", write=lehce, pretty=True)[0]
    except Exception as e:                          # noqa: BLE001
        return DerlemeSonucu(gecersiz=(f"Üretilen SQL '{lehce}' lehçesine "
                                       f"çevrilemedi: {e}",))

    return DerlemeSonucu(sql=cikti, tablolar=tuple(sorted(katilan)),
                         uygulanan_gecerlilikler=tuple(gecerlilikler),
                         notlar=tuple(notlar))
