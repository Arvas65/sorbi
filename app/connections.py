"""Dinamik veritabanı bağlantıları (v2 — kullanıcı DB'yi arayüzden seçer).

İlkeler:
- Şifre HİÇBİR ZAMAN diske yazılmaz; yalnız oturum belleğinde tutulur.
  Profil dosyası (.sorbi/connections.json) şifresiz bağlantı bilgisi saklar.
- G-14: sqlite dosya düzeyinde salt-okunur açılır; sunucu DB'lerinde
  salt-okunur hesap kullanmak KURULUM ÖNKOŞULUDUR (arayüz uyarır).
"""
import json
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text

from app import config

PROFIL_DOSYASI = os.path.join(config.HERE, ".sorbi", "connections.json")

# tip -> (sqlalchemy şeması, varsayılan port, sürücü paketi, sorbi lehçesi)
DESTEKLENEN = {
    "sqlite":   {"scheme": "sqlite",                 "port": None, "surucu": None,              "lehce": "sqlite"},
    "postgres": {"scheme": "postgresql+psycopg2",    "port": 5432, "surucu": "psycopg2-binary", "lehce": "postgres"},
    "mysql":    {"scheme": "mysql+pymysql",          "port": 3306, "surucu": "pymysql",         "lehce": "mysql"},
    "mssql":    {"scheme": "mssql+pyodbc",           "port": 1433, "surucu": "pyodbc",          "lehce": "tsql"},
}


def build_url(tip: str, dosya: str = "", host: str = "", port: int = None,
              veritabani: str = "", kullanici: str = "", sifre: str = "") -> str:
    """Bağlantı bilgilerinden SQLAlchemy URL'si üretir."""
    if tip not in DESTEKLENEN:
        raise ValueError(f"Desteklenmeyen veritabanı tipi: {tip}")
    d = DESTEKLENEN[tip]
    if tip == "sqlite":
        return f"sqlite:///{os.path.abspath(dosya)}"
    port = port or d["port"]
    kimlik = f"{quote_plus(kullanici)}:{quote_plus(sifre)}@" if kullanici else ""
    url = f"{d['scheme']}://{kimlik}{host}:{port}/{veritabani}"
    if tip == "mssql":
        url += "?driver=ODBC+Driver+17+for+SQL+Server"
    return url


def test_connection(url: str) -> dict:
    """Bağlanmayı dener. Dönen: {ok, mesaj, tablolar}."""
    if url.startswith("sqlite:///"):
        dosya = url.replace("sqlite:///", "", 1).split("?")[0].replace("file:", "", 1)
        if not os.path.exists(dosya):
            return {"ok": False, "tablolar": [],
                    "mesaj": f"SQLite dosyası bulunamadı: {dosya}"}
    try:
        eng = create_engine(url, connect_args={"timeout": 5} if url.startswith("sqlite") else {})
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        tablolar = inspect(eng).get_table_names()
        eng.dispose()
        if not tablolar:
            return {"ok": True, "mesaj": "Bağlantı başarılı ama şemada tablo yok.", "tablolar": []}
        return {"ok": True, "mesaj": f"Bağlantı başarılı — {len(tablolar)} tablo bulundu.",
                "tablolar": tablolar}
    except ModuleNotFoundError as e:
        eksik = str(e).split("'")[1] if "'" in str(e) else str(e)
        onerilen = next((v["surucu"] for v in DESTEKLENEN.values()
                         if v["surucu"] and eksik in v["surucu"].replace("-", "_")), eksik)
        return {"ok": False, "tablolar": [],
                "mesaj": f"Sürücü kurulu değil: {eksik}. Kurulum: pip install {onerilen}"}
    except Exception as e:
        return {"ok": False, "tablolar": [], "mesaj": f"Bağlanılamadı: {str(e)[:200]}"}


def aktifle(url: str, lehce: str) -> None:
    """Aktif bağlantıyı değiştirir: config güncellenir, RAG indeksi sıfırlanır."""
    config.DB_URL = url
    config.TARGET_DIALECT = lehce
    from app import pipeline
    pipeline.reset_index()


# ---------------- Profiller (şifresiz) ----------------

def profilleri_yukle() -> dict:
    try:
        with open(PROFIL_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def profil_kaydet(ad: str, bilgiler: dict) -> None:
    """Şifre alanı bilinçli olarak ATILIR — diske yazılmaz."""
    bilgiler = {k: v for k, v in bilgiler.items() if k != "sifre"}
    profiller = profilleri_yukle()
    profiller[ad] = bilgiler
    os.makedirs(os.path.dirname(PROFIL_DOSYASI), exist_ok=True)
    with open(PROFIL_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(profiller, f, ensure_ascii=False, indent=2)


def profil_sil(ad: str) -> None:
    profiller = profilleri_yukle()
    profiller.pop(ad, None)
    with open(PROFIL_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(profiller, f, ensure_ascii=False, indent=2)
