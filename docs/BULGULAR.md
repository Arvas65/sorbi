# Bulgular

Numara **yalnız burada** verilir. 1–32 ve tam açıklamaları arşivde
(`ip-01-02-altyapi` / `ip-46-cekirdek` dalları, eski `docs/is-hatti/BULGULAR.md`);
33–38 nöbet raporlarında (claude.ai proje belgeleri, 2026-09-02 … 09-07).

Durum: **açık** · **Review** (İhsan'ın triyajı bekliyor) · **kapandı** · **emekli** (ait olduğu parça kaldırıldı)

## Açık ve Review bekleyenler

| # | Bulgu | Durum | Not |
|---|-------|-------|-----|
| 15 | `admin` salt+hash'i public depo geçmişinde (`884f8d9`, `.sorbi/users.json`) | **açık — İhsan** | 08-23'te "kapandı" yazılmıştı; kapanan yalnız *yeni* sızıntıydı. Parola **döndürülmedikçe** açık: `parola.bat`. Geçmişi yeniden yazmak indirilmiş kopyaları geri almaz |
| 18 | Cetvel fazla kolon döndüren doğru cevabı yanlış sayıyor | **Review** | Cetvel politikası (SPEC B-2); v4'te eşleme cetveli (İP-56) doğarken karar gerekir |
| 27 | Başka makinenin karne koşumu `KARNE-GECMIS.log`'a yazabiliyor | **Review** | Öneri Ö-a: satıra `makine=` damgası, kıyas aynı damgalı son kayıtla. Gece hattı gitti ama CI ve bulut oturumları hâlâ karne koşuyor |
| 36 | `karsilastirilamaz()` kaydedilen değeri denetliyor, **uygulanmışlığını** değil — API'de `seed=42` damgada var, uç nokta reddediyor; kapı `mod`'a hiç bakmıyor | **açık** | Yerel ile API koşumu yanlışlıkla eşli karşılaştırılabilir. `eval/evaluate.py` |
| 39 | **v4 çekirdeği ürüne bağlı değil.** `portlar.py`'deki `Yurutucu`, `Esleyici`, `Onbellek`, `Cizer`, `SemaKaynagi`'nın hiçbirinin gerçek uygulaması yok; arayüz v3 serbest SQL yolunu gösteriyor | **açık** | PLAN Faz B'nin varlık sebebi. ~2.000 satır testli çekirdek kullanıcıya görünmüyor |
| 40 | `gemini-kur.bat` API anahtarını `setx` ile kullanıcı ortam değişkenine **düz metin** yazıyor; yapıştırılırken ekranda görünüyor | **SONRA** | Geliştirme makinesinde kabul edilebilir. Bulut dağıtımında (Faz C) anahtar bir sır deposundan (Azure Key Vault / Container Apps secret) okunmalı, ortam değişkenine kopyalanmamalı |

## 2026-09-30 toparlamasında kapananlar

| # | Bulgu | Durum | Nasıl |
|---|-------|-------|-------|
| 21 | Tazelik alarmı izlediği sürecin içinde | emekli | Gece hattı kaldırıldı |
| 33 | Yamasız `kontrol.bat` API modunda yanlış ADR-1 alarmı | emekli | `kontrol.bat` yeniden yazıldı |
| 34 | Gözcü saat dilimi | emekli | Gözcü kaldırıldı |
| 35 | Kota sıfırken rapora hiç girmiyor | **kapandı** | `46-yama` uygulandı: `_kota_satiri`, `tests/test_kota_kaydi.py` (6 test) |
| 37 | Gece koşumu `kontrol.bat` hükümlerini log'a yazmıyor | emekli | Gece hattı kaldırıldı |
| 38 | Hattın onarım yolu, onarılmasını gerektiren şeye bağlı | emekli | Hat kaldırıldı; ders CLAUDE.md § 7'de |
| 41 | Docker imajı `docs/kanit`'i taşıyordu ("paket kanıt taşımaz" kuralı imaja uygulanmamıştı) | **kapandı** | `.dockerignore`: `docs/`, `*.bat`, `.claude/` |

## Sıradaki numara: **42**
