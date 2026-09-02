"""SorBI demo: sentetik hastane verisi üreteci.

Deterministik: aynı girdi, her zaman aynı veri. Gerçek kişi verisi İÇERMEZ.
Kullanım: python demo/seed_data.py  ->  demo/hospital.db

## Determinizm neden İKİ parçalı (BULGU-25)

`random.seed(42)` rastgele diziyi sabitler ama tarihleri sabitlemez. Bu dosya
bir zamanlar `TODAY = date.today()` diyordu; yani üretilen veri **koşulduğu
güne** göre kayıyordu. Docstring "her çalıştırmada aynı veri" diye söz
veriyor, o sözü tutan hiçbir şey yoktu.

Sonucu cetvelde görüldü: 43 altın çiftin 9'u zaman filtreli ve dokuzu da
sabit bir satır sayısı iddia ediyor. Takvim ilerledikçe kovalar kayıyor ve
`kod değişmeden` testler kırmızıya dönüyor — 2026-09-02'de `zaman-hafta`
(80 -> 79) düştü, 1 Ekim'de ay/çeyrek sınırında beşi birden düşecekti.

Bu yüzden referans gün **donduruldu.** Değer keyfî değil: cetvelin
kalibre edildiği gün. `REFERANS_GUN` ile üretilen veri, altın çiftlerin ve
101 gold beklentisinin ölçüldüğü veriyle **satır satır aynıdır**
(2026-09-02'de doğrulandı, Python 3.11 ve 3.13 üzerinde).

## Bu günü değiştirirsen

Cetvelin tamamı yeniden kalibre edilmek zorundadır: 43 altın çiftin
`satir_sayisi` değerleri ve güven karnesinin mutant havuzu veriye bağlıdır.
Tek seferlik, bilinçli ve belgelenmiş bir yeniden temellendirme meşrudur;
her tohumlamada kendini güncelleyen bir beklenti değildir — o test hiçbir
şey iddia etmez.

Geçici deneme için `SORBI_BUGUN` ortam değişkeni günü geçersiz kılar;
projenin geri kalanında da aynı kaçış kapısı kullanılıyor (`app/config.py`).
Nöbetçisi: `tests/test_seed_determinizmi.py`.
"""
import os
import random
import sqlite3
from datetime import date, timedelta

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "hospital.db")
DDL = os.path.join(HERE, "hospital_schema.sql")

BOLUMLER = ["Kardiyoloji", "Dahiliye", "Ortopedi", "Nöroloji", "Göz Hastalıkları",
            "Kulak Burun Boğaz", "Genel Cerrahi", "Çocuk Sağlığı", "Kadın Doğum", "Üroloji"]
ADLAR_E = ["Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Osman", "Yusuf", "Murat",
           "Emre", "Burak", "Serkan", "Tolga", "Kerem", "Deniz", "Cem", "Onur", "Barış", "Volkan"]
ADLAR_K = ["Ayşe", "Fatma", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Selin", "Merve", "Esra",
           "Büşra", "Gamze", "Derya", "Seda", "Aslı", "Pınar", "Gül", "Ceren", "İrem", "Nazlı"]
SOYADLAR = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Öztürk", "Aydın", "Arslan", "Doğan", "Kılıç",
            "Aslan", "Çetin", "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Erdoğan", "Yıldız", "Güneş"]
SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Kocaeli", "Konya", "Adana"]
UNVANLAR = ["Prof. Dr.", "Doç. Dr.", "Uzm. Dr.", "Uzm. Dr.", "Dr.", "Dr."]
TANILAR = ["Hipertansiyon", "Tip 2 Diyabet", "Migren", "Bel fıtığı", "Katarakt", "Sinüzit",
           "Gastrit", "Astım", "Anemi", "Menisküs yırtığı", "Aritmi", "Üst solunum yolu enfeksiyonu"]
ISLEMLER = [("Muayene", 800), ("EKG", 450), ("Kan Tahlili", 350), ("MR", 3200), ("Röntgen", 600),
            ("Ultrason", 900), ("EKO", 1500), ("Efor Testi", 1200), ("Endoskopi", 4500), ("Fizik Tedavi Seansı", 700)]
DURUMLAR = ["TAMAMLANDI"] * 70 + ["IPTAL"] * 12 + ["GELMEDI"] * 10 + ["BEKLIYOR"] * 8  # ağırlıklı dağılım

# Cetvelin kalibre edildiği gün. Dondurulmuş — sebebi ve değiştirme
# maliyeti dosya başlığında. `date.today()` BU DOSYADA KULLANILMAZ.
REFERANS_GUN = os.getenv("SORBI_BUGUN", "").strip() or "2026-07-25"
TODAY = date.fromisoformat(REFERANS_GUN)
START = TODAY - timedelta(days=540)  # ~18 ay geçmiş


