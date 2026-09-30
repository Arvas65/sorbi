# SorBI — çalışma belleği

Her oturumda ilk okunan dosya. Amacı: yeni bir oturum projenin nerede
olduğunu, hangi kararların verildiğini ve **hangi hataların zaten yapıldığını**
yeniden keşfetmek zorunda kalmasın. Kısa tutulur; ayrıntı `docs/`'ta.

---

## 1. Bu ne

Türkçe doğal dilden **pano** üreten BI motoru. Müşterinin veritabanına
salt-okunur bağlanır, şemayı tarar, bir **anlam modeli** önerir (hangi tablo
olay, hangi kolon tarih, hangi satır geçersiz); insan onaylar. Soru bu modele
göre derlenir. Serbest LLM SQL'i yerine **deterministik derleyici**.

Depo: `github.com/Arvas65/sorbi` · Yerel: `C:\Users\Arvas\SorBı` · Sahibi: İhsan Arvas

Proje **FDE (Forward Deployed Engineer) yöntemiyle** yürür: her faz bir
müşteriye teslim edilebilir bir dilimdir. Plan: `docs/PLAN.md`.

## 2. Çalışma düzeni

```
Plan onayı → dal (ip-XX-ad) → Build → bağımsız Review → PR → [triyaj] → CI yeşil → [merge = Ship]
```

**Üç kapı İhsan'ındır:** Plan onayı · PR triyajı · merge (Ship).
Gerisi onay beklemeden yürür. Triyaj sözlüğü: **BLOK · DÜZELT · SONRA · KABUL**
(KABUL gerekçesiz verilmez).

- **Teslimat PR'dır.** Yama dosyası, tar paketi, proje belgesine gömülü diff yok.
- **master her zaman yeşil ve güncel.** Bir iş dalda iki haftadan uzun beklemez.
- **İhsan'dan terminal komutu istenmez.** Ondan istenen yalnız üç kapı. Yerelde
  güncellemek için `guncelle.bat`'a çift tıklar.
- Her PR açıklaması dört bölüm taşır: Review · Test · Verify · Devir
  (`.claude/skills/review-triyaj`). Devir'in üç satırı `docs/GUNLUK.md`'nin başına.
- Bulgu numarası **yalnız** `docs/BULGULAR.md`'de verilir.

## 3. Değişmezler

Birini bozan değişiklik geri alınır.

1. **Yalnız SELECT çalışır.** Doğrulama katmanı istisna fırlatmaz, kapalı devre başarısız olur.
2. **Üretilen SQL her zaman gösterilir.** Hata durumunda bile.
3. **Yerel mod varsayılandır**, veri makineden çıkmaz. API modunda dış servise
   yalnız şema metaverisi gider; gerçek değerler `generator.mask_context()` ile
   **koşulsuz** düşürülür. Bu bir ayara bağlanamaz. Dışarı giden her LLM isteği
   **çıkış kapısından** geçer (ADR-10): izin bağlamı yoksa ya da gövdede kişisel
   veri kalmışsa istek gönderilmez.
4. **Ölçülmemiş şey iddia edilmez.** Rapor yalnız çalıştırılmış sayıyı yazar.
5. **Kanıt dosyasının üzerine yazılmaz.** Her koşum damgalı ve benzersiz.
6. **Hiçbir hata sessizce yutulmaz.** `except: pass` yasak.
7. **Sır depoya girmez.** `.sorbi/`, `.env`, anahtar, hash — hiçbiri. Sızarsa
   takipten çıkarmak yetmez: **döndürülür.**

## 4. Nerede ne var

| Yol | Ne |
|-----|-----|
| `app/cekirdek/` | **v4 saf çekirdek** — anlam modeli, seçim, derleyici, pano, portlar (LLM'siz, DB'siz) |
| `app/baglanti/` | Çekirdeğin kenarları — anlam deposu (diğer portlar henüz yok, bkz. PLAN) |
| `app/guven.py` | B-7 sessiz yanlış kontrolleri (v3 yolu) |
| `app/validator.py` | Güvenlik kapısı — asla fırlatmaz |
| `app/guvenlik/` | Anonimleştirici, kişisel veri algılayıcıları, **çıkış kapısı** (ADR-10) |
| `app/executor.py` | v3 yürütücü — **İP-43 ile değişecek** |
| `ui/` | Streamlit — bugün **yalnız v3 serbest SQL yolunu** gösteriyor |
| `eval/evaluate.py` | 101 soruluk ölçüm · `eval/guven_olcum.py` mutasyon karnesi |
| `tests/cekirdek/altin/` | Derleyici altın çiftleri (43) |
| `docs/PLAN.md` · `docs/BULGULAR.md` · `docs/GUNLUK.md` | Plan, bulgular, oturum günlüğü |
| `docs/kararlar/` | ADR'ler · `docs/tasarim/` v4 SPEC, MİMARİ |
| `docs/guvenlik/GUVENLIK.md` | Türkiye mevzuat haritası, tehdit modeli, kontrol kataloğu |
| `docs/kanit/` | Ölçüm tablosu, karne geçmişi, iki taban koşum |

Arşiv (hiçbiri silinmedi): `olcum-otomatik` dalı gece hattını ve tüm kanıtı,
`ip-01-02-altyapi` dalı v3 iş hattı belgelerini taşır.

