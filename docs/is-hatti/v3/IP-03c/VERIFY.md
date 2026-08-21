# İP-03c — VERIFY

**Soru:** İddia edilen ne, kanıtı ne, kanıt nerede duruyor?

| İddia | Kanıt | Nerede |
|-------|-------|--------|
| Sessiz yanlışın çoğu artık bayraklanıyor | 195/240 mutant yakalandı | `eval/guven_olcum.py` çıktısı, TEST.md §2 |
| Uyarı gürültüye boğmuyor | 101 doğru sorgudan 1'i bayrak aldı | aynı |
| Kontrol hattı çökertmiyor | "asla istisna fırlatmaz" sözleşmesi + 3 test | `tests/test_guven.py` |
| Kapatma kararı ölçüme dayanıyor | üç yapılandırmanın karşılaştırması | `app/config.py` yorumu, REVIEW B7R-01 |
| Uçtan uca hat test altında | 13 yeni test, kapsam %0 → %86 | `tests/test_pipeline.py` |
| Kapsam gerilemesi artık CI'ı kırar | `fail_under = 70` | `pyproject.toml` |

## Doğrulanamayanlar (kasten)

- **Doğruluğa etkisi: sıfır olmalı.** Güven kontrolü SQL'i değiştirmez,
  sorguyu yeniden çalıştırmaz, sonucu filtrelemez. Yalnız mesaj ekler.
  Bunu bir sonraki koşumdaki accuracy sayısının **değişmemesi** doğrulayacak;
  değişirse kontrol yan etki üretiyor demektir ve bu bir hatadır.
- **Gecikmeye etkisi.** Ölçülecek: p50/p95 bir önceki koşumla aynı kalmalı.
- **B7R-04 (İ harfi düzeltmesi)** RAG anahtar-kelime yolunu değiştirdi.
  Chroma birincil yol olduğu için etkinin sıfır olması bekleniyor ama
  **bu bir beklenti, ölçüm değil.**

## Kabul kapısı (ship öncesi)

Aşağıdakiler yeşil olmadan `v2.4.0` etiketi atılamaz:

- [ ] Ollama'lı 101 soruluk koşum yapıldı, accuracy **düşmedi**
- [ ] Aynı koşumda p95 gerilemedi
- [ ] Raporda "Güven kontrolü karnesi" bölümü doldu ve yakalama > %50
- [ ] BULGU-06 kapandı: en az bir yeşil CI koşumu var
- [ ] İhsan REVIEW'daki 7 maddeyi triyaj etti
