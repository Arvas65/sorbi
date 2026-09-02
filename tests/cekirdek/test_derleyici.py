"""B-2 / F-1 testleri — derleyici.

Üç katman:

1. **Altın çiftler** (`altin/derleyici.json`) — regresyon nöbetçisi. Anlık
   görüntüdür; ilk kez doğruluğu kanıtlamaz, DEĞİŞTİĞİNİ söyler.
2. **Gerçek veritabanında koşum** — anlık görüntüyü doğrulanmış artefakta
   çevirir. Bunun neden zorunlu olduğu Build sırasında ölçüldü: 2026-08-30'da
   43 altın çiftin 29'u `demo/hospital.db`'de patladı, çünkü örnek anlam
   modelinde uydurma kolon adları vardı (`randevu.iptal`). Ne tip sistemi ne
   `dogrula()` ne de altın çiftlerin kendisi yakaladı — yalnız KOŞTURMAK
   yakaladı. Bu, SPEC R-6'nın (insan yanlış etiketlerse her şey tutarlı
   biçimde yanlış olur) canlı kanıtıdır.
3. **Kural testleri** — elle yazılmış, ilk-kez-doğruluk kontrolleri.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3

import pytest
from ornek import gecerli_model

from app.cekirdek import derleyici as derleyici_modulu
from app.cekirdek.derleyici import derle
from app.cekirdek.secim import Secim
from app.cekirdek.tipler import Filtre, Zaman, ZamanTanesi
from app.validator import validate_and_transpile

KOK = pathlib.Path(__file__).resolve().parents[2]
ALTIN = json.loads((pathlib.Path(__file__).parent / "altin" / "derleyici.json")
                   .read_text(encoding="utf-8"))
DEMO_DB = KOK / "demo" / "hospital.db"


def _secim(veri: dict) -> Secim:
    return Secim.from_dict(veri)


# --------------------------------------------------------------------------- #
#  1) Altın çiftler
# --------------------------------------------------------------------------- #

def test_altin_cift_sayisi():
    """SPEC B-2: en az 40 altın çift."""
    assert len(ALTIN) >= 40, f"yalnız {len(ALTIN)} çift var"


@pytest.mark.parametrize("ad", sorted(ALTIN))
def test_altin_cift(ad: str):
    m = gecerli_model()
    sonuc = derle(_secim(ALTIN[ad]["secim"]), m)
    assert sonuc.ok, f"{ad}: {sonuc.gecersiz}"
    assert sonuc.sql == ALTIN[ad]["beklenen_sql"], f"{ad}: SQL değişti"
    assert list(sonuc.tablolar) == ALTIN[ad]["tablolar"]


# --------------------------------------------------------------------------- #
#  2) Gerçek veritabanında koşum — anlık görüntüyü doğrulanmışa çevirir
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ad", sorted(ALTIN))
def test_altin_cift_gercek_veritabaninda_kosar(ad: str):
    con = sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True)
    try:
        satirlar = con.execute(ALTIN[ad]["beklenen_sql"]).fetchall()
    finally:
        con.close()
    assert len(satirlar) == ALTIN[ad]["satir_sayisi"], f"{ad}: satır sayısı değişti"


def test_kirilim_toplami_sismiyor():
    """Fan-out korumasının SAYISAL kanıtı.

    'Bölüme göre ciro' toplamı, elle hesaplanan (iptal hariç, zincir üzerinden)
    toplamla BİREBİR aynı olmalı ve ham toplamı asla aşmamalı. Ölçüldü:
    14.574.050 — üç yöntem de aynı.
    """
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["ciro"], boyutlar=["bolum"]), m)
    con = sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True)
    try:
        derleyici = round(sum(r[1] for r in con.execute(sonuc.sql)), 2)
        elle = con.execute("""SELECT ROUND(SUM(f.tutar), 2) FROM fatura f
            JOIN muayene mu ON mu.muayene_id = f.muayene_id
            JOIN randevu ra ON ra.randevu_id = mu.randevu_id
            WHERE ra.durum <> 'IPTAL'""").fetchone()[0]
        ham = con.execute("SELECT ROUND(SUM(tutar), 2) FROM fatura").fetchone()[0]
    finally:
        con.close()
    assert abs(derleyici - elle) < 0.01
    assert derleyici <= ham + 0.01, "kırılım toplamı ham toplamı aştı — ÇOĞALMA"


# --------------------------------------------------------------------------- #
#  3) Kural testleri
# --------------------------------------------------------------------------- #

def test_fan_out_reddedilir():
    """Ölçüldü (demo/hospital.db): ciro, muayene_islem üzerinden kırılınca
    14.574.050 -> 34.222.000, yani 2,35x şişiyor. Bu sorgu üretilmemeli."""
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["ciro"], boyutlar=["islem_adi"]), m)
    assert not sonuc.ok
    assert any("ÇOĞALTIR" in g for g in sonuc.gecersiz)
    assert any("islem" in g for g in sonuc.gecersiz)      # hangi tablo, yazılıyor


def test_zincir_reddedilmez():
    """randevu -> muayene -> fatura 1:1 zincir; yasaklamak bilgi kaybı olurdu."""
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["ciro"], boyutlar=["bolum"]), m)
    assert sonuc.ok
    assert set(sonuc.tablolar) >= {"fatura", "muayene", "randevu", "doktor", "bolum"}


def test_olcu_dogru_tarafta_olunca_ayni_kirilim_gecer():
    """Fan-out'un çaresi yasak değil, ölçüyü doğru tarafta tanımlamak."""
    m = gecerli_model()
    assert derle(Secim.kur(m, olculer=["islem_sayisi"], boyutlar=["islem_adi"]), m).ok


