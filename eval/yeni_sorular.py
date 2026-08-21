"""İP-04: hastane test setine eklenecek 50 yeni soru.

Neden (2026-08-16 ablasyonu): qwen2.5-coder:7b %68 verdi, %95 güven aralığı
yaklaşık %55–%81. Hedef %80 bu aralığın İÇİNDE — yani 50 soruluk setle
"hedefin altında mıyız üstünde miyiz" sorusunu cevaplayamıyoruz.
n=100'de standart hata %4,7'ye iner ve 12 puanlık fark 2,6σ olur: ayırt edilebilir.

Tasarım ilkeleri:
- Mevcut 50 sorunun zayıf kaldığı yerler ağırlıklandırıldı: 2-4 JOIN, HAVING,
  alt sorgu, NULL mantığı, tarih aralığı, çoklu toplama.
- Türkçe morfoloji çeşitlendi: aynı kavram farklı eklerle soruldu
  (muayene / muayenede / muayenelerin), çünkü G-09 hattı tam da bunu hedefliyor.
- Değer eşleştirme tuzakları bilinçli kondu: 'Prof. Dr.', 'IPTAL' (noktasız I),
  'GECIKTI' — 3B modelin bu sabah takıldığı sınıf.
- Her gold SQL bu dosyada değil, `--gold-only` koşucusuyla veritabanına karşı
  doğrulanır. Doğrulanmamış soru sete girmez.
"""

