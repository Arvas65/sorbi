---
name: olcum-al
description: SorBI'de bir ölçüm almak, sonucunu yorumlamak ya da iki ölçümü karşılaştırmak gerektiğinde kullan. Doğruluk (G-11), gecikme (G-12), güven kontrolü karnesi ve kanıt kaydı bu skill'in konusudur. "ölçüm al", "accuracy", "karne", "koşum", "bu sayı ne anlama geliyor" gibi durumlarda devreye girer.
---

# Ölçüm alma ve yorumlama

Bu projede sayı üretmek kolay, **güvenilir** sayı üretmek zor. Buradaki kurallar
gerçek hatalardan çıkarıldı; her biri en az bir kez pahalıya mal oldu.

## Ölçümden önce

1. `python eval/evaluate.py --doctor` — **atlama.** GPU keşfi sessizce
   başarısız olur ve model CPU'ya düşer; tek belirti sürelerdir. Bir kez
   iki saat kaybettirdi.
2. `DOCTOR_OZET` satırına bak: `hizlandirma=cpu` ise **ölçüm alma.**
   Önce `OLLAMA_VULKAN=0` ile Ollama'yı yeniden başlat.
3. `model=` alanının ADR-1'deki modelle aynı olduğunu doğrula. Bir kez
   ayrıştı ve 24 puanlık hayali gerilemeye yol açacaktı.
4. `python eval/evaluate.py --gold-only` — cetvel sağlam mı (101/101).

## Ölçüm geçerliyse

Bir sayı ancak şu koşullarda **karşılaştırılabilir**:

- aynı soru sayısı (`n`)
- aynı referans günü (`olcum_gunu`) — 13 soru zamana bağlı
- aynı model, aynı `temperature`/`seed`/`num_ctx`
- aynı `ORNEK_DEGERLER` ayarı

Bunlardan biri farklıysa `karsilastirilamaz()` zaten reddeder. **Reddi ezme.**

## Sayıyı yorumlarken

- **Tek koşum sinyal değildir.** ~1 sorulukk oynama gürültüdür.
- Aynı soru setinde iki yapılandırmayı kıyaslıyorsan **McNemar** kullan,
  binom standart hatası değil — tasarım eşlidir.
- Güven aralığını yaz. "%62" değil, "%62,4 (GA %52,9–71,8)".
- Hedefin aralığın içinde mi dışında mı olduğunu söyle.

## Sessiz yanlış

`sessiz_yanlis` = sorgu çalıştı, temiz tablo döndü, cevap yanlış.
İzlenecek asıl sayı `yanlislarda_sessiz_pay`. Doğruluk yükselirken bu pay
da yükseliyorsa ürün güvenilirliği **kötüleşiyor** demektir, iyileşmiyor.

## Güven kontrolü karnesi

`python eval/guven_olcum.py` — LLM'siz, ~5 sn. Gold'u kasten bozup
kontrolün yakalayıp yakalamadığına bakar.

İki sayı ters yönde çeker:
- **yakalama** yükselmeli
- **yanlış alarm** düşmeli — ve bu daha önemlidir. Sürekli bağıran bir uyarı
  okunmaz hâle gelir; o noktadan sonra sessiz yanlış geri döner.

`zbos=0` olmalı. Değilse referans gün veri setine uymuyor demektir; sayılar
o hâliyle anlamsızdır.

Karne kendi geçmişiyle karşılaştırılır (`docs/kanit/KARNE-GECMIS.log`),
sabit bir beklentiyle değil — sabit, yazıldığı makinenin verisine aittir.

## Kanıt

- Her koşum benzersiz ada yazılır, **üzerine yazılmaz**
- `docs/kanit/OLCUMLER.md` ekle-only günlüktür
- Damga: tarih, ölçüm günü, commit, model, mod, sıcaklık, seed, num_ctx

## Ölçmediğin şeyi yazma

Rapor yalnız çalıştırılmış sayıyı içerir. Beklenti varsa "beklendi, ölçülmedi"
diye ayrı yazılır. Bu kural iki kez kendi hatamı yakaladı.