def test_gecerlilik_her_zaman_eklenir():
    """Eksen 8 — unutulamaz, çünkü istem disiplinine bırakılmadı."""
    m = gecerli_model()
    for kw in ({"olculer": ["randevu_sayisi"]},
               {"olculer": ["randevu_sayisi"], "boyutlar": ["bolum"]},
               {"olculer": ["ciro"], "boyutlar": ["bolum"]}):
        sonuc = derle(Secim.kur(m, **kw), m)
        assert "randevu.durum <> 'IPTAL'" in sonuc.sql, kw
        assert sonuc.uygulanan_gecerlilikler


def test_gecerliligi_olmayan_tablo_kosul_uretmez():
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["ciro"]), m)
    assert sonuc.ok and "WHERE" not in sonuc.sql


def test_zaman_olay_tarihine_uygulanir_kullanici_secemez():
    """Eksen 7 — model tarih kolonu SEÇEMEZ."""
    m = gecerli_model()
    z = Zaman(ZamanTanesi.AY, "2026-01-01", "2026-08-30", "bu yıl")
    sonuc = derle(Secim.kur(m, olculer=["ciro"], zaman=z), m)
    assert "fatura.tarih >=" in sonuc.sql and "fatura.tarih <=" in sonuc.sql


def test_miras_alinan_tarih_icin_kaynak_tablo_birlestirilir():
    """`muayene_islem` kendi tarihini taşımaz; zamanı randevudan alır.

    Gerçek şemada karşılaşıldı: reddetmek yerine güvenli yolla `randevu`
    birleştirilir — yalnız çoğaltmayan yolla, dolayısıyla sayı bozulamaz.
    """
    m = gecerli_model()
    z = Zaman(ZamanTanesi.AY, "2025-01-01", "2026-12-31", "tüm dönem")
    sonuc = derle(Secim.kur(m, olculer=["islem_sayisi"], zaman=z), m)
    assert sonuc.ok
    assert "randevu.tarih" in sonuc.sql
    assert "randevu" in sonuc.tablolar
    assert any("birleştirildi" in n for n in sonuc.notlar)


def test_toplama_ifadeyi_sarar_kaynak_kosulu_iceride_kalir():
    """CASE WHEN toplamanın İÇİNE girer; dışına konsaydı diğer ölçüleri de
    filtreler ve sessizce bozardı."""
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["odenmemis_ciro", "ciro"]), m)
    assert "SUM(CASE WHEN fatura.odeme_durumu <> 'ODENDI' THEN fatura.tutar END)" \
        in sonuc.sql.replace("\n", " ").replace("  ", " ")
    assert "SUM(fatura.tutar) AS ciro" in sonuc.sql


def test_benzersiz_sayim_distinct_uretir():
    m = gecerli_model()
    assert "COUNT(DISTINCT randevu.randevu_id)" in derle(
        Secim.kur(m, olculer=["randevu_sayisi"]), m).sql


def test_ortalama_uyarisi_nota_gecer():
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["ortalama_fatura"], boyutlar=["bolum"]), m)
    assert any("ortalamanın ortalaması" in n for n in sonuc.notlar)


def test_sozluk_gosterimden_ham_degere_cevirir():
    """Eksen 4 — v3'ün en sık sessiz yanlışı: 'Kadın' yazılır, kolonda 'K' var,
    sorgu çalışır ve sıfır satır döner."""
    m = gecerli_model()
    sonuc = derle(Secim.kur(m, olculer=["randevu_sayisi"],
                            filtreler=[Filtre("cinsiyet", "esittir", ("Kadın",))]), m)
    assert "hasta.cinsiyet = 'K'" in sonuc.sql
    assert "Kadın" not in sonuc.sql


def test_maskeli_kolon_derleme_aninda_reddedilir():
    """SPEC E-5: SQL'e HİÇ dönüşmez — çalışma anında değil."""
    m = gecerli_model()
    from dataclasses import replace
    b = dict(m.boyutlar)
    b["hasta_adi"] = replace(b["sehir"], ad="hasta_adi", kolon="ad")
    m2 = replace(m, boyutlar=b)
    sonuc = derle(Secim.kur(m2, olculer=["randevu_sayisi"], boyutlar=["hasta_adi"]), m2)
    assert not sonuc.ok
    assert any("maskeli" in g for g in sonuc.gecersiz)
    assert not sonuc.sql