YENI = [
    # ---------------------------------------------------------- 0 JOIN (kolay)
    ("En eski kayıtlı hasta hangi tarihte kaydolmuş?", "kolay", 0,
     "SELECT MIN(kayit_tarihi) FROM hasta"),
    ("Kaç farklı şehirden hastamız var?", "kolay", 0,
     "SELECT COUNT(DISTINCT sehir) FROM hasta"),
    ("Doçent unvanlı kaç doktor var?", "kolay", 0,
     "SELECT COUNT(*) FROM doktor WHERE unvan = 'Doç. Dr.'"),
    ("Ödenmiş faturaların toplamı ne kadar?", "kolay", 0,
     "SELECT SUM(tutar) FROM fatura WHERE odeme_durumu = 'ODENDI'"),
    ("Hangi katlarda bölüm var?", "kolay", 0,
     "SELECT DISTINCT kat FROM bolum ORDER BY kat"),
    ("En ucuz işlem hangisi?", "kolay", 0,
     "SELECT ad FROM islem ORDER BY ucret ASC LIMIT 1"),
    ("Erkek hasta sayısı kaçtır?", "kolay", 0,
     "SELECT COUNT(*) FROM hasta WHERE cinsiyet = 'E'"),
    ("Tamamlanan randevu sayısı nedir?", "kolay", 0,
     "SELECT COUNT(*) FROM randevu WHERE durum = 'TAMAMLANDI'"),
    ("Hâlâ hastanede yatan hastaların oda numaraları neler?", "kolay", 0,
     "SELECT oda_no FROM yatis WHERE cikis_tarihi IS NULL"),
    ("İşlemlerin ortalama ücreti kaç TL?", "kolay", 0,
     "SELECT AVG(ucret) FROM islem"),
    ("Bursa'da yaşayan hastaları listele", "kolay", 0,
     "SELECT hasta_id FROM hasta WHERE sehir = 'Bursa'"),
    ("Kaç fatura kesilmiş toplamda?", "kolay", 0,
     "SELECT COUNT(*) FROM fatura"),
    ("En yüksek ücretli 3 işlemin adı ve ücreti nedir?", "kolay", 0,
     "SELECT ad, ucret FROM islem ORDER BY ucret DESC LIMIT 3"),
    ("Ödeme durumlarına göre fatura sayısı nasıl dağılıyor?", "kolay", 0,
     "SELECT odeme_durumu, COUNT(*) FROM fatura GROUP BY odeme_durumu"),
    ("2015'ten önce işe başlayan doktor sayısı kaç?", "kolay", 0,
     "SELECT COUNT(*) FROM doktor WHERE ise_baslama < '2015-01-01'"),

    # ---------------------------------------------------------- 1 JOIN (orta)
    ("Nöroloji bölümünde çalışan doktor sayısı kaç?", "orta", 1,
     "SELECT COUNT(*) FROM doktor d JOIN bolum b ON b.bolum_id = d.bolum_id "
     "WHERE b.ad = 'Nöroloji'"),
    ("Her doktorun kaç randevusu var?", "orta", 1,
     "SELECT d.doktor_id, COUNT(r.randevu_id) FROM doktor d "
     "LEFT JOIN randevu r ON r.doktor_id = d.doktor_id GROUP BY d.doktor_id"),
    ("İptal edilmiş randevusu olan hasta sayısı kaç?", "orta", 1,
     "SELECT COUNT(DISTINCT hasta_id) FROM randevu WHERE durum = 'IPTAL'"),
    ("Hangi bölümde en çok doktor çalışıyor?", "orta", 1,
     "SELECT b.ad FROM bolum b JOIN doktor d ON d.bolum_id = b.bolum_id "
     "GROUP BY b.bolum_id ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Yatışı olan hastaların şehirleri nedir?", "orta", 1,
     "SELECT DISTINCT h.sehir FROM hasta h JOIN yatis y ON y.hasta_id = h.hasta_id"),
    ("Muayenelerde en az 20 kez konulan tanılar hangileri?", "orta", 1,
     "SELECT tani FROM muayene GROUP BY tani HAVING COUNT(*) >= 20"),
    ("Ortopedi bölümüne yatan hasta sayısı kaç?", "orta", 1,
     "SELECT COUNT(*) FROM yatis y JOIN bolum b ON b.bolum_id = y.bolum_id "
     "WHERE b.ad = 'Ortopedi'"),
    ("Geciken faturaların toplam tutarı ne kadar?", "orta", 1,
     "SELECT SUM(tutar) FROM fatura WHERE odeme_durumu = 'GECIKTI'"),
    ("Her ödeme durumu için ortalama fatura tutarı nedir?", "orta", 1,
     "SELECT odeme_durumu, AVG(tutar) FROM fatura GROUP BY odeme_durumu"),
    ("Kaç muayenenin faturası kesilmiş?", "orta", 1,
     "SELECT COUNT(*) FROM muayene m JOIN fatura f ON f.muayene_id = m.muayene_id"),
    ("EKG işlemi kaç kez uygulanmış?", "orta", 1,
     "SELECT SUM(mi.adet) FROM muayene_islem mi JOIN islem i ON i.islem_id = mi.islem_id "
     "WHERE i.ad = 'EKG'"),
    ("Profesörlerin toplam randevu sayısı kaçtır?", "orta", 1,
     "SELECT COUNT(*) FROM randevu r JOIN doktor d ON d.doktor_id = r.doktor_id "
     "WHERE d.unvan = 'Prof. Dr.'"),

    # ---------------------------------------------------------- 2 JOIN (zor)
    ("Kardiyoloji bölümündeki doktorların randevu sayısı toplam kaç?", "zor", 2,
     "SELECT COUNT(*) FROM randevu r JOIN doktor d ON d.doktor_id = r.doktor_id "
     "JOIN bolum b ON b.bolum_id = d.bolum_id WHERE b.ad = 'Kardiyoloji'"),
    ("Migren tanısı konan muayenelerin faturalarının toplamı nedir?", "zor", 2,
     "SELECT SUM(f.tutar) FROM muayene m JOIN fatura f ON f.muayene_id = m.muayene_id "
     "WHERE m.tani = 'Migren'"),
    ("İstanbul'daki hastaların tamamlanmış randevu sayısı kaç?", "zor", 2,
     "SELECT COUNT(*) FROM randevu r JOIN hasta h ON h.hasta_id = r.hasta_id "
     "WHERE h.sehir = 'İstanbul' AND r.durum = 'TAMAMLANDI'"),
    ("Hangi bölümün doktorları en çok muayene yapmış?", "zor", 3,
     "SELECT b.ad FROM bolum b JOIN doktor d ON d.bolum_id = b.bolum_id "
     "JOIN randevu r ON r.doktor_id = d.doktor_id "
     "JOIN muayene m ON m.randevu_id = r.randevu_id GROUP BY b.bolum_id "
     "ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Röntgen çekilen muayenelerin tanıları nelerdir?", "zor", 2,
     "SELECT DISTINCT m.tani FROM muayene m "
     "JOIN muayene_islem mi ON mi.muayene_id = m.muayene_id "
     "JOIN islem i ON i.islem_id = mi.islem_id WHERE i.ad = 'Röntgen'"),
    ("Ankara'daki hastaların ödenmemiş fatura toplamı ne kadar?", "zor", 4,
     "SELECT SUM(f.tutar) FROM hasta h JOIN randevu r ON r.hasta_id = h.hasta_id "
     "JOIN muayene m ON m.randevu_id = r.randevu_id "
     "JOIN fatura f ON f.muayene_id = m.muayene_id "
     "WHERE h.sehir = 'Ankara' AND f.odeme_durumu <> 'ODENDI'"),
    ("Her bölümün ortalama fatura tutarı nedir?", "zor", 4,
     "SELECT b.ad, AVG(f.tutar) FROM bolum b JOIN doktor d ON d.bolum_id = b.bolum_id "
     "JOIN randevu r ON r.doktor_id = d.doktor_id "
     "JOIN muayene m ON m.randevu_id = r.randevu_id "
     "JOIN fatura f ON f.muayene_id = m.muayene_id GROUP BY b.bolum_id"),
    ("En çok işlem uygulanan 3 muayenenin tanısı nedir?", "zor", 1,
     "SELECT m.tani FROM muayene m JOIN muayene_islem mi ON mi.muayene_id = m.muayene_id "
     "GROUP BY m.muayene_id ORDER BY SUM(mi.adet) DESC LIMIT 3"),
    ("Uzman doktorların baktığı hastaların şehirleri nelerdir?", "zor", 2,
     "SELECT DISTINCT h.sehir FROM hasta h JOIN randevu r ON r.hasta_id = h.hasta_id "
     "JOIN doktor d ON d.doktor_id = r.doktor_id WHERE d.unvan = 'Uzm. Dr.'"),
    ("Gastrit tanısı alan kaç farklı hasta var?", "zor", 3,
     "SELECT COUNT(DISTINCT r.hasta_id) FROM muayene m "
     "JOIN randevu r ON r.randevu_id = m.randevu_id WHERE m.tani = 'Gastrit'"),

    # ------------------------------------------- tarih mantığı (G-07 sınavı)
    ("Bu ay kaç fatura kesildi?", "orta", 0,
     "SELECT COUNT(*) FROM fatura WHERE tarih >= date('now','start of month') "
     "AND tarih <= date('now')"),
    ("Son 7 günde kaç randevu var?", "orta", 0,
     "SELECT COUNT(*) FROM randevu WHERE tarih >= date('now','-7 day') "
     "AND tarih <= date('now')"),
    ("2025 yılında kaydolan hasta sayısı kaç?", "orta", 0,
     "SELECT COUNT(*) FROM hasta WHERE kayit_tarihi >= '2025-01-01' "
     "AND kayit_tarihi <= '2025-12-31'"),
    ("Hâlâ yatan hastalar kaç gündür hastanede?", "orta", 0,
     "SELECT yatis_id, CAST(julianday('now') - julianday(giris_tarihi) AS INTEGER) "
     "FROM yatis WHERE cikis_tarihi IS NULL"),
    ("Ortalama yatış süresi kaç gün?", "orta", 0,
     "SELECT AVG(julianday(cikis_tarihi) - julianday(giris_tarihi)) FROM yatis "
     "WHERE cikis_tarihi IS NOT NULL"),

    # --------------------------------- alt sorgu / HAVING (yeni yetenek sınavı)
    ("Ortalamanın üzerinde ücreti olan işlemler hangileri?", "zor", 0,
     "SELECT ad FROM islem WHERE ucret > (SELECT AVG(ucret) FROM islem)"),
    # NOT: "hiç randevusu olmayan doktor" sorusu bilinçli olarak ELENDİ — bu veride
    # boş küme dönüyor ve boş küme döndüren HER sorgu "doğru" sayılırdı. Gold'un
    # ayırt edici olması, sorunun kendisi kadar önemlidir.
    ("Ortalamadan fazla randevusu olan doktorlar kimler?", "zor", 1,
     "SELECT doktor_id FROM randevu GROUP BY doktor_id "
     "HAVING COUNT(*) > (SELECT COUNT(*) * 1.0 / COUNT(DISTINCT doktor_id) FROM randevu)"),
    ("Kadın hastaların ortalama yaşı kaç?", "orta", 0,
     "SELECT AVG((julianday('now') - julianday(dogum_tarihi)) / 365.25) FROM hasta "
     "WHERE cinsiyet = 'K'"),
    ("Yıllara göre kaç hasta kaydolmuş?", "orta", 0,
     "SELECT strftime('%Y', kayit_tarihi), COUNT(*) FROM hasta "
     "GROUP BY strftime('%Y', kayit_tarihi)"),
    ("En sık uygulanan işlem hangisi?", "zor", 1,
     "SELECT i.ad FROM islem i JOIN muayene_islem mi ON mi.islem_id = i.islem_id "
     "GROUP BY i.islem_id ORDER BY SUM(mi.adet) DESC LIMIT 1"),
    ("En uzun yatış kaç gün sürmüş?", "orta", 0,
     "SELECT MAX(julianday(cikis_tarihi) - julianday(giris_tarihi)) FROM yatis "
     "WHERE cikis_tarihi IS NOT NULL"),
    ("Beşten fazla randevusu olan hasta sayısı kaç?", "zor", 1,
     "SELECT COUNT(*) FROM (SELECT hasta_id FROM randevu GROUP BY hasta_id "
     "HAVING COUNT(*) > 5)"),
    ("En çok hasta kaydı olan şehir hangisi?", "orta", 0,
     "SELECT sehir FROM hasta GROUP BY sehir ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Ortalama fatura tutarının üzerinde kaç fatura var?", "zor", 0,
     "SELECT COUNT(*) FROM fatura WHERE tutar > (SELECT AVG(tutar) FROM fatura)"),
]
