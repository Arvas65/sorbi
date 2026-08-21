"""Ölçüm koşumlarında SQL'in 'bugün'ünü sabitler (İP-23).

Neden gerekli — 2026-08-20'de bulundu:

Test setinin 101 sorusundan 13'ü zamana bağlı ("geçen ay", "son 7 gün",
"bugün bekleyen"). Demo verisi 2026-08-16'da tohumlandı ve orada bitiyor.
Gerçek takvim ilerledikçe bu sorular sessizce boşaldı:

    "Bugün bekleyen kaç randevu var?"  16 Ağustos: gerçek bir sayı
                                       20 Ağustos: HER ZAMAN 0

Sonuç: kod hiç değişmeden mutasyon karnesi 199/240'tan 198/239'a kaydı.
İki ölçüm arasındaki farkın koda mı takvime mi ait olduğu ayırt edilemez
hale gelmişti. Cetvel çürüyordu.

Burada yapılan: ölçüm anında SQL'deki `'now'` referansları sabit bir güne
çevrilir. Hem gold hem üretilen sorguya uygulanır — ikisi de aynı günü
görmezse karşılaştırma anlamsızlaşır. Üretimde kullanılmaz; orada 'bugün'
gerçekten bugündür.

Sınır: yalnız FONKSİYON ARGÜMANI konumundaki `'now'` değiştirilir
(`date('now')`, `strftime('%Y-%m','now')`). `WHERE durum = 'now'` gibi bir
veri değeri korunur.
"""
import re

from app import config

# Veritabanı okunamazsa kullanılacak son çare. Buna DÜŞMEK istemiyoruz:
# sabit bir gün, yazıldığı makinenin verisine aittir (aşağıya bakın).
YEDEK_GUN = "2026-08-16"

# İlk sürümde referans gün SABİTTİ ve bu bir hataydı. Sabit, benim demo
# veritabanımdan türetilmişti; İhsan'ın kopyası başka bir günde tohumlanmıştı
# ve aynı sabit onun makinesinde üç soruyu boşa düşürüp 4 gereksiz bayrak
# üretti (2026-08-21 koşumu). Ölçüm günü VERİDEN türetilmeli — makineye
# değil, veriye ait bir sayıdır.
_ONBELLEK: dict[str, str] = {}

# Kişi niteliği olan tarihler olay tarihi değildir; doğum tarihi yıllar
# öncesine düşer ve "verinin son günü" hesabını bozar.
_ES_ALINMAZ = ("dogum", "birth", "ise_bas", "baslama")

# Bir kolonun "canlı" sayılması için genel sondan en fazla bu kadar geride
# olabileceği gün sayısı. Nitelik kolonlarını olay kolonlarından ayırır.
_CANLI_PENCERE_GUN = 90


def veri_gunu(db_url: str | None = None) -> str | None:
    """Verinin bildiği son gün: HER canlı tablonun hâlâ kaydı olduğu son gün.

    Neden maksimum değil minimum: tablolar farklı günlerde bitiyor
    (fatura 19'unda, randevu 16'sında, yatış 14'ünde). Genel maksimumu
    seçersek "bugün bekleyen randevu" sorusu boş döner ve soru bir şey
    ölçmez hâle gelir. Her tablonun hâlâ dolu olduğu son gün, zamana bağlı
    13 sorunun tamamının anlamlı kaldığı gündür.
    """
    from datetime import date, timedelta

    from sqlalchemy import create_engine, inspect, text

    url = db_url or config.DB_URL
    if url in _ONBELLEK:
        return _ONBELLEK[url]
    try:
        eng = create_engine(url)
        insp = inspect(eng)
        prep = eng.dialect.identifier_preparer
        sonlar = []
        with eng.connect() as conn:
            for t in insp.get_table_names():
                for k in insp.get_columns(t):
                    ad = k["name"]
                    dl = ad.lower()
                    tarihsel = "tarih" in dl or "date" in str(k.get("type", "")).lower()
                    if not tarihsel or any(x in dl for x in _ES_ALINMAZ):
                        continue
                    sorgu = f"SELECT MAX({prep.quote(ad)}) FROM {prep.quote(t)}"  # noqa: S608
                    deger = conn.execute(text(sorgu)).scalar()
                    if isinstance(deger, str) and len(deger) >= 10:
                        sonlar.append(deger[:10])
                    elif hasattr(deger, "isoformat"):
                        sonlar.append(deger.isoformat()[:10])
        eng.dispose()
        if not sonlar:
            return None
        en_son = max(sonlar)
        esik = (date.fromisoformat(en_son) - timedelta(days=_CANLI_PENCERE_GUN)).isoformat()
        canli = [g for g in sonlar if g >= esik]
        gun = min(canli) if canli else en_son
        _ONBELLEK[url] = gun
        return gun
    except Exception:      # noqa: BLE001 - türetme başarısızsa ölçüm yine koşar
        return None


def olcum_gunu() -> str:
    """Ölçümlerin sabitleneceği gün.

    Sıra: SORBI_BUGUN (elle) → veriden türetilen gün → yedek sabit.
    Hangisi kullanıldıysa koşum başlığına ve kanıt damgasına yazılır.
    """
    if config.BUGUN:
        config.bugun()          # biçim doğrulaması; bozuksa burada patlar
        return config.BUGUN
    return veri_gunu() or YEDEK_GUN


# `(` ya da `,` ile başlayan konum = fonksiyon argümanı.
_NOW = re.compile(r"([(,]\s*)'now'", re.IGNORECASE)


def sabitle(sql: str, gun) -> str:
    """SQL'deki 'now' argümanlarını `gun`e sabitler. `gun` None ise dokunmaz."""
    if not sql or gun is None:
        return sql
    return _NOW.sub(lambda m: f"{m.group(1)}'{gun}'", sql)


def sayac(sql: str) -> int:
    """Kaç yerde sabitleme yapılacağı — teşhis ve test için."""
    return len(_NOW.findall(sql or ""))
