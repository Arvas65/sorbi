"""Salt-okunur yürütme (G-14) — 30 sn zaman aşımı + satır limiti."""
import threading
import time
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text

from app import config


@dataclass
class ExecResult:
    status: str                 # BASARILI | ZAMAN_ASIMI | CALISMA_HATASI
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    rowcount: int = 0
    elapsed_s: float = 0.0
    error: str = ""


def _readonly_url(url: str) -> str:
    """SQLite için dosya düzeyinde salt-okunur aç; diğer DB'lerde salt-okunur
    hesap kullanılması kurulum önkoşuludur (G-14 — README güvenlik bölümü)."""
    if url.startswith("sqlite:///") and "mode=ro" not in url:
        return url.replace("sqlite:///", "sqlite:///file:", 1) + "?mode=ro&uri=true"
    return url


def run(sql: str, db_url: str = None, timeout_s: int = None, max_rows: int = None) -> ExecResult:
    db_url = _readonly_url(db_url or config.DB_URL)
    timeout_s = timeout_s or config.QUERY_TIMEOUT_S
    max_rows = max_rows or config.MAX_ROWS

    eng = create_engine(db_url, connect_args={"check_same_thread": False}
                        if db_url.startswith("sqlite") else {})
    result = ExecResult(status="CALISMA_HATASI")
    start = time.time()
    conn = eng.connect()

    # SQLite: ayrı zamanlayıcıyla interrupt (K3 kapısı)
    timer = None
    raw = getattr(conn.connection, "driver_connection", None) or conn.connection
    if hasattr(raw, "interrupt"):
        timer = threading.Timer(timeout_s, raw.interrupt)
        timer.start()

    try:
        rs = conn.execute(text(sql))
        cols = list(rs.keys())
        rows = rs.fetchmany(max_rows)
        result = ExecResult(status="BASARILI", columns=cols,
                            rows=[list(r) for r in rows], rowcount=len(rows))
    except Exception as e:
        msg = str(e)
        if "interrupt" in msg.lower():
            result = ExecResult(status="ZAMAN_ASIMI",
                                error=f"Sorgu {timeout_s} saniyede tamamlanamadı ve iptal edildi. "
                                      "Soruyu daraltmayı deneyin (ör. tarih aralığı ekleyin).")
        else:
            result = ExecResult(status="CALISMA_HATASI", error=msg)
    finally:
        if timer:
            timer.cancel()
        result.elapsed_s = round(time.time() - start, 2)
        conn.close()
        eng.dispose()
    return result
