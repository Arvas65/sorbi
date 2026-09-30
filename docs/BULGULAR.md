# Bulgular

Numara **yalnız burada** verilir. 1–32 ve tam açıklamaları arşivde
(`ip-01-02-altyapi` / `ip-46-cekirdek` dalları, eski `docs/is-hatti/BULGULAR.md`);
33–38 nöbet raporlarında (claude.ai proje belgeleri, 2026-09-02 … 09-07).

Durum: **açık** · **Review** (İhsan'ın triyajı bekliyor) · **kapandı** · **emekli** (ait olduğu parça kaldırıldı)

## Açık ve Review bekleyenler

| # | Bulgu | Durum | Not |
|---|-------|-------|-----|
| 18 | Cetvel fazla kolon döndüren doğru cevabı yanlış sayıyor | **SONRA** (triyaj 2026-09-30) | Cetvel politikası İP-56'da, eşleme cetveli doğarken kararlaştırılır |
| 36 | `karsilastirilamaz()` kaydedilen değeri denetliyor, **uygulanmışlığını** değil — API'de `seed=42` damgada var, uç nokta reddediyor; kapı `mod`'a hiç bakmıyor | **açık** | Yerel ile API koşumu yanlışlıkla eşli karşılaştırılabilir. `eval/evaluate.py` |
| 39 | **v4 çekirdeği ürüne bağlı değil.** `portlar.py`'deki `Yurutucu`, `Esleyici`, `Onbellek`, `Cizer`, `SemaKaynagi`'nın hiçbirinin gerçek uygulaması yok; arayüz v3 serbest SQL yolunu gösteriyor | **açık** | PLAN Faz B'nin varlık sebebi. ~2.000 satır testli çekirdek kullanıcıya görünmüyor |
| 40 | `gemini-kur.bat` API anahtarını `setx` ile kullanıcı ortam değişkenine **düz metin** yazıyor; yapıştırılırken ekranda görünüyor | **SONRA** | Geliştirme makinesinde kabul edilebilir. Bulut dağıtımında (Faz C) anahtar bir sır deposundan (Azure Key Vault / Container Apps secret) okunmalı, ortam değişkenine kopyalanmamalı |
| 42 | **Diskte düz metin kişisel veri.** Denetim izi (`.audit.db`) soruları, anlam modeli dosyası (`.sorbi/anlam/*.json`) sözlükteki gerçek değerleri şifresiz tutuyor. Hastane kurulumunda özel nitelikli veri; Kurul 2018/10 şifreli saklama ve ayrı anahtar ister | **DÜZELT** (karar 2026-09-30) | **(a)** disk şifreleme (BitLocker/LUKS) kurulum önkoşulu + kurulumda denetim; **(c′)** denetim izi yerelde TAM tutulur ("X'in verisine kim baktı" sorusu cevaplanabilmeli — sağlık erişim kaydının amacı), makineden çıkan her kopya (dışa aktarım, destek paketi, log gönderimi) anonimleştiriciden geçer. Asıl (c) — izi jetonlu tutmak — hesap verebilirliği bozduğu için uygulanmadı. G2 |
| 44 | Gömme modeli (`paraphrase-multilingual-MiniLM`) ilk çalışmada HuggingFace'ten indiriliyor: tedarik zinciri riski ve kurum içi (internetsiz) kurulumda çalışmama | **açık** | GÜVENLİK K-14, G3: model dosyası sürüm + özetle sabitlenip pakete girer |

| 47 | **Giriş formunda deneme sınırı yok** — parola denemesi sınırsız | **açık** | GÜVENLİK G2: hesap kilidi / artan bekleme + güvenlik olay kaydı (K-11) |
| 49 | `test_soru_sor_cevap_al_ve_sayfa_yeniden_cizilir` 2026-09-30'da tam süitte **bir kez** düştü; ardından 13 tam koşumda ve 6 tek başına koşumda hiç düşmedi. Hata metni kaydedilmedi (çıktının yalnız son satırı alınmıştı) | **açık — gözlem** | Kök neden bilinmiyor; "düzeldi" sayılmaz. Tekrarlarsa test tam hata metnini basar (`_hatalar`). CI'daki üç Python koşumu izlenir. Ders: kararsızlık şüphesinde çıktının tamamı saklanır |
| 48 | **İlk kurulum ekranı, ekrana ilk ulaşanı yönetici yapıyor.** Kurum içinde kabul edilebilir; internete açık kurulumda (Azure demo) yönetici hesabı ele geçirme | **açık — Azure öncesi BLOK** | İlk yönetici kurulumu komut satırından ya da tek kullanımlık kurulum anahtarıyla; arayüzden kaldırılır |

## 2026-09-30 duman testinde kapananlar

| # | Bulgu | Durum | Nasıl |
|---|-------|-------|-------|
| 46 | **Ana sayfa ilk sorudan sonra çöküyordu** (2026-08-29 → 09-30). B7R-05 denetim kaydına sekizinci kolonu ekledi, "Geçmiş" sekmesi yedi kolon adı veriyordu; Streamlit bütün sekmeleri çizdiği için sayfanın tamamı düştü. 693 testin hiçbiri arayüzü çalıştırmıyordu | **kapandı** | Kolon adları tek kaynaktan (`audit.KAYIT_KOLONLARI`); `tests/test_arayuz_duman.py` (Streamlit AppTest, 6 test — eski kodla asıl test düşüyor); CI arayüz bağımlılıklarını kurar |

## 2026-09-30 güvenlik turunda kapananlar

| # | Bulgu | Durum | Nasıl |
|---|-------|-------|-------|
| 43 | **v3 yolu mod kilidini atlıyordu.** `pipeline.ask` `config.MODE`'u doğrudan kullanıyordu; `SORBI_MODE=api` tanımlı makinede (İhsan'ınki) bir müşteri DB'sine bağlanmak soruyu, şema bağlamını ve onarımda hatalı SQL ile DB hata iletisini dış servise gönderiyordu | **kapandı** | Karar bağlantıya göre (`cikarim_modu`); tüm LLM çağrıları izin bağlamında; **çıkış kapısı** izinsiz çağrıyı ağa çıkmadan durdurur. `tests/test_cikis_kapisi.py` |
| 45 | Bilinen açıklı bağımlılıklar: `urllib3` 2.7.0 (3 CVE, sıkıştırma bombası dahil), `oauthlib` 3.3.1 | **kapandı** | 2.8.0 ve 4.0.0'a yükseltildi, başka pin değişmedi. `chromadb` 1.5.9'un 4 açığı **KABUL**: hepsi HTTP sunucusuna ait, SorBI gömülü koşuyor — bekçi `tests/test_guvenlik_bagimlilik.py` |

