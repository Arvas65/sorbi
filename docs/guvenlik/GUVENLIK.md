# SorBI — Güvenlik yönetimi

**Sürüm:** 1.0 · **Tarih:** 2026-09-30 · **Sahibi:** İhsan Arvas · **Hazırlayan:** Claude (güvenlik yöneticisi rolü)
**Kararlar:** ADR-5 (B, kabul) · ADR-10 (veri sınırı ve anonimleştirme, öneri)

Bu belge SorBI'nin güvenlik duruşunu tek yerde tutar: hangi Türk mevzuatı neyi
istiyor, neyi tehdit olarak görüyoruz, hangi kontrol **kodda** hangisi **yalnız
kâğıtta**. Kâğıttaki her kontrol "yok" sayılır.

---

## 1. Türkiye çerçevesi — SorBI'ye ne düşüyor

| Kural | Ne istiyor | SorBI'de karşılığı |
|---|---|---|
| **KVKK md. 9** (7499 ile, 1 Haz 2024) | Yurt dışı aktarım: yeterlilik kararı (bugün yok) ya da uygun güvence — pratikte **standart sözleşme**, imzadan itibaren **5 iş günü** içinde Kurul'a bildirim. Yabancı bulut/SaaS **sürekli aktarımdır**; arızi hâller (tek seferlik açık rıza) dayanak olamaz | Yabancı LLM API'si = yurt dışı aktarım. **Müşteri verisi için kapalı** (ADR-5 B, İP-45, kod). Açılacaksa ADR-5 D + sözleşme + bildirim birlikte |
| **KVKK md. 6** | Sağlık verisi özel nitelikli | Hastane veritabanı değerleri **S3**; B2'ye hiçbir koşulda çıkmaz (ADR-10) |
| **Kurul 2018/10** "yeterli önlemler" | Şifreli saklama + anahtarlar ayrı, işlem kaydı, uzaktan erişimde **2FA**, VPN/sFTP ile aktarım, periyodik yetki gözden geçirme, eğitim, gizlilik sözleşmesi | § 4 kontrol kataloğu: **K-7, K-8, K-9 bugün açık** |
| **Kurul 2019/10** | Veri ihlali: Kurul'a **72 saat** içinde bildirim | Müdahale planı yok → Faz E önkoşulu (K-15) |
| **Kişisel Sağlık Verileri Hk. Yön.** (21.06.2019) | Yurt dışı aktarımda KVKK md. 9; erişim hizmetin gereğiyle sınırlı; çıktılarda kimliksizleştirme/maskeleme | Rol modeli (analist/yönetici) var; bölüm bazlı yetki yok (K-10) |
| **2019/12 Genelge** | Kamu verisi: kurumun kendi sistemi ya da kurum kontrolündeki **yerli** sağlayıcı dışında bulutta saklanmaz | Kamu hastanesi müşterisinde **yalnız kurum içi kurulum** (B0/B1). Azure seçeneği yalnız sentetik demo için |
| **7545 Siber Güvenlik Kanunu** (19.03.2025) | Kamu ve kritik altyapı: siber olay bildirimi, **yerli çözüm önceliği**, yabancı çözüm için Başkanlık onayı | Sağlık kritik sektör: satışta "yerli yazılım" ve olay bildirimini destekleyen kayıt (K-11) gerekir |
| **KVKK Üretken YZ Rehberi** (Kasım 2025) | Veri en aza indirme, yabancı sağlayıcıda aktarım uyumu, çıktıda insan denetimi | Anonimleştirme (ADR-10), SQL her zaman görünür (değişmez 2), B-7 bayrakları |

> Bu tablo bir hukuk görüşü değildir. Müşteri sözleşmesinden önce bir KVKK
> avukatının okuması gerekir — özellikle standart sözleşme ve veri işleme
> sözleşmesi metinleri için.

## 2. Roller

- **Kurum içi kurulum (B0/B1):** müşteri **veri sorumlusu**dur; SorBI müşterinin
  makinesinde koşar, biz veriyi görmeyiz — veri işleyen bile değiliz. Tercih edilen model.
