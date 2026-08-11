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

Three independent Stardew Valley outputs are valid: contiguous produced 22 Themes, interleaved 17, and hashed 13. An earlier interleaved output was rejected from stability scoring because its workspace could see the contiguous result; subsequent runs use separate filesystem roots containing only their own input and schema.

Hades II contiguous exhausted the three-attempt limit for whole-result generation. Discovery contained two case-normalized excerpts; repair attempt two left one unchanged; the final repair fixed that excerpt but regenerated unrelated evidence and introduced a new non-exact excerpt. The user then approved a new evidence-only repair contract that can replace excerpts only for explicitly rejected Theme keys. Its first output repaired `polished_sequel_and_expanded_content` without changing support membership or any unrelated Theme field, and the complete 16-Theme result passed strict validation. A provider output is never silently repaired or scored after validation failure.

The first Hades II interleaved attempt returned zero Themes, exposing that the initial schema had only a maximum Theme count. The result was rejected and preserved; the shared contract now requires 1–60 Themes before further runs.
