"""İP-03c triyajından çıkan B-7 düzeltmeleri (2026-08-23).

Her testin karşılığı bir triyaj maddesi ve ölçülmüş bir sayı var:

| Madde  | Ne değişti                                        | Ölçülen etki |
|--------|---------------------------------------------------|--------------|
| B7R-06 | `bilinen_degerler` artık `tablo.kolon` da tutuyor  | yanlış alarm sabit |
| B7R-03 | `filtresiz` zaman ve durum daraltmasını görüyor    | where_dus %59 → %83 |
| B7R-01 | `sema_ortusmez` kolon adlarına da bakıyor          | açıkken yanlış alarm 7 → 3 |
| B7R-08 | havuza gerçekçi hata aileleri eklendi             | havuz 239 → 306 mutant |
|        | `deger_uyumsuz` + `distinct_eksik` kontrolleri     | deger_takasi %21 → %74 |

Karne yolculuğu — sayının ne kadarının gerçek olduğu:

    başlangıç   199/239  %83,3   (kolay havuz, 1 gereksiz bayrak)
    B7R-03/06   212/239  %88,7   (aynı havuz, 1 gereksiz bayrak)
    havuz büyüdü 222/306  %72,5   (dürüst havuz — sayı DÜŞTÜ, doğruluk arttı)
    yeni kontrol 245/306  %80,1   (1 gereksiz bayrak)

Ortadaki düşüş bir gerileme değil, bir düzeltmedir: %83'ün bir kısmı havuzun
kolaylığından geliyordu. BULGU-04'ün söylediği tam olarak buydu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import guven  # noqa: E402


def degerlendir(soru, sql, satir=1, kolon=1, **kw):
    return guven.degerlendir(soru=soru, sql=sql, satir_sayisi=satir,
                             kolon_sayisi=kolon, **kw)


# ===========================================================  B7R-06
# Aynı adlı kolonların değerleri tek bir kümede birleşiyordu. Demo şemasında
# `bolum.ad` bölüm adları, `islem.ad` işlem adları taşır — birleşince
# `bolum.ad = 'EKG'` gibi imkânsız bir filtre "bilinen değer" sayılıyordu.

IKI_TABLOLU = {
    "bolum.ad": ["Kardiyoloji", "Nöroloji", "Ortopedi"],
    "islem.ad": ["EKG", "MR", "Muayene"],
    "ad": ["Kardiyoloji", "Nöroloji", "Ortopedi", "EKG", "MR", "Muayene"],
}


def test_yanlis_tablonun_degeri_artik_yakalaniyor():
    """`bolum.ad = 'EKG'` — EKG bir işlem adı, bölüm adı değil.

    Eski birleşik kümede 'EKG' bilinen bir değerdi ve bu filtre sessizce
    geçiyordu: sorgu çalışır, sıfır satır döner, kullanıcı 'demek ki yok' der.
    """
    r = degerlendir("kardiyoloji bölümünde kaç doktor var",
                    "SELECT COUNT(*) FROM bolum WHERE ad = 'EKG'", 0,
                    bilinen_degerler=IKI_TABLOLU)
    assert guven.BILINMEYEN_DEGER in r.kodlar
    assert "Bu kolondaki değerler" in " ".join(r.mesajlar)


def test_dogru_tablonun_degeri_bayrak_almiyor():
    r = degerlendir("kardiyoloji bölümü",
                    "SELECT * FROM bolum WHERE ad = 'Kardiyoloji'", 3,
                    bilinen_degerler=IKI_TABLOLU)
    assert guven.BILINMEYEN_DEGER not in r.kodlar


def test_takma_ad_uzerinden_tablo_cozuluyor():
    """Üretilen SQL kolonu neredeyse her zaman takma adla niteler."""
    r = degerlendir("bölüm",
                    "SELECT COUNT(*) FROM bolum AS b WHERE b.ad = 'MR'", 0,
                    bilinen_degerler=IKI_TABLOLU)
    assert guven.BILINMEYEN_DEGER in r.kodlar


def test_cozulemeyen_kolon_birlesik_kumeye_duser():
    """İki tablolu JOIN'de niteliksiz kolon çözülemez — susmak yerine
    birleşik kümeyi kullanmak doğru: değer hiçbirinde yoksa gerçekten yoktur."""
    r = degerlendir("x",
                    "SELECT * FROM bolum JOIN islem ON 1=1 WHERE ad = 'Yokbu'", 0,
                    bilinen_degerler=IKI_TABLOLU)
    assert guven.BILINMEYEN_DEGER in r.kodlar
    assert "Aynı adlı kolonlardaki" in " ".join(r.mesajlar)


def test_orneklenmemis_kolon_baska_tablonun_degerleriyle_kiyaslanmaz():
    """Tablo çözüldü ama o kolon örneklenmemiş: yer gerçeğimiz yok.

    Birleşik kümeye düşmek burada yanlış alarmın ta kendisi olurdu —
    `bolum.kat` değerlerini `islem.ad` değerleriyle karşılaştırmak gibi.
    """
    r = degerlendir("x", "SELECT * FROM bolum WHERE kat = 'Zemin'", 0,
                    bilinen_degerler=IKI_TABLOLU)
    assert guven.BILINMEYEN_DEGER not in r.kodlar


def test_eski_bicimli_sozluk_calismaya_devam_ediyor():
    """Nitelikli anahtar taşımayan bir sözlük (elle kurulmuş, eski kayıt)
    susturmamalı — sözlüğün biçimi, kolonun örneklenmemiş olması demek değil."""
    r = degerlendir("profesör sayısı",
                    "SELECT COUNT(*) FROM doktor WHERE unvan = 'Profesör'", 0,
                    bilinen_degerler={"unvan": ["Prof. Dr.", "Doç. Dr."]})
    assert guven.BILINMEYEN_DEGER in r.kodlar


# ===========================================================  B7R-03
# `filtresiz` yalnız sayı / özel ad / tam değer eşleşmesine bakıyordu.
# Kaçırılan `where_dus` mutantlarının ölçülen dökümünde en büyük iki aile
# zaman daraltması ve durum sözcüğüydü.

DURUMLAR = {"randevu.durum": ["BEKLIYOR", "GELMEDI", "IPTAL", "TAMAMLANDI"],
            "fatura.odeme_durumu": ["BEKLIYOR", "GECIKTI", "ODENDI"],
            "durum": ["BEKLIYOR", "GELMEDI", "IPTAL", "TAMAMLANDI"],
            "odeme_durumu": ["BEKLIYOR", "GECIKTI", "ODENDI"]}


def test_zaman_daraltmasi_filtresiz_sorguyu_yakaliyor():
    """"Geçen ay kaç randevu oluşturuldu?" — WHERE'siz COUNT tüm randevuları
    sayar. Ne sayı, ne özel ad, ne bilinen değer var; eskiden hiç işaret yoktu."""
    r = degerlendir("Geçen ay kaç randevu oluşturuldu?",
                    "SELECT COUNT(*) FROM randevu", 1)
    assert guven.FILTRESIZ in r.kodlar


def test_bugun_ve_bu_yil_da_daraltmadir():
    for soru in ("Bugün bekleyen kaç randevu var?",
                 "Bu yıl kesilen faturaların toplam tutarı nedir?",
                 "Son 7 günde kaç muayene yapıldı?"):
        r = degerlendir(soru, "SELECT COUNT(*) FROM randevu", 1)
        assert guven.FILTRESIZ in r.kodlar, soru


def test_zaman_ifadesi_olmayan_soru_bayrak_almiyor():
    r = degerlendir("Toplam kaç hasta kayıtlı?",
                    "SELECT COUNT(*) FROM hasta", 1)
    assert guven.FILTRESIZ not in r.kodlar


def test_durum_sozcugu_farkli_cekimle_de_eslesiyor():
    """Kolonda 'GECIKTI', soruda 'geciken'. İkisi de birbirinin ön eki değil;
    ortak olan ilk beş harf ('gecik')."""
    r = degerlendir("Geciken fatura sayısı kaç?",
                    "SELECT COUNT(*) FROM fatura", 1, bilinen_degerler=DURUMLAR)
    assert guven.FILTRESIZ in r.kodlar


def test_gelmeyen_gelmedi_eslesiyor():
    r = degerlendir("Randevusuna gelmeyen kaç kayıt var?",
                    "SELECT COUNT(*) FROM randevu", 1, bilinen_degerler=DURUMLAR)
    assert guven.FILTRESIZ in r.kodlar


def test_kisa_on_ek_yanlis_alarm_uretmiyor():
    """'katlarda' kökü 'kat'; 'Katarakt' değeriyle üç harfte eşleşiyordu ve
    doğru bir cevaba uyarı konuyordu. Beş harf eşiği bunu düşürür."""
    r = degerlendir("Hangi katlarda bölüm var?",
                    "SELECT DISTINCT kat FROM bolum", 4,
                    bilinen_degerler={"tani": ["Katarakt", "Anemi"],
                                      "muayene.tani": ["Katarakt", "Anemi"]})
    assert guven.FILTRESIZ not in r.kodlar


def test_daraltma_case_icinde_ifade_edilmisse_bayrak_yok():
    """Doğru sorgu WHERE taşımaz, `SUM(CASE WHEN durum='GELMEDI' ...)` taşır.
    Daraltma eksik değil, başka yerde ifade edilmiş."""
    sql = ("SELECT doktor_id, "
           "SUM(CASE WHEN durum = 'GELMEDI' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS oran "
           "FROM randevu GROUP BY doktor_id ORDER BY oran DESC LIMIT 5")
    r = degerlendir("Randevusuna gelmeme oranı en yüksek 5 doktor kim?",
                    sql, 5, 2, bilinen_degerler=DURUMLAR)
    assert guven.FILTRESIZ not in r.kodlar


def test_zaman_ifadesi_where_varsa_hic_bakilmaz():
    """`filtresiz` yalnız hiç koşul yokken konuşur; bu kontrolün sınırıdır."""
    r = degerlendir("Geçen ay kaç randevu oluşturuldu?",
                    "SELECT COUNT(*) FROM randevu WHERE tarih >= '2026-07-01'", 1)
    assert guven.FILTRESIZ not in r.kodlar


# ===========================================================  B7R-08 / BULGU-04
# Mutasyon havuzuna gerçek model hatasına benzeyen aileler eklendi
# (`deger_takasi`, `karsilastirma`, `distinct_dus`, `join_ici_disi`).
# Karne %83,3 → %72,5'e düştü: abartılı bir sayının yerine dürüst bir sayı.
# Aşağıdaki iki kontrol o aileyi hedefliyor ve karneyi %79,7'ye çıkardı —
# bu kez yakalayarak, havuzu kolaylaştırarak değil.

DURUM_SET = {"randevu.durum": ["BEKLIYOR", "GELMEDI", "IPTAL", "TAMAMLANDI"],
             "durum": ["BEKLIYOR", "GELMEDI", "IPTAL", "TAMAMLANDI"]}


def test_soru_baska_degeri_istiyorsa_bayrak():
    """Sorgu çalışır, satır döner, tablo makul — ama sayı başka şeyin sayısı."""
    r = degerlendir("İptal edilen randevu sayısı kaç?",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'BEKLIYOR'", 12,
                    bilinen_degerler=DURUM_SET)
    assert guven.DEGER_UYUMSUZ in r.kodlar
    assert "IPTAL" in " ".join(r.mesajlar)


def test_dogru_deger_kullanildiysa_bayrak_yok():
    r = degerlendir("İptal edilen randevu sayısı kaç?",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'IPTAL'", 12,
                    bilinen_degerler=DURUM_SET)
    assert guven.DEGER_UYUMSUZ not in r.kodlar


def test_soru_hicbir_degeri_anmiyorsa_susar():
    """Soru bir durumdan söz etmiyorsa kontrolün söyleyecek sözü yok."""
    r = degerlendir("Randevu sayısı kaç?",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'IPTAL'", 12,
                    bilinen_degerler=DURUM_SET)
    assert guven.DEGER_UYUMSUZ not in r.kodlar


def test_bilinmeyen_deger_oteki_kontrolun_isi():
    """Değer şemada hiç yoksa bu kontrol karışmaz — `bilinmeyen_deger` konuşur."""
    r = degerlendir("İptal edilen randevu sayısı kaç?",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'İPTAL'", 0,
                    bilinen_degerler=DURUM_SET)
    assert guven.BILINMEYEN_DEGER in r.kodlar
    assert guven.DEGER_UYUMSUZ not in r.kodlar


def test_kac_farkli_sorusunda_distinct_yoksa_bayrak():
    r = degerlendir("MR çektiren kaç farklı hasta var?",
                    "SELECT COUNT(*) FROM muayene_islem WHERE islem_id = 3", 240)
    assert guven.DISTINCT_EKSIK in r.kodlar


def test_distinct_varsa_bayrak_yok():
    r = degerlendir("MR çektiren kaç farklı hasta var?",
                    "SELECT COUNT(DISTINCT hasta_id) FROM muayene_islem", 88)
    assert guven.DISTINCT_EKSIK not in r.kodlar


def test_farkli_demeyen_soru_bayrak_almaz():
    r = degerlendir("Kaç muayene yapıldı?",
                    "SELECT COUNT(*) FROM muayene", 240)
    assert guven.DISTINCT_EKSIK not in r.kodlar


def test_gruplanmis_sorgu_distinct_istemez():
    r = degerlendir("Bölümlere göre kaç farklı hasta var?",
                    "SELECT bolum_id, COUNT(*) FROM muayene GROUP BY bolum_id", 8, 2)
    assert guven.DISTINCT_EKSIK not in r.kodlar


def test_karsilastirma_yonu_ters_ise_bayrak():
    r = degerlendir("Ücreti 1000 TL'nin üzerinde olan işlemleri göster",
                    "SELECT * FROM islem WHERE ucret < 1000", 6)
    assert guven.DEGER_UYUMSUZ in r.kodlar


def test_karsilastirma_yonu_dogruysa_bayrak_yok():
    r = degerlendir("Ücreti 1000 TL'nin üzerinde olan işlemleri göster",
                    "SELECT * FROM islem WHERE ucret > 1000", 6)
    assert guven.DEGER_UYUMSUZ not in r.kodlar


def test_yon_isareti_belirsizse_susar():
    """'en az' hem eşik hem üstünlük demek olabiliyor — belirsiz işaretle
    bayrak koymak yanlış alarmdır."""
    r = degerlendir("En az randevu alan doktor kim?",
                    "SELECT doktor_id FROM randevu GROUP BY doktor_id "
                    "ORDER BY COUNT(*) ASC LIMIT 1", 1)
    assert guven.DEGER_UYUMSUZ not in r.kodlar
