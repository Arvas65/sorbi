"""B-7 güven kontrolü testleri — LLM'siz, veritabanısız.

Bu testlerin iki işi var:
1. Her kontrol GERÇEKTEN yakalaması gerekeni yakalıyor mu (isabet)
2. Doğru sorgularda SUSUYOR mu (yanlış alarm) — asıl risk burada.
   Sürekli bağıran bir uyarı sistemi, hiç olmayandan daha kötüdür: kullanıcı
   uyarıyı okumayı bırakır ve o noktadan sonra sessiz yanlış geri döner.
"""
from app import guven
from app.guven import degerlendir

# --------------------------------------------------------------- sözleşme

def test_asla_istisna_firlatmaz_bozuk_sql():
    r = degerlendir("kaç doktor var", "SELECT ((( FROM", 0)
    assert isinstance(r, guven.GuvenSonucu)


def test_asla_istisna_firlatmaz_bos_girdi():
    assert degerlendir("", "", 0) is not None


def test_bozuk_sql_ile_bile_bicim_kontrolu_calisir():
    """Ayrıştırılamayan SQL, ayrıştırma gerektirmeyen kontrolleri susturmamalı."""
    r = degerlendir("hastaları listele", "SELECT ((( FROM", 1, kolon_sayisi=1)
    assert guven.BICIM_LISTE in r.kodlar


# --------------------------------------------------------------- boş sonuç

