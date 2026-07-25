# SorBI — Analist Teknik Yeterlilik Okuma Listesi

Sıra önerisi: yıldızlı (★) olanlar önce — projenin kararlarını doğrudan etkileyenler.

## 1. Text-to-SQL temelleri ve ölçüm (G-11'in bilimi)

- ★ **Spider** — Yu et al., 2018. Alanın standart kıyas seti; "execution accuracy" kültürü buradan. https://arxiv.org/abs/1809.08887
- ★ **BIRD** — Li et al., 2023. Gerçekçi/kirli veritabanlarıyla kıyas; JOIN zorluğu bulgumuzun (B14) kaynağı. https://arxiv.org/abs/2305.03111 · site: https://bird-bench.github.io/
- **Spider 2.0** — 2024. Kurumsal ölçekte (bin+ kolon) neden hâlâ zor olduğunun kanıtı; yatırımcı sorusu "neden herkes yapamıyor?"un cevabı. https://arxiv.org/abs/2411.07763
- ★ **Test-suite / execution eval** — Zhong et al., 2020. "Çalışan ama yanlış SQL" (B7) nasıl ölçülür; evaluate.py'ımızın teorisi. https://arxiv.org/abs/2010.02840
- **Exploring the Landscape of Text-to-SQL with LLMs** — 2025 sörveyi; alanın güncel haritası. https://arxiv.org/pdf/2505.23838

## 2. Türkçe Text-to-SQL (B3 bulgusunun güncel hâli)

- ★ **TURSpider** — Spider'ın Türkçe insan çevirisi + LLM çalışması (IEEE). Eğitim setimizin birinci adayı. https://ieeexplore.ieee.org/document/10753591/
- ★ **BIRDTurk** — BIRD'ün Türkçe uyarlaması (Şubat 2026). Türkçede tutarlı performans düşüşü bulgusu — bizim fine-tune gerekçemizin hakemli kanıtı. https://arxiv.org/abs/2602.03633
- **TUR2SQL** — Çapraz alanlı Türkçe set. https://www.researchgate.net/publication/374959367
- **Düşük kaynaklı dillerde Text-to-SQL iyileştirme** — DergiPark, Türkçe bağlam. https://dergipark.org.tr/en/pub/bitlisfen/article/1561298

## 3. Prompt / RAG yaklaşımları (ADR-3'ün dayanağı)

- ★ **RAG** — Lewis et al., 2020. Retrieval-augmented generation'ın kurucu makalesi. https://arxiv.org/abs/2005.11401
- ★ **DIN-SQL** — 2023. Soruyu alt görevlere bölme (şema bağlama → üretim → öz düzeltme); pipeline'ımızın akıl haritası. https://arxiv.org/abs/2304.11015
- **DAIL-SQL** — 2023. Prompt mühendisliği seçeneklerinin sistematik kıyası; "örnek seçimi" nasıl yapılır. https://arxiv.org/abs/2308.15363
- **MCS-SQL** — çoklu prompt + seçim; güven skoru fikrimizin (G-03) akrabası. https://arxiv.org/pdf/2405.07467
- **Sentetik veri üretimi (zayıf+güçlü LLM)** — training/generate_dataset.py'ımızın yöntemsel temeli. https://arxiv.org/pdf/2408.03256

## 4. Fine-tuning (ADR-1/2'nin dayanağı)

- ★ **LoRA** — Hu et al., 2021. Adaptör mantığı. https://arxiv.org/abs/2106.09685
- ★ **QLoRA** — Dettmers et al., 2023. 4-bit + LoRA; 6GB VRAM planımızın var olma sebebi. https://arxiv.org/abs/2305.14314
- **Attention Is All You Need** — 2017. Transformer'ı bir kez gerçekten anlamak için. https://arxiv.org/abs/1706.03762
- **Llama 3 model raporu** — taban modelimizin yetenek/limit haritası. https://arxiv.org/abs/2407.21783

## 5. Türkçe NLP

- ★ **Zemberek-NLP** — Türkçe morfoloji aracı (G-09'un olası motoru). https://github.com/ahmetaa/zemberek-nlp
- **TURNA** — Türkçe encoder-decoder LM çalışması; Türkçe modelleme zorluklarına giriş. https://arxiv.org/abs/2401.14373

## 6. Analist tarafı (ürünün "neden"i)

- **Kendall & Kendall, Systems Analysis and Design** — zaten şablonumuzun omurgası; Böl. 2 (bilgi toplama) ve Böl. 13 (UAT) tekrar okunmalı.
- **BABOK v3** özet bölümleri — gereksinim sınıflandırması ve izlenebilirlik (G-tablosu pratiğinin sektör standardı).
- **Nielsen, 10 Usability Heuristics** — Böl. 10 denetim listemizin kaynağı. https://www.nngroup.com/articles/ten-usability-heuristics/

## Okuma planı önerisi (4 hafta)

| Hafta | Konu | Çıktı |
|---|---|---|
| 1 | Spider + BIRD + test-suite eval | evaluate.py'ı bilerek savunabilmek |
| 2 | TURSpider + BIRDTurk + TUR2SQL | Veri seti stratejisini revize etmek (B3 güncellemesi) |
| 3 | LoRA + QLoRA + DIN-SQL | train_qlora.py hiperparametrelerini anlayarak seçmek |
| 4 | RAG + DAIL-SQL + Zemberek | RAG bağlam stratejisini (tablo başına belge) iyileştirmek |
