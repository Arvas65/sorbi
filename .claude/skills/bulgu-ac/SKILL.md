---
name: bulgu-ac
description: Planlanmamış bir sorun, kusur ya da risk fark edildiğinde kullan — kod, ölçüm hattı, belge ya da sürecin kendisinde. "bulgu", "bir sorun var", "bunu kaçırmışız", "backlog'a ekle" durumlarında devreye girer. Bulgunun kaybolmadan kaydedilmesini ve tarifinin de doğrulanmasını sağlar.
---

# Bulgu açma

Fark edilen ama o an çözülmeyen her şey **kaydedilir.** Kaydedilmeyen bulgu
yok sayılmış bulgudur.

## Nereye

- Küçük ve tanımlı → `docs/is-hatti/BACKLOG.md`, sıradaki İP numarasıyla
- Kök sebebi ilginç ya da ders çıkaran → `docs/is-hatti/v3/IP-XX/BULGU.md`
- Review kapısında karar gerekiyorsa → o İP'nin `REVIEW.md` tablosuna

## Ne yazılır

1. **Belirti** — ne görüldü, hangi çıktıda
2. **Kök sebep** — neden oluyor. "Bilmiyorum" yazmak, yanlış tahmin
   yazmaktan iyidir.
3. **Etkisi** — mümkünse sayıyla. "Aralık'ta koşulsaydı 8 kat gerileme
   gösterecekti" cümlesi bir önceliklendirmedir.
4. **Çözüm ya da öneri**
5. **Ders** — tekrarını önleyecek olan şey. Değerli olan genellikle bu.

## Bulgunun tarifi de doğrulanır

Bir bulgu backlog'da haftalarca **yanlış tarifle** durabilir. İP-16 tam bunu
yaptı: "dashboard tablo adlarını gömüyor" diyordu, dashboard öyle bir şey
yapmıyordu; gerçek nokta başka dosyadaydı.

Bir bulguyu çözmeden önce **tarifini doğrula.**

## Kapatınca

- Backlog satırını üstü çizili yap, tarih ve gerekçe ekle — silme
- Kök sebebi ilginçse `CLAUDE.md` § 7'ye bir satır ekle
- Tekrarını önleyecek bir test yazılabiliyorsa **yaz.** Varsayımı
  çalıştırılabilir bir kontrole çevirmek bu projedeki tek kalıcı çözümdür.