def test_iliski_yoksa_farkli_mesaj_verir():
    """'İlişki yok' ile 'çoğaltır' farklı sorunlardır ve farklı şey yaptırır."""
    from dataclasses import replace
    m = gecerli_model()
    t = dict(m.tablolar)
    t["muayene_islem"] = replace(t["muayene_islem"], iliskiler=())
    sonuc = derle(Secim.kur(replace(m, tablolar=t), olculer=["ciro"],
                            boyutlar=["islem_adi"]), replace(m, tablolar=t))
    assert not sonuc.ok
    assert any("tanımlı bir ilişki yok" in g for g in sonuc.gecersiz)


# ------------------------------------------------------------------ yapısal

def test_atif_yapilan_her_tablo_birlestirilmis():
    """Build hatası (2026-08-30): filtre tablosu `gerekli` kümesine girmiyordu;
    `hasta.cinsiyet` filtresi üretiliyor ama `JOIN hasta` yoktu. Duman testi
    yakaladı, birim test değil — o yüzden bu yapısal denetim var."""
    m = gecerli_model()
    for ad in sorted(ALTIN):
        sql = ALTIN[ad]["beklenen_sql"]
        atif = set(re.findall(r"\b([a-z_]+)\.", sql)) & set(m.tablolar)
        katilan = set(re.findall(r"(?:FROM|JOIN)\s+([a-z_]+)", sql))
        assert not (atif - katilan), f"{ad}: birleştirilmemiş tabloya atıf {atif - katilan}"


def test_derlenen_sql_validatorden_gecer():
    """Derinlemesine savunma: derleyicinin çıktısı da kapıdan geçer."""
    m = gecerli_model()
    for ad in sorted(ALTIN):
        v = validate_and_transpile(ALTIN[ad]["beklenen_sql"],
                                   known_tables=set(m.tablolar))
        assert v.ok, f"{ad}: {v.error}"


def test_hedef_lehceye_cevrilir():
    m = gecerli_model()
    z = Zaman(ZamanTanesi.AY, "2026-01-01", "2026-08-30", "bu yıl")
    pg = derle(Secim.kur(m, olculer=["ciro"], boyutlar=["fatura_tarihi"], zaman=z),
               m, lehce="postgres")
    assert pg.ok
    assert "STRFTIME" not in pg.sql.upper()      # sqlite'a özgü kalmadı


def test_derle_asla_firlatmaz():
    m = gecerli_model()
    assert not derle(Secim(olculer=("yok",), gecersiz=("bilerek",)), m).ok
    assert not derle(Secim(), m).ok


# --------------------------------------------------------------------------- #
#  İP-49 — yapısal güvence: seçilen kolon kümesi daima açık
# --------------------------------------------------------------------------- #

def test_hicbir_altin_ciftte_yildiz_yok():
    """`SELECT *` iki değişmezi birden deler.

    Sınır 1: yıldız, anlam modelinde YER ALMAYAN kolonları da getirir —
    maskeli olanlar dâhil. `test_maskeli_kolon_derleme_aninda_reddedilir`
    yalnız ADIYLA istenen maskeli kolonu durdurur; yıldız onun etrafından
    dolaşır.
    Değişmez #4: sonucun şekli seçime bağlı olmaktan çıkar, şemaya bağlı
    hâle gelir; şemaya bir kolon eklendiğinde grafik seçimi sessizce başka
    bir şey üretir.
    """
    for ad, cift in sorted(ALTIN.items()):
        sql = cift["beklenen_sql"].upper()
        assert "SELECT *" not in sql and "SELECT\n  *" not in sql, ad
        assert ".*" not in cift["beklenen_sql"], ad


def test_derleyici_yildiz_uretecek_bir_yol_tasimiyor():
    """Kaynak denetimi: `derleyici.py` içinde hiçbir yerde '*' bir seçim
    öğesi olarak geçmez. Altın çiftler bugün üretilen SQL'i korur; bu test
    yarın eklenecek bir kod yolunu korur."""
    metin = pathlib.Path(derleyici_modulu.__file__).read_text(encoding="utf-8")
    for satir in metin.splitlines():
        govde = satir.split("#", 1)[0]
        assert "SELECT *" not in govde.upper(), satir
        assert '"*"' not in govde and "'*'" not in govde, satir


def test_secilen_kolonlar_secimden_gelir():
    """Sonuçtaki sütun sayısı = boyut + ölçü sayısı. Ne bir eksik ne bir
    fazla: fazlası sızıntı, eksiği sessiz kayıp olurdu."""
    m = gecerli_model()
    s = Secim.kur(m, olculer=["ciro", "randevu_sayisi"],
                  boyutlar=["unvan", "cinsiyet"])
    sonuc = derle(s, m)
    assert sonuc.ok, sonuc.gecersiz
    con = sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True)
    try:
        imlec = con.execute(sonuc.sql)
        assert len(imlec.description) == 4
    finally:
        con.close()
