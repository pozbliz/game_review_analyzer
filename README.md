# Game Review Analyzer

Game Review Analyzer is a local web application under active development that turns large sets of Steam reviews into evidence-backed positive and negative game-design themes. It also captures a comprehensive Steam store snapshot so a developer can understand the game, its features, and the review evidence in one report.

The local application shell, keyed Steam catalog synchronization, local-first name search with a replaceable public fallback, direct-AppID preview, rich regional storefront snapshots, durable Quick and Full review imports, delta refresh, explicit reconciliation, fixture-backed report exploration, immutable history, and safe report export/re-import are complete. Imports retain append-only review revisions, survive backend or browser restarts, and expose progress, cancellation, retry, and checkpoints. Reconciliation records reviews absent from a complete scan without deleting historical evidence. Versioned analysis contracts, bounded Opinion Point extraction, privacy-minimized Manual Codex package validation, deterministic Theme metrics, and Report Version 2.0 persistence with owned metadata snapshots are available. Reports show ranked design and Technical Themes, linked mixed reception, exact scope and provenance, representative evidence, full local review context, grouped Steam facts and media, newest-first history, and refresh recovery. Versioned JSON, CSV, and standalone HTML downloads omit reviewer identity and full review text by default; JSON re-import requires every exact local evidence revision. Storage diagnostics and exact-confirmation deletion controls cover reports, inactive incomplete jobs, and complete Game Datasets. Connected-browser acceptance and real-world reliability calibration remain deferred.

## Current implementation status

Slices 1–8, 11, and 12 are implemented, including a successful authenticated Codex CLI report run. The one-review live report retained six exact Opinion Points, classified the review as mixed, and correctly omitted Themes that lacked two-review support. The complete structured contract has high fixed overhead—15,744 input tokens even for that tiny scope—so quota optimization remains open. Slice 9 is active: Ollama 0.32.8 plus Qwen 3.5 4B and 9B are installed, and the app can explicitly run either through the durable local report flow. The human-reviewed pilot found 4B invalid on all three games and 9B impractically slow on this CPU-only machine, so neither is a reliable default for full analysis here. Hosted API and Claude Code adapters remain later choices. Slice 10 remains blocked by deferred cohort-size calibration. Source and packaged release work remains in Slices 13 and 14. The exact continuation checkpoint and every open action are maintained in `TASKS.md`.

## Product goals

- Search Steam by game name or enter an AppID directly.
- Collect a configurable recent sample or all eligible English reviews.
- Refresh stored datasets with new and updated reviews without redownloading everything.
- Show up to 10 reliable positive and 10 reliable negative design themes with counts, percentages, excerpts, and full evidence drill-down.
- Preserve mixed reception, playtime, helpfulness, review scope, and historical report versions.
- Include tags, regional price, descriptions, features, platforms, DLC/storefront information, screenshots, and opt-in Steam-hosted trailers when available.
- Present evidence without generating design recommendations.

## Planned operation

The MVP runs locally in a browser and stores data on the user's machine. Source code will be public at [pozbliz/game_review_analyzer](https://github.com/pozbliz/game_review_analyzer) under the MIT license. Windows is the first packaged-release target; source-based use should remain cross-platform where dependencies permit.

GitHub hosts the source and release downloads. GitHub Pages may later host documentation or a static demonstration, but it cannot run the Python backend required by the analyzer.

## Planned stack

- React, TypeScript, and Vite
- FastAPI and Python
- SQLite
- Provider-neutral structured AI analysis

Initial analysis options are automated Codex CLI, manual Codex package export/import, Ollama with a user-installed model, and later OpenAI, Anthropic Claude, and Google Gemini API adapters. Claude Code may be added as a separate CLI adapter. The application will not download AI models. API credentials, when API adapters are added, will be session-only by default with optional operating-system credential-vault and environment-variable support.

Embeddings are not required in the MVP. They remain a future enhancement for semantic clustering.

## Documentation

- `docs/evaluation/cloud-provider-selection.md` — provisional first-provider recommendation, evidence, and current prices
- `docs/evaluation/stability-v1.md` — deferred full-corpus stability experiment and retained restart point
- `DESIGN.md` — authoritative product behavior and architecture
- `docs/specifications/DOMAIN_GLOSSARY.md` — canonical domain terminology
- `docs/specifications/ANALYSIS_EVALUATION.md` — analysis-quality corpus format and scoring rules
- `docs/evaluation/pilot-v1.md` — first human-adjudicated evaluation results and limits
- `docs/evaluation/ollama-pilot-v1.md` — local Qwen 3.5 4B/9B contract and performance results
- `docs/steam-data-policy.md` — validated Steam Web API and best-effort storefront obligations
- `PLAN.md` — phased implementation sequence
- `TASKS.md` — active work and unresolved issues
- `DECISION_LOG.md` — design-change history

## Local development

Install Python 3.12, [uv](https://docs.astral.sh/uv/), and Node.js 20.19 or newer. Restore and verify each toolchain from its committed lockfile:

```powershell
cd backend
uv sync --locked --extra dev
uv run pytest

cd ../frontend
npm ci
npm test
npm run build
```

For development, run `uv run uvicorn game_review_analyzer.interfaces.http.app:app --reload` from `backend/` and `npm run dev` from `frontend/`. For the production delivery path, build the frontend first and run only the backend; FastAPI serves `frontend/dist/` along with the API.

The local human evaluation tool is available at `frontend/public/review-labeler.html` directly or `/review-labeler.html` through the running application. It loads candidate JSON locally and exports reviewed JSON without transmitting review data.

The backend uses a packaged `src/game_review_analyzer/` layout with domain, application, interface, infrastructure, and shared ownership boundaries. The frontend shell lives under `frontend/src/app/`, shared styling under `frontend/src/styles/`, and integration tests under `frontend/tests/`.

## Known constraints

- Rich Steam storefront metadata relies partly on best-effort public storefront sources and may be incomplete.
- Keyed catalog synchronization requires a standard Steam Web API key supplied only to the local backend. Store country is configured with `GAME_REVIEW_ANALYZER_STEAM_COUNTRY`; returned currency and formatted prices are shown without conversion.
- A recent-review sample represents that time-biased sample, not all historical opinion.
- Full imports and cloud-provider analysis can be slow or costly for popular games.
- The application data directory cannot yet be relocated. Report exports are not complete database backups.
- AI grouping is fallible, so reports must retain inspectable evidence and deterministic metrics.
