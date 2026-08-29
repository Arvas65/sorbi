# İP-33 — Triyaj uygulaması · VERIFY

**Tarih:** 2026-08-23 · **Kaynak:** İP-03c Review triyajı + BULGU-01…16 triyajı
**Karar:** İhsan Arvas — 16 açık maddenin tamamı **DÜZELT**

Verify, Test'ten farklıdır ve karıştırılmamalıdır:
**Test** sorar — kod, spec'in dediğini yapıyor mu?
**Verify** sorar — spec'in ve belgelerin iddiası gerçekte doğru mu?

---

## 1. Kapatılan maddeler ve dayanakları

| # | Ne yapıldı | Dayanak (ölçüm / test) |
|---|-----------|------------------------|
| **BULGU-N4** | `tests/conftest.py` içe aktarma anında tohumluyor; `skipif` ve koşullu `pytest.skip` üç dosyadan silindi | DB silinip süit koşuldu: **415 geçti, 0 atlandı**. `test_suit_dururlugu.py` geri gelmesini kilitliyor |
| **B7R-06** | `bilinen_degerler` `tablo.kolon` anahtarı taşıyor; takma ad çözümlemesi | `bolum.ad='EKG'` yakalanıyor; gereksiz bayrak sabit |
| **B7R-03** | `filtresiz` zaman + durum daraltmasını görüyor | `where_dus` **%59 → %83** |
| **B7R-01** | `sema_ortusmez` kolon adlarına da bakıyor; takas her koşumda basılıyor | açıkken gereksiz bayrak **7 → 3** |
| **B7R-08 / BULGU-04** | Havuza 4 gerçekçi hata ailesi; iki yeni kontrol | havuz 239 → **306**; `deger_takasi` %21 → **%74** |
| **B7R-05** | Güven kodları denetim izinde; `audit.guven_karnesi()` | `test_audit_guven.py` — yerinde göç dahil |
| **BULGU-09/10** | Regresyon kapısı eşli McNemar kararına bağlandı | `test_regresyon_kapisi.py` — ölçülen gürültü (4/3) kapıyı **açmıyor**, 12/0 **açıyor** |
| **BULGU-05** | `docs/kanit/sonuclar-<damga>.json` yazılıyor | rapor artık `.gitignore`'daki bir dosyayı kaynak göstermiyor |
| **BULGU-06** | "yakalanan" → **"reddedilen"**; karne tarafı "bayraklanan" | rapor iki tanımı ayırıyor ve farkı yazıyor |
| **BULGU-08** | `seed` isteğe gerçekten konuyor; damga metni **koddan** türetiliyor | `test_api_istegi_seed_gonderiyor`, `test_damga_metni_koddan_tureniyor` |
| **YENİ-C** | Soru bazında gerçek mod kaydediliyor; rapora `mod_dagilimi` satırı | damga bölünmüş koşumu artık gizleyemiyor |
| **BULGU-15** | `.gitignore` + `test_depo_hijyeni.py` | takip edilen yasak yol yok. **Geçmiş temizlenmedi — aşağıya bak** |
| **YENİ-A** | ADR-3, ADR-4 yazıldı; ADR-5 taslağı depoya indi | `test_claude_md_de_anilan_her_adr_dosyasi_var` |
| **YENİ-B** | CI'a LLM'siz B-7 karnesi eklendi; regresyon kapısının **nerede** koştuğu yazıldı | `ci.yml` |

## 2. Verify kontrol listesi

- [x] `CLAUDE.md`'nin B-7 iddiası koda karşı kontrol edildi — "%83 yakalama"
      cümlesi düzeltildi; artık **iki karne ayrı ayrı** yazıyor (mutasyon %80,1 ·
      saha %20) ve aralıkların kesişmediği belirtiliyor
- [x] `CLAUDE.md`'de adı geçen her ADR'nin dosyası var (testle kilitlendi)
- [x] Belgede adı geçen komutlar koşturuldu: `pytest`, `ruff check .`,
      `eval/guven_olcum.py`, `eval/evaluate.py --gold-only`
- [x] Ölçüm iddiaları bu ağaçta yeniden üretildi (sayılar aşağıda)
- [x] Kapsam dışı bırakılanlar kapsam dışı kaldı — `evaluate.py`'nin LLM'li
      yolu değiştirilmedi, `--gold-only` yolu LLM içe aktarmıyor
- [ ] **Güvenlik kapıları canlı doğrulanmadı** — gerçek Postgres'e yazma
      denemesi ve 30 sn iptali bu turda koşulmadı; kapsam dışıydı

## 3. Ölçümler (bu ağaçta, 2026-08-23)

```
pytest tests/          415 geçti, 0 atlandı   (öncesi: 363 geçti)
                       demo/*.db SİLİNMİŞ hâlde koşuldu
ruff check .           temiz
kapsam                 %79,0  (eşik %70)
guven_olcum.py         gold=101 alarm=1 mutant=306 yakalanan=245 (%80,1)
```

Ölçüm günü `2026-08-21`'e sabit; referans gün damgada.

## 4. Ölçülmeyen, dolayısıyla iddia edilmeyen

- **Yeni kontrollerin GERÇEK model hatalarındaki karnesi.** `deger_uyumsuz` ve
  `distinct_eksik` mutasyon havuzunda ölçüldü; sahadaki sayı ancak bir sonraki
  101'lik koşumda çıkar. Bu tam olarak BULGU-04'ün uyardığı ayrımdır ve burada
  tekrarlanmaması için yazılıyor: **%80,1 bir mutasyon sayısıdır.**
- **`seed`'in sunucuda uygulanıp uygulanmadığı.** Gönderiliyor; uygulandığının
  tek kanıtı aynı gece art arda iki koşumun birebir aynı çıkmasıdır. O koşum
  alınmadı — ADR-5 Ö-7 bu yüzden "kısmen" durumunda.
- **`join_ici_disi` ailesi** havuzda yalnız 1 mutant üretiyor; o sayı bir şey
  ölçmüyor. Daha çok JOIN'li gold sorgusu gerekiyor.

## 5. Kapanmayan ve İhsan'a kalan

1. **BULGU-15 — admin parolası döndürülmeli.** `.sorbi/users.json` `884f8d9`
   commit'inde uzak depo geçmişinde duruyor. Takipten çıkarmak onu oradan
   silmez. Depo herkese açıksa bu madde **BLOK**'tur.
2. **YENİ-B — CI'ın ilk yeşil koşumu.** Bu push, CI'ı gerçek kodla tetikleyen
   ilk push. Nöbetin GitHub Actions erişimi yok.
3. **ADR-5 (İP-32) Ship kararı.** Ö-1, Ö-2, Ö-3 bu İP'te kapandı; **Ö-6**
   (ticari şartlar) ve **Ö-7** (belirlenim doğrulaması) açık.