- **Barındırılan hizmet:** biz **veri işleyen** oluruz → veri işleme sözleşmesi
  (DPA), alt işleyen listesi (LLM sağlayıcısı dahil), ihlal bildirimi taahhüdü.
- **Yabancı LLM sağlayıcısı:** alt işleyen; yurt dışı aktarımın karşı tarafı.

## 3. Tehdit modeli

**Varlıklar:** müşteri veritabanı (S2/S3) · anlam modeli dosyası (sözlükte **gerçek
değerler** var → S2/S3) · denetim izi (sorular düz metin → S2/S3) · sonuç önbelleği ·
API anahtarı ve parolalar (S4).

| # | Tehdit | Etki | Kontrol | Durum |
|---|---|---|---|---|
| T1 | Kişisel/sağlık verisinin yabancı LLM'e gitmesi | KVKK md. 9 ihlali | Mod kilidi (İP-45) · anonimleştirme · **çıkış kapısı** (ADR-10) | **kodda** |
| T2 | v3 yolunun kilidi atlaması | T1'in aynısı | `pipeline.ask` bağlantıya göre karar verir; kapı izin olmadan çağrıyı durdurur | **kodda** (bulgu 2026-09-30, BULGU-43) |
| T3 | Yazma/silme sorgusu | Veri kaybı | SELECT-only doğrulayıcı · deterministik derleyici · **sunucu tarafı salt-okunurluk** | kısmi — İP-43 |
| T4 | Ağır sorguyla müşteri DB'sini kilitleme | Hizmet kesintisi (HBYS!) | Sunucu tarafı zaman aşımı + LIMIT | kısmi — İP-43 |
| T5 | LLM çıktısıyla SQL enjeksiyonu | T3 | v4'te LLM SQL yazmaz, `Secim` üretir; adlar sözlüğe karşı doğrulanır | **kodda** (v4) |
| T6 | Yetkisiz arayüz erişimi | Tüm veri | PBKDF2 parola, rol | kısmi — **2FA yok** (K-8) |
| T7 | Diskte düz metin kişisel veri | Cihaz kaybında sızıntı | denetim izi ve anlam modeli **şifresiz** | **açık** (BULGU-42) |
| T8 | Sır sızıntısı | Hesap ele geçirme | `.gitignore`, gitleaks CI, BULGU-15 döndürüldü | kısmi — BULGU-40 |
| T9 | Tedarik zinciri | Kod çalıştırma | Sabitlenmiş bağımlılıklar, pip-audit CI; gömme modeli çalışma anında indiriliyor | kısmi — BULGU-44 |
| T10 | Sonuç verisinin diskte/log'da kalması | S3 sızıntısı | Sonuç yalnız bellekte (Sınır 2); **kanarya testi** | kısmi — İP-54 |
| T11 | Sessiz yanlış cevapla yanlış karar | Hasta/finans zararı | SQL görünür, B-7 bayrakları, satır sayısı | kısmi |
| T12 | Denetim izinin sonradan değiştirilmesi | Hesap verebilirlik kaybı | Ekle-yalnız; **hash zinciri yok** | açık (K-12) |

## 4. Kontrol kataloğu

