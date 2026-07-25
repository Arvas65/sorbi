"""Denetim izi (G-17): kim - ne zaman - hangi soru - hangi sorgu - kaç satır.
Ekleme-yalnız (append-only) tablo; uygulama içinden güncelleme/silme yolu yoktur.
Sonuç VERİSİ saklanmaz, yalnız satır sayısı (Böl. 9 KVKK kararı)."""
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
    elle_yazildi INTEGER DEFAULT 0   -- kontrollü bypass bayrağı (Böl. 12)
)"""


def write(kullanici: str, soru: str, sql: str, durum: str, satir_sayisi: int = 0,
          mod: str = "local", sure_s: float = 0.0, elle_yazildi: bool = False) -> None:
    con = sqlite3.connect(config.AUDIT_DB)
    con.execute(_DDL)
    con.execute("INSERT INTO denetim (zaman, kullanici, soru, sql, durum, satir_sayisi, mod, sure_s, elle_yazildi) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), kullanici, soru, sql, durum,
                 satir_sayisi, mod, sure_s, int(elle_yazildi)))
    con.commit()
    con.close()


def recent(limit: int = 50) -> list[tuple]:
    con = sqlite3.connect(config.AUDIT_DB)
    con.execute(_DDL)
    rows = con.execute("SELECT zaman, kullanici, soru, durum, satir_sayisi, mod, sure_s "
                       "FROM denetim ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return rows
