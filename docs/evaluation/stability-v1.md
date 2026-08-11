# Headline Theme Stability Evaluation V1

## Local corpus

The gitignored `evaluation-data/stability_raw_v1.json` contains the latest 5,000 eligible English reviews returned in Steam recent-source order for each approved game. Recommendation outcomes were not balanced or resampled.

| Game | Reviews | Recommended | Not Recommended |
| --- | ---: | ---: | ---: |
| Hades II | 5,000 | 4,784 (95.7%) | 216 (4.3%) |
| Stardew Valley | 5,000 | 4,906 (98.1%) | 94 (1.9%) |
| Cyberpunk 2077 | 5,000 | 4,761 (95.2%) | 239 (4.8%) |

All 15,000 review identifiers are unique within their game corpus. The local file is 10,951,627 bytes.

## Provider-run status

No provider run has started. The required experiment will transmit public review text to the selected provider and consume provider quota. The local Codex CLI supports non-interactive structured output, but external processing requires explicit human approval and a pinned model identifier before the three-run minimum begins.