def rand_date(a: date, b: date) -> date:
    return a + timedelta(days=random.randint(0, (b - a).days))


def main() -> None:
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(DDL, encoding="utf-8").read())
    cur = con.cursor()

    # Bölümler
    for i, ad in enumerate(BOLUMLER, 1):
        cur.execute("INSERT INTO bolum VALUES (?,?,?)", (i, ad, (i % 4) + 1))

    # Doktorlar (bölüm başına 2-4)
    doktor_id = 0
    for bolum_id in range(1, len(BOLUMLER) + 1):
        for _ in range(random.randint(2, 4)):
            doktor_id += 1
            cinsiyet = random.choice("KE")
            ad = random.choice(ADLAR_K if cinsiyet == "K" else ADLAR_E)
            cur.execute("INSERT INTO doktor VALUES (?,?,?,?,?,?)",
                        (doktor_id, ad, random.choice(SOYADLAR), random.choice(UNVANLAR),
                         bolum_id, rand_date(date(2008, 1, 1), date(2024, 6, 1)).isoformat()))
    n_doktor = doktor_id

    # Hastalar
    N_HASTA = 600
    for h in range(1, N_HASTA + 1):
        cinsiyet = random.choice("KE")
        ad = random.choice(ADLAR_K if cinsiyet == "K" else ADLAR_E)
        tckn = "".join(str(random.randint(0, 9)) for _ in range(11))  # sentetik, algoritmik geçerlilik aranmaz
        cur.execute("INSERT INTO hasta VALUES (?,?,?,?,?,?,?,?)",
                    (h, ad, random.choice(SOYADLAR), tckn,
                     rand_date(date(1940, 1, 1), date(2018, 12, 31)).isoformat(),
                     cinsiyet, random.choice(SEHIRLER),
                     rand_date(START, TODAY).isoformat()))

    # İşlem kataloğu
    for i, (ad, ucret) in enumerate(ISLEMLER, 1):
        cur.execute("INSERT INTO islem VALUES (?,?,?)", (i, ad, float(ucret)))

    # Randevular + muayene + işlemler + fatura
    N_RANDEVU = 6000
    muayene_id = fatura_id = 0
    for r in range(1, N_RANDEVU + 1):
        d_id = random.randint(1, n_doktor)
        tarih = rand_date(START, TODAY)
        durum = random.choice(DURUMLAR)
        if tarih > TODAY - timedelta(days=7) and random.random() < 0.5:
            durum = "BEKLIYOR"
        cur.execute("INSERT INTO randevu VALUES (?,?,?,?,?,?)",
                    (r, random.randint(1, N_HASTA), d_id, tarih.isoformat(),
                     f"{random.randint(9, 17):02d}:{random.choice(['00','15','30','45'])}", durum))
        if durum == "TAMAMLANDI":
            muayene_id += 1
            cur.execute("INSERT INTO muayene VALUES (?,?,?,?)",
                        (muayene_id, r, random.choice(TANILAR), None))
            toplam = 0.0
            islemler = random.sample(range(1, len(ISLEMLER) + 1), k=random.randint(1, 3))
            for i_id in islemler:
                adet = 1 if i_id != 10 else random.randint(1, 10)  # fizik tedavi seans olabilir
                cur.execute("INSERT INTO muayene_islem VALUES (?,?,?)", (muayene_id, i_id, adet))
                toplam += ISLEMLER[i_id - 1][1] * adet
            fatura_id += 1
            odeme = random.choices(["ODENDI", "BEKLIYOR", "GECIKTI"], weights=[75, 15, 10])[0]
            cur.execute("INSERT INTO fatura VALUES (?,?,?,?,?)",
                        (fatura_id, muayene_id, toplam, odeme,
                         (tarih + timedelta(days=random.randint(0, 3))).isoformat()))

    # Yatışlar
    for y in range(1, 351):
        giris = rand_date(START, TODAY)
        sure = random.randint(1, 14)
        cikis = giris + timedelta(days=sure)
        cur.execute("INSERT INTO yatis VALUES (?,?,?,?,?,?)",
                    (y, random.randint(1, N_HASTA), random.randint(1, len(BOLUMLER)),
                     f"{random.randint(1, 4)}{random.randint(0, 3)}{random.randint(1, 9)}",
                     giris.isoformat(),
                     None if cikis > TODAY else cikis.isoformat()))

    con.commit()
    # Özet
    for t in ["bolum", "doktor", "hasta", "randevu", "muayene", "fatura", "yatis"]:
        print(f"{t:14s} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>6d} satır")
    con.close()
    print(f"\nOK -> {DB}")


if __name__ == "__main__":
    main()
