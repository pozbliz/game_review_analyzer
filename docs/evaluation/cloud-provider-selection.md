# First Cloud Provider Evaluation

**Status:** Codex CLI first path approved

**Reviewed:** 2026-08-12

## Decision criteria

The first automated adapter must support schema-constrained output, preserve the requested and returned model identifiers, operate directly on review text without embeddings, and remain subject to the application's exact-evidence validator. Provider documentation establishes capability and list pricing; only a run against this project's labeled corpus can establish analysis quality.

| Candidate | Project-specific quality evidence | Structured output and model identification | Standard text price per 1M tokens | Assessment |
| --- | --- | --- | ---: | --- |
| OpenAI `gpt-5.6-luna`, medium reasoning | The existing Codex CLI experiment passed synthetic conformance and produced valid real-corpus results, but also produced non-exact excerpts and incomplete evidence that strict validation rejected. This is indicative rather than a direct API benchmark. | Structured outputs are supported. The request model and API-returned model value can be retained in provenance. | $0.20 input / $1.20 output | Best first adapter: lowest listed standard price and the only candidate with project-specific evidence. |
| Google `gemini-3.5-flash-lite` | Not yet tested on the project corpus. | Structured outputs are supported using a documented JSON Schema subset. The stable model code is documented. | $0.30 input / $2.50 output | Strong second candidate; quality and exact-evidence behavior remain unknown. |
| Anthropic `claude-haiku-4-5-20251001` | Not yet tested on the project corpus. | Structured outputs are generally available for Haiku 4.5. The dated API ID is a pinned snapshot. | $1.00 input / $5.00 output | Strong schema/versioning fit, but materially more expensive and untested here. |

Prices are list prices checked on 2026-08-11 and can change. The runtime estimator must display its pricing date and include reasoning/output tokens and retry risk. Batch discounts are excluded because Slice 8 requires an interactive report path.

## Approved first path

Automate the user's separately installed and authenticated Codex CLI first with `gpt-5.6-luna` and medium reasoning. Run non-interactively with an ephemeral session, read-only sandbox, isolated temporary directory, and explicit output schema. Send only the existing privacy-minimized analysis request, validate every result through the existing contract and exact-evidence checks, record requested model and measured usage when available, and never fall back to another provider or model.

Codex subscription quota cannot be converted into a trustworthy dollar estimate, so the application must disclose quota use and uncertainty. This approval does not approve production-quality claims. After implementation, Ollama is the next evaluation path, starting with installed Qwen 3.5 9B and 4B models against the same labeled pilot; hosted APIs remain optional later adapters.

## Sources

- [OpenAI GPT-5.6 Luna model](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Gemini 3.5 Flash-Lite model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Claude models overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