| # | Kontrol | Durum | Nerede / hangi iş |
|---|---|---|---|
| K-1 | Yalnız SELECT, kapalı devre doğrulayıcı | ✔ kodda | `app/validator.py` |
| K-2 | Mod kilidi: API yalnız sentetik demo DB'de | ✔ kodda | `app/akis/mod.py`, `pipeline.ask`, `eval` |
| K-3 | Anonimleştirme (izin listesi, geri dönüşlü, istek başına) | ✔ kodda | `app/guvenlik/anonimlestirici.py` |
| K-4 | Çıkış kapısı — varsayılan kapalı, tek çıkış noktası | ✔ kodda | `app/guvenlik/cikis_kapisi.py` ← `generator._api_chat` |
| K-5 | Bağımlılık açığı taraması | ✔ CI | `ci.yml` `guvenlik` işi + bekçi testleri |
| K-6 | Sır taraması | ✔ CI | gitleaks, çalışma ağacı |
| K-7 | Diskte şifreleme (denetim izi, anlam modeli), anahtar ayrı | ✘ | BULGU-42 → G2 |
| K-8 | Uzaktan erişimde 2FA | ✘ | G2 |
| K-9 | Sunucu tarafı salt-okunurluk + zaman aşımı | ✘ | İP-43 (İhsan) |
| K-10 | Bölüm/birim bazlı yetki (satır düzeyi) | ✘ | Faz E |
| K-11 | Güvenlik olay kaydı (kapı engelleri, giriş denemeleri) | kısmi | engel iletisi log'a gider; yapılandırılmış kayıt G2 |
| K-12 | Denetim izi hash zinciri | ✘ | G3 |
| K-13 | Kanarya — tam oturum sonrası veri ne gövdede ne diskte | ✘ | İP-54 (İhsan) |
| K-14 | Gömme modeli kurum içine sabitlenmiş (indirme yok) | ✘ | BULGU-44 → G3 |
| K-15 | İhlal müdahale planı (72 saat), etki değerlendirmesi, DPA taslağı | ✘ | Faz E önkoşulu |

## 5. Yol haritası

| Dalga | İçerik | Ne zaman |
|---|---|---|
| **G1** ✔ | K-2…K-6; v3 kilit açığı kapandı; iki bağımlılık yükseltildi | bu PR |
| **G2** | İP-43 (K-9) · diskte şifreleme (K-7) · 2FA (K-8) · yapılandırılmış güvenlik kaydı (K-11) | Faz B–C |
| **G3** | Kanarya (K-13) · hash zinciri (K-12) · gömme modelinin sabitlenmesi (K-14) | Faz C |
| **G4** | KVKK uyum paketi: etki değerlendirmesi, ihlal planı, DPA ve standart sözleşme taslakları, avukat okuması (K-15) · bölüm bazlı yetki (K-10) | Faz E önkoşulu |

**Hastane pilotunun güvenlik kapısı:** G2 + G3 + G4 tamam, kanarya yeşil, yalnız
B0/B1. Bu kapı ticari takvimle esnetilmez.

## Kaynaklar

- KVKK md. 9 ve 7499 sonrası rejim: [Güneş Partners](https://www.gunespartners.com/makale/yurt-disina-veri-aktarimi-7499-sayili-kanun) · [Netta](https://nettacompany.com/blog/kvkk-yurt-disina-veri-aktarimi-sunucunuz-yurt-disindaysa)
- Sağlık verisi ve md. 6: [Hanyaloğlu & Acar](https://www.hanyaloglu-acar.av.tr/malpraktis-tazminat/kvkk_degisiklik_saglik_verisi_yurt_disi_aktarim) · [Kişisel Sağlık Verileri Hk. Yön. — Esin](https://www.esin.av.tr/tr/2019/07/05/kisisel-saglik-verileri-hakkinda-yonetmelik-yayimlandi/) · [M. B. Kaya](https://mbkaya.com/saglik-bakanligi-kisisel-saglik-verileri-yonetmeligi/)
- Kurul 2018/10: [ProCompliance](https://www.procompliance.net/ozel-nitelikli-kisisel-verilerin-islenmesinde-veri-sorumlularinca-alinmasi-gereken-onlemler-hk-kvkk-karari/)
- İhlal bildirimi 72 saat: [ProCompliance](https://www.procompliance.net/kisisel-veri-ihlallerinin-kvkkya-bildiriminde-uyulacak-sureler-hk-kvkk-karari/)
- 2019/12 Genelge: [Sağlık Bakanlığı SBA](https://sba.saglik.gov.tr/TR-83952/201912-sayili-cumhurbaskanligi-bilgi-ve-iletisim-guvenligi-tedbirleri-genelgesi.html)
- 7545 Siber Güvenlik Kanunu: [MC Legal](https://www.mclegal.com.tr/7545-sayili-siber-guvenlik-kanunu-yururluge-girdi/)
- Üretken YZ Rehberi: [Erdem & Erdem](https://www.erdem-erdem.av.tr/bilgi-bankasi/uretken-yapay-zeka-ve-kisisel-verilerin-korunmasina-iliskin-rehber-yayimlandi)
