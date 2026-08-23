# Ölçüm Günlüğü

Her koşum bir satır. Bu dosyaya asla üzerine yazılmaz.
Karşılaştırma yalnız aynı test seti ve aynı model için anlamlıdır.

| Tarih | Model | Acc | Sessiz yanlış | p50 | p95 | temp | seed | num_ctx | değer örn. | commit | Rapor |
|-------|-------|-----|---------------|-----|-----|------|------|---------|-----------|--------|-------|
| 2026-08-16 | `qwen2.5-coder:7b-instruct` | **%62** (63/101) | 36 (%95) | 14.4 | 21.2 | 0.0 | 42 | 4096 | açık | `ffe5db3` | accuracy-2026-08-16-qwen2-5-coder-7b-instruct-01.md |
| 2026-08-22 | `qwen2.5-coder:7b-instruct` | **%56** (57/101) | 42 (%95) | 21.7 | 32.8 | 0.0 | 42 | 8192 | açık | `ffe5db3` | accuracy-2026-08-22-qwen2-5-coder-7b-instruct-01.md |
| 2026-08-22 | `gemini-3.7-flash` | **%71** (72/101) | 29 (%100) | 2.3 | 3.8 | 0.0 | 42 | 8192 | açık | `884f8d9 (+islenmemis degisiklikler)` | accuracy-2026-08-22-gemini-3-7-flash-01.md |
| 2026-08-23 | `gemini-3.7-flash` | **%70** (71/101) | 30 (%100) | 2.3 | 4.8 | 0.0 | 42 | 8192 | açık | `259f50a (+islenmemis degisiklikler)` | accuracy-2026-08-23-gemini-3-7-flash-01.md |
