-- SorBI demo: Özel hastane şeması (SQLite)
-- Tamamen sentetik veri için tasarlandı. Kişisel veri işaretli kolonlar: demo/glossary.json → masked_columns

CREATE TABLE bolum (
    bolum_id     INTEGER PRIMARY KEY,
    ad           TEXT NOT NULL,            -- Kardiyoloji, Dahiliye, ...
    kat          INTEGER
);

CREATE TABLE doktor (
    doktor_id    INTEGER PRIMARY KEY,
    ad           TEXT NOT NULL,
    soyad        TEXT NOT NULL,
    unvan        TEXT NOT NULL,            -- Prof. Dr. | Doç. Dr. | Uzm. Dr. | Dr.
    bolum_id     INTEGER NOT NULL REFERENCES bolum(bolum_id),
    ise_baslama  DATE NOT NULL
);

CREATE TABLE hasta (
    hasta_id     INTEGER PRIMARY KEY,
    ad           TEXT NOT NULL,            -- kişisel veri (maskeli)
    soyad        TEXT NOT NULL,            -- kişisel veri (maskeli)
    tckn         TEXT NOT NULL,            -- kişisel veri (maskeli)
    dogum_tarihi DATE NOT NULL,            -- kişisel veri (maskeli)
    cinsiyet     TEXT NOT NULL,            -- K | E
    sehir        TEXT NOT NULL,
    kayit_tarihi DATE NOT NULL
);

CREATE TABLE randevu (
    randevu_id   INTEGER PRIMARY KEY,
    hasta_id     INTEGER NOT NULL REFERENCES hasta(hasta_id),
    doktor_id    INTEGER NOT NULL REFERENCES doktor(doktor_id),
    tarih        DATE NOT NULL,
    saat         TEXT NOT NULL,            -- HH:MM
    durum        TEXT NOT NULL             -- TAMAMLANDI | IPTAL | GELMEDI | BEKLIYOR
);

CREATE TABLE muayene (
    muayene_id   INTEGER PRIMARY KEY,
    randevu_id   INTEGER NOT NULL UNIQUE REFERENCES randevu(randevu_id),
    tani         TEXT NOT NULL,            -- ICD benzeri kısa tanı adı
    notlar       TEXT
);

CREATE TABLE islem (
    islem_id     INTEGER PRIMARY KEY,
    ad           TEXT NOT NULL,            -- EKG, MR, Tahlil, ...
    ucret        REAL NOT NULL             -- TL
);

CREATE TABLE muayene_islem (               -- N:M kesişim
    muayene_id   INTEGER NOT NULL REFERENCES muayene(muayene_id),
    islem_id     INTEGER NOT NULL REFERENCES islem(islem_id),
    adet         INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (muayene_id, islem_id)
);

CREATE TABLE fatura (
    fatura_id    INTEGER PRIMARY KEY,
    muayene_id   INTEGER NOT NULL UNIQUE REFERENCES muayene(muayene_id),
    tutar        REAL NOT NULL,            -- TL
    odeme_durumu TEXT NOT NULL,            -- ODENDI | BEKLIYOR | GECIKTI
    tarih        DATE NOT NULL
);

CREATE TABLE yatis (
    yatis_id     INTEGER PRIMARY KEY,
    hasta_id     INTEGER NOT NULL REFERENCES hasta(hasta_id),
    bolum_id     INTEGER NOT NULL REFERENCES bolum(bolum_id),
    oda_no       TEXT NOT NULL,
    giris_tarihi DATE NOT NULL,
    cikis_tarihi DATE                      -- NULL = hâlâ yatıyor
);

CREATE INDEX ix_randevu_tarih  ON randevu(tarih);
CREATE INDEX ix_randevu_doktor ON randevu(doktor_id, tarih);
CREATE INDEX ix_fatura_tarih   ON fatura(tarih);
CREATE INDEX ix_yatis_giris    ON yatis(giris_tarihi);
