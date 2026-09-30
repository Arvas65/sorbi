# ADR-1 (revizyon 2) — Taban model

**Durum:** Kabul edildi, 2026-08-16 · **Değiştirdiği:** ADR-1 rev.1 (llama3.2:3b)
**Karar sahibi:** İhsan · **Gerekçe kaynağı:** ölçüm, tahmin değil

## Bağlam

Rev.1 tabanı `llama3.2:3b` seçmişti ve gerekçesi **fine-tune edilebilirlikti**:
6 GB'lık bir kartta 3B hem QLoRA ile eğitilebilir hem çıkarım yapabilir. O
tarihte hiçbir ölçüm yoktu; gerekçe donanım kısıtından türetilmişti.

## Ölçüm

Aynı 50 soruluk sette, aynı istem, aynı bağlam, aynı belirlenimci ayarlar:

| Model | Doğruluk |
|-------|----------|
| `llama3.2:3b` | %38 |
| `qwen2.5-coder:7b-instruct` | **%68** |

McNemar eşli testi: **p = 2,8 × 10⁻⁴**. Bu fark gürültü değil.

101 soruluk genişletilmiş sette qwen %62,4 (%95 GA: %52,9–%71,8).

Aynı gün istem ve bağlam üzerinde yapılan **altı** değişiklikten hiçbiri
3B'de anlamlı fark üretmedi (hepsi ±1 sorunun içinde kaldı). Yani mesele
istem mühendisliği değildi.

## Karar

Taban model **`qwen2.5-coder:7b-instruct`**.

## Sonuçları

1. **Fine-tune edilebilirlik varsayımı düştü.** 7B, 6 GB'lık kartta QLoRA ile
   yerel olarak eğitilemez. Eğitim yapılacaksa bulut GPU gerekir → ADR-2.
2. **Gecikme hedefi tartışmaya açıldı.** Model VRAM'e sığmıyor (%82 GPU /
   %18 CPU), p95 21,2 sn. G-12'nin 10 saniyelik hedefi 3B varsayımıyla
   konmuştu. Hedefin korunması ayrı bir karar gerektirir → G-12 notu.
3. **ADR-1 rev.1'in gerekçesi geçersiz, kararı tesadüfen zararsızdı:** 3B ile
   başlamak ölçüm hattını kurmayı ucuzlattı. Yanlış olan model seçimi değil,
   **ölçmeden seçmiş olmaktı.**

## Reddedilen seçenekler

| Seçenek | Neden değil |
|---------|-------------|
| 3B'de kalıp istem üzerinde çalışmak | Altı tur denendi, hiçbiri anlamlı fark üretmedi |
| 14B/32B'ye çıkmak | 6 GB kartta çalışmaz; yerel çıkarım vaadi düşer |
| Doğrudan API modeline geçmek | G-16/G-13 (veri dışarı çıkmaz) ürünün ana vaadi |