## 2026-09-30 toparlamasında kapananlar

| # | Bulgu | Durum | Nasıl |
|---|-------|-------|-------|
| 21 | Tazelik alarmı izlediği sürecin içinde | emekli | Gece hattı kaldırıldı |
| 33 | Yamasız `kontrol.bat` API modunda yanlış ADR-1 alarmı | emekli | `kontrol.bat` yeniden yazıldı |
| 34 | Gözcü saat dilimi | emekli | Gözcü kaldırıldı |
| 35 | Kota sıfırken rapora hiç girmiyor | **kapandı** | `46-yama` uygulandı: `_kota_satiri`, `tests/test_kota_kaydi.py` (6 test) |
| 37 | Gece koşumu `kontrol.bat` hükümlerini log'a yazmıyor | emekli | Gece hattı kaldırıldı |
| 38 | Hattın onarım yolu, onarılmasını gerektiren şeye bağlı | emekli | Hat kaldırıldı; ders CLAUDE.md § 7'de |
| 27 | Başka makinenin karne koşumu kıyas referansı oluyordu | **kapandı** (DÜZELT) | `makine=` damgası (ana makine adının SHA-256 özeti), kıyas aynı damgalı son kayıtla; `tests/test_karne_makine_damgasi.py` — eski kodla 5 bekçinin 4'ü düşüyor |
| 15 | `admin` salt+hash'i public depo geçmişinde (`884f8d9`) | **kapandı** | 2026-09-30: İhsan parolayı döndürdü; geçmişteki hash artık değersiz |
| 41 | Docker imajı `docs/kanit`'i taşıyordu ("paket kanıt taşımaz" kuralı imaja uygulanmamıştı) | **kapandı** | `.dockerignore`: `docs/`, `*.bat`, `.claude/` |

## Sıradaki numara: **50**
