# ADR-2 (revizyon 2) — Fine-tune kararı

**Durum:** **Tetiklendi ama ERTELENDİ** · 2026-08-16

## Karar kuralı (rev.1'den)

> RAG-only baseline 101 soruluk sette %80'in altında kalırsa QLoRA fine-tune
> yeniden açılır.

## Ölçüm

**%62,4** (63/101), %95 GA %52,9–%71,8. Hedef, aralığın **3,7 standart hata**
üzerinde. Tetiklenme tartışmasız.

## Ama sorunun kendisi değişti

Rev.1 "3B'yi fine-tune edelim mi" diye soruyordu. ADR-1 rev.2'den sonra soru
"7B'yi bulutta eğitip yerelde mi koşturalım" oldu — bu farklı bir maliyet,
farklı bir risk ve farklı bir gizlilik konuşması (eğitim verisi buluta gider).

## Karar

**Ertelendi.** Önce B-7 (sessiz yanlış) yapıldı — İP-03c. Gerekçe:

Doğruluk %62'den %80'e çıksa bile, ölçüm kalan yanlışların **%95'inin sessiz**
olduğunu gösteriyor. Yani fine-tune, yanlış cevap **sayısını** azaltır ama
yanlış cevabın **görünmezliğini** azaltmaz. Sistem analizi B7'nin kaydettiği
risk — "hata verse anlarız, yanlış sayı verirse felaket" — doğrulukla değil,
görünürlükle çözülür.

Bugünün ölçümü bu sıralamayı doğruladı: B-7 bir tur çalışmayla bilinen
yanlışların %81'ini bayraklanır hale getirdi; aynı çabayla doğrulukta 18
puan alınamazdı.

## Yeniden açılma koşulu

Aşağıdakilerden biri gerçekleşince ADR-2 tekrar masaya gelir:

1. B-7 gerçek koşumda (mutasyon değil) yakalama > %50 ile doğrulandı **ve**
   doğruluk hâlâ < %80 → fine-tune sıradaki en büyük kazanç olur
2. İstem/bağlam turu 2 (7B üzerinde, hata analizi tabanlı) tükendi
3. Bulut GPU maliyeti ve eğitim verisinin nereye gideceği İhsan tarafından
   onaylandı (G-13 gizlilik vaadiyle çelişmediği gösterilerek)