## 5. Durum

**Ölçülen (v3 yolu, 101 soru):** API modu %69–72 (altı koşum) · yerel %56–62 ·
G-11 hedefi %80 **hiçbir modda karşılanmadı**. Yanlışların %95–100'ü *sessiz*.
Bu, v4'ün varlık sebebidir: serbest SQL'in doğruluğu artırılarak güvenilirlik
gelmiyor; anlam modeli + derleyici ile yanlış ya **tutarlı ve denetlenebilir**
olur ya da hiç derlenmez.

**v4:** çekirdek yazıldı ve testli; **ürüne bağlı değil** (BULGU-39).
Sıradaki iş uçtan uca ince dilim — `docs/PLAN.md` Faz B.

**Bekleyen kapılar:** yok. Faz B onaylandı (2026-09-30), Build'de.

## 6. Alınmış kararlar

- **ADR-1 rev.2** taban model `qwen2.5-coder:7b-instruct` (McNemar p=2,8e-4)
- **ADR-2 rev.2** QLoRA ertelendi — yanlışın sayısını azaltır, görünmezliğini değil
- **ADR-3** Chroma RAG · **ADR-4** sqlglot ile lehçe taşınabilirliği
- **ADR-5 KABUL — B** (2026-09-30): yerel varsayılan, API açıkça seçilir. `config.py`'ye ve teste kilitli
- **ADR-8** anlam katmanı · **ADR-9** anlam modeli müşterinin makinesinde dosya
- **ADR-10 KABUL** (2026-09-30) veri sınırı ve anonimleştirme: sağlık/kamu verisi yabancı
  LLM'e hiçbir koşulda çıkmaz; diğer kişisel veri yalnız takma adlı
- Lisans çift: çekirdek açık, kurumsal katman kapalı
- FastAPI çekirdek + Streamlit istemci; tam yeniden yazım yok
- Roller: güvenlik-kritik modülleri (yürütücü, kanarya) İhsan yazar
- **2026-09-30** toparlama: gece hattı emekli, teslimat PR, FDE planı, müşteri
  sırası önce kurgusal dış müşteri → sonra (izinle) hastane pilotu

## 7. Bu projede zaten yapılmış hatalar

Ortak payda: **bir yerde geçerli olanın başka yerde de geçerli olduğunu
varsaymak.** Çare hep aynı — varsayımı çalıştırılabilir bir kontrole çevir.

| Hata | Ders |
|------|------|
| Tek koşumu sinyal sanmak | Tek koşum gürültüdür; aynı soru setinde **McNemar** |
| Kanıtın üzerine yazmak | Damgalı benzersiz ad + ekle-only günlük |
| Doğrulama katmanının doğruluğu bastırdığını görmemek | Reddedilen sorguları **oku** |
| GPU'nun kullanılmadığını fark etmemek | `--doctor` her ölçümden önce |
| ADR'yi yazıp koda indirmemek | Karar `config.py`'de ve bir testte değilse karar değildir |
| Gizlilik vaadini docstring'e yazmak | Vaat bir testle sabitlenir, ayarla değil |
| Beklenen değeri betiğe gömmek / referans günü sabitlemek | Sabit, yazıldığı makineye aittir; ölçüleni **kendi geçmişiyle** karşılaştır |
| Otomatik betiğin HEAD'i itmesi | Push reddedilmez, yanlış şeyi **başarıyla** taşır (BULGU-24) |
| Testin çöpünü `.gitignore`'a eklemek | Görünmezlik düzeltme değildir |
| Denetimin kapsamını tek dizine sabitlemek | Kapsam da bir varsayımdır, o da kilitlenir |
| Bulgu numarasını yazarken vermek | Numara tek yerde verilir |
| **Ölçüm hattını ürünün önüne koymak** | 2026-08-22 → 09-07 arası emek ölçüm hattının kendisine gitti; ürün 09-03'ten sonra ilerlemedi. **Ölçüm ürüne hizmet eder, yerine geçmez** |
| **Onarımı onardığı şeyin çalışmasına bağlamak** | Gece hattının dört onarım yolu da hattın koşmasını gerektiriyordu (BULGU-38) |
| **İşi dalda biriktirmek** | master iki ay geride kaldı; 26 commit hiç birleşmedi. İş PR ile biter |
| **Çekirdeği ürüne bağlamadan büyütmek** | 2.000 satır testli çekirdek, kullanıcının göremediği yerde (BULGU-39). Önce ince uçtan uca dilim |

## 8. Komutlar

```
guncelle.bat                master'ı çek, kur, denetle (Windows, çift tık)
kontrol.bat                 hızlı denetim (LLM'siz, ~1 dk) — CI'nın aynısı
kontrol.bat tam             + 101 soruluk ölçüm
gemini-kur.bat              API modu anahtarı · /kaldir ile yerele dön
parola.bat                  kullanıcı parolası değiştir

python -m ruff check .
python -m pytest tests/
python eval/evaluate.py --doctor | --gold-only
python eval/guven_olcum.py
```

## 9. Oturum sonunda

`docs/GUNLUK.md`'nin başına üç satırlık giriş: ne yapıldı, ne ölçüldü, ne açık.
