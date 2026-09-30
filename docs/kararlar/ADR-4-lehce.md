# ADR-4 — Lehçe taşınabilirliği ve doğrulama katmanı: sqlglot

**Durum:** **Kabul edildi** · Yazıya geçirildi 2026-08-23 (YENİ-A)
**İlgili:** G-10, G-18 · `app/validator.py`, `eval/tarih_sabitle.py`

> ADR-3 gibi: kararın kendisi koda inmişti, belgesi yoktu.

## Sorun

İki ayrı ihtiyaç aynı araca bakıyor:

1. **Taşınabilirlik (G-10):** demo SQLite'ta koşuyor, hedef müşteri
   Postgres. Model tek bir lehçe üretiyor.
2. **Güvenlik (G-18):** üretilen SQL çalıştırılmadan önce "yalnız SELECT"
   kuralının **ayrıştırıcı düzeyinde** doğrulanması gerekiyor. Düzenli
   ifadeyle yapılan bir kontrol, yorum satırı ve iç sorguyla kandırılır.

## Karar

Her iki iş de **sqlglot** ile yapılır: tek bir AST, tek bir doğruluk kaynağı.

Doğrulama katmanının sözleşmesi: **asla istisna fırlatmaz, kapalı devre
başarısız olur.** Ayrıştırılamayan bir sorgu reddedilir; "anlamadım o hâlde
geçir" diye bir yol yoktur (CLAUDE.md § 3, değişmez 1).

## Reddedilen seçenekler

| Seçenek | Neden reddedildi |
|---------|------------------|
| Düzenli ifadeyle SELECT kontrolü | Yorum, iç sorgu ve CTE ile kandırılabilir; güvenlik kapısı olamaz |
| Her lehçe için elle SQL | Ölçüm hattı ikiye katlanır, gold SQL iki kez bakım ister |
| ORM üzerinden üretim | Model doğal dilden SQL üretiyor; araya ORM koymak yeni bir çeviri katmanı ekler |

## Beklenmedik kazanç

Aynı AST İP-23'te üçüncü bir iş için kullanıldı: `eval/tarih_sabitle.py`
SQL içindeki `'now'` argümanlarını ölçüm gününe çeviriyor — ve bunu yalnız
**fonksiyon argümanı konumunda** yapıyor, `WHERE durum = 'now'` gibi bir veri
değerine dokunmuyor. Metin değiştirmeyle bu ayrım yapılamazdı.
