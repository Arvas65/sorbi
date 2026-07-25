# SorBI v2 — Kapsam Notu (Sistem Analisti Bilgilendirmesi)

**Tarih:** 2026-07-25 · **Durum:** v1 tamamlandı, v2 başladı · **Karar sahibi:** İhsan

## v1 Kapanış Özeti

MVP uygulama sırasının (sistem analizi EK bölümü) 1–9. adımları tamamlandı:

- Demo şema + 50 soruluk test seti üretildi; gold SQL sağlığı: 50/50 (`--gold-only` koşucusu eklendi)
- Pipeline uçtan uca çalışıyor: ön işleme → RAG → üretim → doğrulama → salt-okunur yürütme → denetim izi
- 75 birim testi eklendi (`tests/`), tümü geçiyor — G-07/09/10/14/18 kapıları test altında
- Arayüz: SQL her zaman görünür (G-02), sonuç grafiği, CSV indirme, şema tarayıcı
- Bilinen saha sorunu: Windows + Ollama 0.30.x Vulkan backend çökmesi (0xe06d7363) —
  uygulama artık anlaşılır hata mesajı veriyor; CPU'ya zorlama geçici çözümü belgelendi
- Bekleyen v1 kalıntısı: execution accuracy ölçümü (G-11) Ollama sorunu çözülünce koşulacak;
  QLoRA (7. adım) kararı bu ölçüme bağlı (ADR-2 koşulu korunuyor)

## v2 Kapsamı — "BI tarafı parlasın"

Ürün tezi: SOR = Türkçe text-to-SQL, BI = yönetici bakışı. v1 SOR'u kanıtladı; v2 BI'ı ekler.

**v2.1 (bu sürümde eklendi)**

- `ui/pages/1_Dashboard.py`: Hizmet Analizi dashboard'u
  - Filtre şeridi: bölüm, doktor unvanı, hasta şehri, ödeme durumu, tarih aralığı
  - KPI şeridi: randevu, muayene, ciro, geciken tahsilat, iptal %, gelmeme %
  - Bölüm bazlı bar grafik (muayene/ciro anahtarı), bölüm × ay ısı haritası, doktor özet tablosu
  - Her görselin altında "SQL göster" — G-02 ilkesi dashboard'a taşındı
  - **Yönetici Önerisi**: KPI özeti yerel LLM'e gider (yalnız toplam sayılar, hasta verisi gitmez — G-16
    ile uyumlu); LLM yoksa kural tabanlı eşik önerileri (iptal >%10, geciken tahsilat >%15 vb.)

**v2 adayları (önceliklendirme bekliyor)**

1. Dashboard'u SOR ile köprüle: "bu grafiği filtrele" tarzı doğal dil filtre komutları
2. Trend görünümü: aylık ciro/muayene çizgi grafikleri + yıl karşılaştırma
3. Dashboard tanımlarını konfigürasyona taşı (YAML) — hastane dışı şemalara taşınabilirlik (ADR-4 ruhu)
4. Zamanlanmış PDF/e-posta yönetici raporu
5. Execution accuracy panosu: eval sonuçlarının arayüzden izlenmesi (G-11 görünürlüğü)

**Pazarlık edilemezler v2'de de geçerli:** salt-okunur bağlantı, SELECT-only, 30 sn limit,
maskeleme, denetim izi (G-14/16/17/18). Dashboard sorguları da aynı kanaldan geçer.
