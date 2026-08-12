# Ollama Pilot V1

## Scope

Qwen 3.5 4B and 9B were tested locally against the existing human-reviewed pilot of 18 reviews: six each from Hades II, Stardew Valley, and Cyberpunk 2077. Each game used the production full-analysis schema, exact scope/evidence validation, a 16,384-token context, thinking disabled, temperature zero, and at most one malformed-output retry. No embeddings or cloud processing were used.

## Environment

- Ollama 0.32.8 on Windows
- 15.4 GB visible system memory
- No NVIDIA runtime detected by `nvidia-smi`
- CPU-only inference reported by Ollama
- Qwen 3.5 4B: 3.6 GB loaded with 16,384-token context
- Qwen 3.5 9B: 6.6 GB loaded with 16,384-token context

## Results

| Model | Valid games | Hades II | Stardew Valley | Cyberpunk 2077 | Conclusion |
| --- | ---: | --- | --- | --- | --- |
| Qwen 3.5 4B | 0/3 | Incomplete scope, 147.6 s | Unknown Opinion Point reference, 111.5 s | Incomplete scope, 164.7 s | Does not satisfy the current full-analysis contract |
| Qwen 3.5 9B | 0 completed | Stopped after about 20 minutes | Not run | Not run | Impractical for this contract on this CPU-only machine |

The 4B failures occurred after the adapter requested the full 16,384-token context, so the original 4,096-token default was not the sole cause. Because no 4B response passed the trust boundary, extraction precision, recall, sentiment accuracy, and Theme quality could not be scored honestly. The 9B result is a performance finding only, not an accuracy finding.

## Decision

Neither local candidate should be presented as a reliable default for full analysis on this machine. Keep Ollama available for explicit experimentation with installed models, but retain Codex CLI as the first supported path. A future local experiment should use the already-designed bounded Opinion Point extraction pipeline instead of asking a small model for the complete extraction, grouping, summary, opposition, and classification result in one response.

This pilot does not resume or replace the deferred 15,000-review stability experiment and does not establish production-quality thresholds.
