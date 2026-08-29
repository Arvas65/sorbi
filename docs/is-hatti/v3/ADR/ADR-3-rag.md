# ADR-3 — Bağlam getirme: gömme tabanlı RAG, anahtar-kelime yedeğiyle

**Durum:** **Kabul edildi** · Yazıya geçirildi 2026-08-23 (YENİ-A)
**İlgili:** G-05, G-06 · `app/schema_rag.py`

> Bu karar kodda uygulanmıştı ama dosyası yoktu; `CLAUDE.md` § 6 ona atıf
> yapıyordu. Dayanaksız atıf, Verify sınıfı bir hatadır — README'nin var
> olmayan bir `training/` klasörünü anlatması ile aynı aile.

## Sorun

Şemanın tamamı isteme sığmıyor ve sığsaydı bile zararlı olurdu: model
alakasız on tablonun içinde doğru olanı seçmek zorunda kalır. Soru başına
yalnız ilgili tabloları, ilişkilerini ve JOIN yollarını vermek gerekiyor.

## Karar

Chroma üzerinde gömme tabanlı getirme; **anahtar-kelime yedeği zorunlu.**

Yedek bir konfor değil, bir kısıt: CI'da ve hafif kurulumda `torch`
kurulmuyor (bkz. `.github/workflows/ci.yml`, "yalnız core + dev"). Chroma
yoksa `schema_rag` sessizce anahtar-kelime moduna düşer ve ölçüm koşmaya
devam eder. Ölçüm hattının bir gömme modeline bağımlı olması, cetveli
bağımlılığa bağlamak olurdu.

## Reddedilen seçenekler

| Seçenek | Neden reddedildi |
|---------|------------------|
| Şemanın tamamını isteme koymak | Bağlam penceresi ve dikkat dağılımı; 8 tablo üstünde doğruluk düşüyor |
| Yalnız anahtar-kelime | Türkçe çekim ve eş anlamlılarda kaçırıyor ("ciro" ↔ `fatura.tutar`) |
| Yalnız gömme (yedek yok) | CI ve hafif kurulum `torch` kurmuyor; ölçüm koşamaz hale gelirdi |

## Sonuçları

- `demo/glossary.json` iş terimini şema nesnesine bağlar (G-06); getirme
  hangi modda olursa olsun sözlükten geçer.
- **Değer örneklemesi getirmenin bir parçasıdır** (İP-19): şemayı bilmek
  yetmiyordu, DEĞERLERİ bilmemek 0 JOIN'li soruların yarısını düşürüyordu.
- Maskeli kolonlar (G-16) hiçbir modda örneklenmez.
