"""SorBI demo 2: farklı şemalı sentetik SATIŞ veritabanı.
Amaç: dinamik bağlantı geçişini (Bağlantı Yöneticisi) farklı bir şemayla denemek.
Kullanım: python demo/seed_satis.py  ->  demo/satis.db
"""
import os
import random
import sqlite3
from datetime import date, timedelta

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "satis.db")

DDL = """
CREATE TABLE musteri (
    musteri_id  INTEGER PRIMARY KEY,
    unvan       TEXT NOT NULL,
    sehir       TEXT NOT NULL,
    segment     TEXT NOT NULL           -- KURUMSAL | BIREYSEL
);
CREATE TABLE urun (
    urun_id     INTEGER PRIMARY KEY,
    ad          TEXT NOT NULL,
    kategori    TEXT NOT NULL,
    birim_fiyat REAL NOT NULL
);
CREATE TABLE siparis (
    siparis_id  INTEGER PRIMARY KEY,
    musteri_id  INTEGER NOT NULL REFERENCES musteri(musteri_id),
    tarih       DATE NOT NULL,
    durum       TEXT NOT NULL           -- TESLIM | KARGODA | IPTAL
);
CREATE TABLE siparis_kalemi (
    siparis_id  INTEGER NOT NULL REFERENCES siparis(siparis_id),
    urun_id     INTEGER NOT NULL REFERENCES urun(urun_id),
    adet        INTEGER NOT NULL,
    PRIMARY KEY (siparis_id, urun_id)
);
"""

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]
KATEGORILER = [("Laptop", 45000), ("Monitör", 12000), ("Klavye", 1500),
               ("Mouse", 800), ("Kulaklık", 3500), ("Dock", 5500)]

if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.executescript(DDL)

for i in range(1, 81):
    con.execute("INSERT INTO musteri VALUES (?,?,?,?)",
                (i, f"Müşteri-{i:03d}", random.choice(SEHIRLER),
                 random.choice(["KURUMSAL"] * 3 + ["BIREYSEL"] * 7)))

for i, (ad, fiyat) in enumerate(KATEGORILER, 1):
    for j in range(1, 4):
        con.execute("INSERT INTO urun VALUES (?,?,?,?)",
                    ((i - 1) * 3 + j, f"{ad} Model-{j}", ad,
                     round(fiyat * random.uniform(0.8, 1.3), 2)))

bugun = date(2026, 7, 25)
sid = 0
for _ in range(600):
    sid += 1
    con.execute("INSERT INTO siparis VALUES (?,?,?,?)",
                (sid, random.randint(1, 80),
                 (bugun - timedelta(days=random.randint(0, 365))).isoformat(),
                 random.choice(["TESLIM"] * 8 + ["KARGODA"] + ["IPTAL"])))
    for uid in random.sample(range(1, 19), random.randint(1, 4)):
        con.execute("INSERT INTO siparis_kalemi VALUES (?,?,?)",
                    (sid, uid, random.randint(1, 5)))

con.commit()
for t in ["musteri", "urun", "siparis", "siparis_kalemi"]:
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t:16s} {n:6d} satır")
con.close()
print(f"\nOK -> {DB}")
