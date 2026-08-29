"""Denetim izi (G-17): kim - ne zaman - hangi soru - hangi sorgu - kaç satır.
Ekleme-yalnız (append-only) tablo; uygulama içinden güncelleme/silme yolu yoktur.
Sonuç VERİSİ saklanmaz, yalnız satır sayısı (Böl. 9 KVKK kararı).

B7R-05 (2026-08-23): güven bayrakları da yazılıyor. Eskiden yalnız kullanıcıya
gösteriliyordu ve ekran kapanınca kayboluyordu — "bu uyarı ne zaman çıktı",
"şu kontrol sahada kaç kez konuştu" sorularının cevabı hiçbir yerde yoktu.
Oysa B-7'nin SAHA karnesi (mutasyon karnesi değil) tam olarak bu veriyle
ölçülebilir hale gelir; BULGU-04'ün ayırmayı istediği iki sayıdan biri budur.

Saklanan şey KODLAR, mesaj metni değil: kod bir sözleşmedir, mesaj değişir.
"""
import sqlite3
from datetime import datetime, timezone

from app import config

_DDL = """CREATE TABLE IF NOT EXISTS denetim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zaman TEXT NOT NULL,
    kullanici TEXT NOT NULL,
    soru TEXT NOT NULL,
    sql TEXT,
    durum TEXT NOT NULL,        -- BASARILI | SOZDIZIM_RED | ZAMAN_ASIMI | CALISMA_HATASI | DUSUK_GUVEN
    satir_sayisi INTEGER,
    mod TEXT,                   -- local | api
    sure_s REAL,
    elle_yazildi INTEGER DEFAULT 0,  -- kontrollü bypass bayrağı (Böl. 12)
    guven_kodlari TEXT               -- B-7 bayrak kodları, virgülle (B7R-05)
)"""


def _goc(con) -> None:
    """Var olan kurulumda tablo eski şemayla oluşmuştur.

    Denetim izi ekleme-yalnızdır; tabloyu silip yeniden yaratmak kaydı yok
    etmek demek olurdu. Kolonu yerinde eklemek tek doğru yol.
    """
    kolonlar = {r[1] for r in con.execute("PRAGMA table_info(denetim)")}
    if "guven_kodlari" not in kolonlar:
        con.execute("ALTER TABLE denetim ADD COLUMN guven_kodlari TEXT")


def _baglan():
    con = sqlite3.connect(config.AUDIT_DB)
    con.execute(_DDL)
    _goc(con)
    return con


def write(kullanici: str, soru: str, sql: str, durum: str, satir_sayisi: int = 0,
          mod: str = "local", sure_s: float = 0.0, elle_yazildi: bool = False,
          guven_kodlari=None) -> None:
    con = _baglan()
    con.execute(
        "INSERT INTO denetim (zaman, kullanici, soru, sql, durum, satir_sayisi, "
        "mod, sure_s, elle_yazildi, guven_kodlari) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), kullanici, soru, sql, durum,
         satir_sayisi, mod, sure_s, int(elle_yazildi),
         ",".join(guven_kodlari) if guven_kodlari else None))
    con.commit()
    con.close()


def recent(limit: int = 50) -> list[tuple]:
    con = _baglan()
    rows = con.execute("SELECT zaman, kullanici, soru, durum, satir_sayisi, mod, sure_s, "
                       "guven_kodlari FROM denetim ORDER BY id DESC LIMIT ?",
                       (limit,)).fetchall()
    con.close()
    return rows


def guven_karnesi(limit: int = 1000) -> dict[str, int]:
    """Sahada hangi B-7 kontrolü kaç kez konuştu.

    Mutasyon karnesi bizim HAYAL ETTİĞİMİZ hatalar üzerinde ölçer; bu sayaç
    aynı kontrollerin GERÇEK sorularda kaç kez ateşlediğini verir. İkisi ayrı
    şeydir ve BULGU-04 tam olarak bu ikisinin karıştırılmasıydı: mutasyonda
    %80, gerçek model hatalarında %20.

    Bu bir isabet oranı DEĞİLDİR — bayrağın haklı olup olmadığını bilmiyoruz.
    Yalnız hangi kontrolün sahada sesli, hangisinin sessiz olduğunu söyler.
    """
    con = _baglan()
    satirlar = con.execute(
        "SELECT guven_kodlari FROM denetim WHERE guven_kodlari IS NOT NULL "
        "AND guven_kodlari != '' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    sayac: dict[str, int] = {}
    for (kodlar,) in satirlar:
        for k in kodlar.split(","):
            if k:
                sayac[k] = sayac.get(k, 0) + 1
    return dict(sorted(sayac.items(), key=lambda x: -x[1]))