def test_bos_sonuc_metin_filtresiyle_bayraklanir():
    r = degerlendir("iptal edilen randevu sayısı",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'İPTAL'", 0)
    assert guven.BOS_SONUC_FILTRELI in r.kodlar
    assert "'İPTAL'" in r.mesajlar[0]


def test_bos_sonuc_filtresiz_de_bayraklanir_ama_farkli_kodla():
    r = degerlendir("kaç hasta var", "SELECT * FROM hasta", 0)
    assert guven.BOS_SONUC in r.kodlar


def test_dolu_sonuc_bos_bayragi_almaz():
    r = degerlendir("kaç hasta var", "SELECT COUNT(*) FROM hasta", 1)
    assert guven.BOS_SONUC not in r.kodlar
    assert guven.BOS_SONUC_FILTRELI not in r.kodlar


# --------------------------------------------------------------- bilinmeyen değer

DEGERLER = {"unvan": ["Prof. Dr.", "Doç. Dr.", "Uzm. Dr."],
            "durum": ["IPTAL", "TAMAMLANDI", "BEKLIYOR"]}


def test_semada_olmayan_deger_yakalanir():
    r = degerlendir("profesör sayısı",
                    "SELECT COUNT(*) FROM doktor WHERE unvan = 'Profesör'", 5,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER in r.kodlar


def test_noktali_i_tuzagi_yakalanir_ve_dogru_yazim_onerilir():
    """'İPTAL' ile 'IPTAL' farklı dizelerdir; sorgu hata vermez, 0 satır döner."""
    r = degerlendir("iptal sayısı",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'İPTAL'", 3,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER in r.kodlar
    assert "'IPTAL'" in " ".join(r.mesajlar)


def test_dogru_deger_bayrak_almaz():
    r = degerlendir("iptal sayısı",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'IPTAL'", 3,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER not in r.kodlar


def test_in_listesindeki_deger_de_denetlenir():
    r = degerlendir("durumlar",
                    "SELECT * FROM randevu WHERE durum IN ('IPTAL', 'SILINDI')", 2,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER in r.kodlar


def test_like_denetlenmez():
    """LIKE '%kardiyo%' hiçbir tam değere eşit değildir ama doğrudur."""
    r = degerlendir("kardiyoloji doktorları",
                    "SELECT * FROM doktor WHERE unvan LIKE '%Doç%'", 4,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER not in r.kodlar


def test_bilinmeyen_kolon_sessiz_kalir():
    """Örneklenmemiş kolon hakkında bir şey bilmiyoruz — susmak doğru davranış."""
    r = degerlendir("x", "SELECT * FROM t WHERE aciklama = 'herhangi'", 2,
                    bilinen_degerler=DEGERLER)
    assert guven.BILINMEYEN_DEGER not in r.kodlar


# --------------------------------------------------------------- sonuç biçimi

def test_sayi_soruldu_cok_satir_dondu():
    r = degerlendir("kaç doktor var", "SELECT id FROM doktor", 40)
    assert guven.BICIM_SAYI in r.kodlar


def test_kac_sorusu_group_by_ile_bayrak_almaz():
    """'Bölüm bazında kaç doktor var' meşru biçimde çok satır döndürür."""
    r = degerlendir("bölüm bazında kaç doktor var",
                    "SELECT bolum_id, COUNT(*) FROM doktor GROUP BY bolum_id", 8,
                    kolon_sayisi=2)
    assert guven.BICIM_SAYI not in r.kodlar


def test_liste_soruldu_tek_deger_dondu():
    r = degerlendir("doktorları listele", "SELECT COUNT(*) FROM doktor", 1, kolon_sayisi=1)
    assert guven.BICIM_LISTE in r.kodlar


def test_ilk_n_asilirsa_bayrak():
    r = degerlendir("en çok kazandıran ilk 5 işlem",
                    "SELECT ad FROM islem ORDER BY ucret DESC", 30)
    assert guven.BICIM_ADET in r.kodlar


def test_ilk_n_tam_gelirse_bayrak_yok():
    r = degerlendir("en çok kazandıran ilk 5 işlem",
                    "SELECT ad FROM islem ORDER BY ucret DESC LIMIT 5", 5)
    assert guven.BICIM_ADET not in r.kodlar


def test_ilk_n_altinda_kalirsa_bayrak_yok():
    """Veride 5 kayıt yoksa 3 satır dönmesi doğrudur."""
    r = degerlendir("ilk 5 işlem", "SELECT ad FROM islem ORDER BY ucret DESC LIMIT 5", 3)
    assert guven.BICIM_ADET not in r.kodlar


# --------------------------------------------------------------- toplama uyumu

def test_kac_sorusuna_sum_uyumsuz():
    r = degerlendir("kaç randevu var", "SELECT SUM(ucret) FROM randevu", 1)
    assert guven.TOPLAMA_UYUMSUZ in r.kodlar


def test_ortalama_sorusuna_sum_uyumsuz():
    r = degerlendir("ortalama fatura tutarı nedir", "SELECT SUM(tutar) FROM fatura", 1)
    assert guven.TOPLAMA_UYUMSUZ in r.kodlar


def test_kac_sorusuna_count_uyumlu():
    r = degerlendir("kaç randevu var", "SELECT COUNT(*) FROM randevu", 1)
    assert guven.TOPLAMA_UYUMSUZ not in r.kodlar


def test_toplama_yoksa_sessiz():
    r = degerlendir("kaç doktor var", "SELECT ad FROM doktor", 1)
    assert guven.TOPLAMA_UYUMSUZ not in r.kodlar


def test_count_ve_sum_birlikteyse_bayrak_yok():
    r = degerlendir("kaç fatura ve toplam tutar",
                    "SELECT COUNT(*), SUM(tutar) FROM fatura", 1, kolon_sayisi=2)
    assert guven.TOPLAMA_UYUMSUZ not in r.kodlar


# --------------------------------------------------------------- şema örtüşmesi

def test_alakasiz_tablo_bayraklanir():
    r = degerlendir("kaç doktor var", "SELECT COUNT(*) FROM fatura", 1,
                    tablolar=("fatura",))
    assert guven.SEMA_ORTUSMEZ in r.kodlar


def test_turkce_harf_katlamasi_yanlis_alarm_uretmez():
    """Soru 'işlem' yazar, tablo 'islem'dir. Katlama olmadan bu bir yanlış alarmdır."""
    r = degerlendir("en pahalı işlem hangisi", "SELECT ad FROM islem", 1,
                    tablolar=("islem",))
    assert guven.SEMA_ORTUSMEZ not in r.kodlar


def test_sozluk_uzerinden_baglanti_kurulur():
    r = degerlendir("ciro ne kadar", "SELECT SUM(tutar) FROM fatura", 1,
                    tablolar=("fatura",), sozluk={"ciro": "fatura tutarı toplamı"})
    assert guven.SEMA_ORTUSMEZ not in r.kodlar


def test_tablolar_verilmezse_sqlden_cikarilir():
    """Çağıranın liste vermesi gerekmez; sorgunun kendisi zaten söylüyor."""
    r = degerlendir("kaç doktor var", "SELECT COUNT(*) FROM fatura", 1)
    assert guven.SEMA_ORTUSMEZ in r.kodlar


def test_sql_ayristirilamiyorsa_ortusme_kontrolu_susar():
    r = degerlendir("kaç doktor var", "SELECT ((( FROM", 1)
    assert guven.SEMA_ORTUSMEZ not in r.kodlar


def test_kullanilan_tablo_getirilen_tabloya_baskin():
    """RAG altı tablo getirir, model birini kullanır; kontrol kullanılanı sorar."""
    r = degerlendir("en pahalı işlem hangisi",
                    "SELECT ad FROM islem ORDER BY ucret DESC LIMIT 1", 1)
    assert guven.SEMA_ORTUSMEZ not in r.kodlar


# --------------------------------------------------------------- kapatma anahtarı

def test_kod_kapatilabilir():
    acik = degerlendir("kaç doktor var", "SELECT id FROM doktor", 40)
    kapali = degerlendir("kaç doktor var", "SELECT id FROM doktor", 40,
                         kapali={guven.BICIM_SAYI})
    assert guven.BICIM_SAYI in acik.kodlar
    assert guven.BICIM_SAYI not in kapali.kodlar


def test_tum_bayraklar_kapaliysa_guvenli_geri_doner():
    r = degerlendir("kaç doktor var", "SELECT id FROM doktor", 40,
                    kapali=set(guven.TUM_KODLAR))
    assert r.guvenli is True
    assert r.bayraklar == []


# --------------------------------------------------------------- temiz sorgular

TEMIZ = [
    ("Kaç doktor var?", "SELECT COUNT(*) FROM doktor", 1, 1, ("doktor",)),
    ("Bölümleri listele", "SELECT ad FROM bolum", 8, 1, ("bolum",)),
    ("Toplam fatura tutarı nedir?", "SELECT SUM(tutar) FROM fatura", 1, 1, ("fatura",)),
    ("Ortalama yatış süresi kaç gün?",
     "SELECT AVG(julianday(cikis)-julianday(giris)) FROM yatis", 1, 1, ("yatis",)),
    ("Her bölümde kaç doktor var?",
     "SELECT b.ad, COUNT(*) FROM doktor d JOIN bolum b ON d.bolum_id=b.id GROUP BY b.ad",
     8, 2, ("doktor", "bolum")),
    ("En pahalı ilk 5 işlem", "SELECT ad FROM islem ORDER BY ucret DESC LIMIT 5",
     5, 1, ("islem",)),
]


def test_temiz_sorgularda_hic_bayrak_yok():
    """Yanlış alarm bütçesi: bu altı sorgunun hiçbiri uyarı almamalı."""
    kirli = {}
    for soru, sql, satir, kolon, tablolar in TEMIZ:
        r = degerlendir(soru, sql, satir, kolon_sayisi=kolon, tablolar=tablolar,
                        bilinen_degerler=DEGERLER)
        if r.kodlar:
            kirli[soru] = r.kodlar
    assert kirli == {}


# --------------------------------------------------------------- sıfır toplama

def test_sifir_donduren_toplama_bayraklanir():
    """COUNT boş küme üzerinde 0 satır değil, içinde 0 yazan TEK satır döner."""
    r = degerlendir("iptal edilen randevu sayısı",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'İPTAL'", 1,
                    kolon_sayisi=1, satirlar=[(0,)])
    assert guven.SIFIR_TOPLAMA in r.kodlar


def test_sifir_toplama_filtresizse_bayrak_yok():
    """Filtre yoksa sıfır meşru olabilir; söyleyecek bir şeyimiz yok."""
    r = degerlendir("kaç randevu var", "SELECT COUNT(*) FROM randevu", 1,
                    kolon_sayisi=1, satirlar=[(0,)])
    assert guven.SIFIR_TOPLAMA not in r.kodlar


def test_sifirdan_farkli_toplama_bayrak_almaz():
    r = degerlendir("iptal sayısı",
                    "SELECT COUNT(*) FROM randevu WHERE durum = 'IPTAL'", 1,
                    kolon_sayisi=1, satirlar=[(12,)])
    assert guven.SIFIR_TOPLAMA not in r.kodlar


def test_null_ortalama_da_sayilir():
    r = degerlendir("ortalama tutar",
                    "SELECT AVG(tutar) FROM fatura WHERE durum = 'YOK'", 1,
                    kolon_sayisi=1, satirlar=[(None,)])
    assert guven.SIFIR_TOPLAMA in r.kodlar


def test_gruplu_sorgu_sifir_toplama_almaz():
    r = degerlendir("bölüm bazında sayı",
                    "SELECT b, COUNT(*) FROM t WHERE d = 'x' GROUP BY b", 1,
                    kolon_sayisi=2, satirlar=[("a", 0)])
    assert guven.SIFIR_TOPLAMA not in r.kodlar


# --------------------------------------------------------------- filtresiz

def test_soruda_daraltma_var_sorguda_kosul_yok():
    r = degerlendir("İstanbul'da yaşayan kaç hasta var?",
                    "SELECT COUNT(*) FROM hasta", 1, kolon_sayisi=1, satirlar=[(40,)])
    assert guven.FILTRESIZ in r.kodlar


def test_sayili_daraltma_yakalanir():
    r = degerlendir("Ücreti 1000 TL üzerindeki işlemler",
                    "SELECT ad FROM islem", 20)
    assert guven.FILTRESIZ in r.kodlar


def test_limit_olarak_harcanan_sayi_daraltma_sayilmaz():
    """'En çok randevu alan 5 hasta kim?' — 5, LIMIT 5'tir; WHERE beklenmez."""
    r = degerlendir("En çok randevu alan 5 hasta kim?",
                    "SELECT h.ad FROM randevu r JOIN hasta h ON r.hasta_id = h.hasta_id "
                    "GROUP BY h.hasta_id ORDER BY COUNT(*) DESC LIMIT 5", 5)
    assert guven.FILTRESIZ not in r.kodlar


def test_where_varsa_kontrol_susar():
    r = degerlendir("İstanbul'da yaşayan kaç hasta var?",
                    "SELECT COUNT(*) FROM hasta WHERE sehir = 'İstanbul'", 1,
                    kolon_sayisi=1, satirlar=[(12,)])
    assert guven.FILTRESIZ not in r.kodlar


def test_daraltma_isareti_yoksa_bayrak_yok():
    r = degerlendir("Hastanede kaç doktor çalışıyor?",
                    "SELECT COUNT(*) FROM doktor", 1, kolon_sayisi=1, satirlar=[(40,)])
    assert guven.FILTRESIZ not in r.kodlar


def test_tablo_adiyla_ortusen_bilinen_deger_daraltma_sayilmaz():
    """'muayene' hem bir değer hem bir tablodur; konu belirtir, filtre istemez."""
    r = degerlendir("Hangi bölümün doktorları en çok muayene yapmış?",
                    "SELECT b.ad FROM bolum b JOIN muayene m ON 1=1 "
                    "GROUP BY b.ad ORDER BY COUNT(*) DESC LIMIT 1", 1,
                    bilinen_degerler={"ad": ["Muayene", "MR", "EKG"]})
    assert guven.FILTRESIZ not in r.kodlar


# --------------------------------------------------------------- atlanan kolon

KOLONLAR = {"unvan", "sehir", "cinsiyet", "odeme_durumu", "kayit_tarihi", "tutar"}


def test_soruda_gecen_kolona_sorgu_dokunmuyorsa_bayrak():
    """'Profesör' şemada bilinen bir değer değil, ama 'unvan' bir kolon adı."""
    r = degerlendir("Profesör unvanlı doktorlar kimler?",
                    "SELECT ad, soyad FROM doktor", 40, kolonlar=KOLONLAR)
    assert guven.ATLANAN_KOLON in r.kodlar


def test_kolona_dokunuluyorsa_bayrak_yok():
    r = degerlendir("Profesör unvanlı doktorlar kimler?",
                    "SELECT ad FROM doktor WHERE unvan = 'Prof. Dr.'", 5,
                    kolonlar=KOLONLAR)
    assert guven.ATLANAN_KOLON not in r.kodlar


def test_cok_parcali_kolon_adi_parca_parca_eslesir():
    """Soru 'ödeme durumlarına göre' der; kolon `odeme_durumu`dur."""
    r = degerlendir("Ödeme durumlarına göre fatura sayısı nasıl dağılıyor?",
                    "SELECT odeme_durumu, COUNT(*) FROM fatura GROUP BY odeme_durumu",
                    3, kolon_sayisi=2, kolonlar=KOLONLAR)
    assert guven.ATLANAN_KOLON not in r.kodlar


def test_kisa_kokler_eslesmez():
    """'hastanede' → 'has'; bu 'hasta_id' parçasına çarpıp yanlış alarm veriyordu."""
    r = degerlendir("Hastanede kaç doktor çalışıyor?",
                    "SELECT COUNT(*) FROM doktor", 1, kolon_sayisi=1,
                    satirlar=[(40,)], kolonlar=KOLONLAR | {"hasta_id"})
    assert guven.ATLANAN_KOLON not in r.kodlar


def test_kolon_listesi_yoksa_kontrol_susar():
    r = degerlendir("Profesör unvanlı doktorlar kimler?",
                    "SELECT ad FROM doktor", 40)
    assert guven.ATLANAN_KOLON not in r.kodlar
