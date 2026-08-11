# Headline Theme Stability Evaluation V1

## Local corpus

The gitignored `evaluation-data/stability_raw_v1.json` contains the latest 5,000 eligible English reviews returned in Steam recent-source order for each approved game. Recommendation outcomes were not balanced or resampled.

| Game | Reviews | Recommended | Not Recommended |
| --- | ---: | ---: | ---: |
| Hades II | 5,000 | 4,784 (95.7%) | 216 (4.3%) |
| Stardew Valley | 5,000 | 4,906 (98.1%) | 94 (1.9%) |
| Cyberpunk 2077 | 5,000 | 4,761 (95.2%) | 239 (4.8%) |

All 15,000 review identifiers are unique within their game corpus. The local file is 10,951,627 bytes.

## Provider configuration

The user approved `gpt-5.6-luna` with medium reasoning through the local Codex CLI. Each game has three privacy-minimized inputs containing only its identity, run metadata, review revision IDs, and review text. The contiguous, interleaved, and SHA-256-hashed strategies each contain all 5,000 reviews in 20 deterministic 250-review batches.

The synthetic conformance run reproduced both expected Themes with exact evidence. The first full Stardew Valley contiguous discovery output failed case-sensitive excerpt validation. A second discovery output fixed exact excerpts but omitted one representative review from its Theme support membership. A narrow third provider attempt repaired that relationship and passed strict validation with 22 Themes. Both rejected outputs remain local for audit.

The remaining eight full-corpus runs have not started. A provider output is never silently repaired or scored after validation failure.
