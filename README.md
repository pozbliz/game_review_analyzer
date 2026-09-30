# Game Review Analyzer

Game Review Analyzer is a local web application under active development.

It turns large sets of Steam reviews into the main positive and negative player-opinion Themes.

The current code implements catalog synchronization, game preview, rich Steam metadata, durable review imports, refresh, reconciliation, and local storage controls.

Jobs survive backend and browser restarts. They expose progress, cancellation, retry, and checkpoints.

The current code also implements evidence-heavy Version 2 reports, Opinion Points, categories, mixed reception, Evidence Filters, and immutable history.

Existing HTML, CSV, and JSON exports omit reviewer identity and full review text by default.

Connected-browser acceptance and real-world reliability calibration remain deferred.

Steam review imports wait two seconds between pages and honor rate-limit delays while preserving their latest checkpoint.

The proposed target replaces report history with one progressive Main Report and one separate 50-review Test Report per game.

It removes Opinion Points, excerpts, evidence browsing, categories, filters, mixed-reception links, and Version 2 compatibility.

## Current implementation status

Slices 1–8 and 10–12 implement the earlier evidence-heavy report system.

The current code includes authenticated Codex CLI analysis, Ollama, Evidence Filters, immutable history, and exports.

The Version 3 Test Report and first Main Report are implemented.

The Test Report analyzes 25 oldest and 25 newest reviews in one Codex call.

The shared `Create report` action supports the 50-review Test Report and 1,000-review Main Report scopes.

Each Test Report Theme can reveal its matching local reviews. Evidence is sorted by helpful votes and loaded only when opened.

The current Test and Main Reports are saved separately from Version 2 reports. Slice 18 is the next implementation step.

Current application data was reset before this redesign. The gitignored evaluation corpus remains available.

## Product goals

- Search Steam by game name or enter an AppID directly.
- Complete a Full Import of eligible English reviews before analysis.
- Refresh stored datasets before extending or replacing the Main Report.
- Grow one Main Report in 1,000-review increments split between oldest and newest unseen reviews.
- Show up to five positive and five negative Themes that reach 5% support in either cohort.
- Keep one separate 50-review Test Report for provider testing.
- Include tags, regional price, descriptions, features, platforms, DLC/storefront information, screenshots, and opt-in Steam-hosted trailers when available.
- Export aggregated Theme metrics without review text or reviewer identity.
- Avoid design recommendations.

## Planned operation

The MVP runs locally in a browser and stores data on the user's machine.

Source code will be public at [pozbliz/game_review_analyzer](https://github.com/pozbliz/game_review_analyzer) under the MIT license.

Windows is the first packaged-release target. Source-based use should remain cross-platform where dependencies permit.

GitHub hosts the source and release downloads.

GitHub Pages may later host documentation or a static demonstration. It cannot run the required Python backend.

## Planned stack

- React, TypeScript, and Vite
- FastAPI and Python
- SQLite
- Versioned structured AI analysis

Version 3 initially supports automated Codex CLI with one application-supported model and low reasoning.

Additional providers and model controls are deferred. The application will not download AI models.

Embeddings are not required in the MVP. They remain a future enhancement for semantic clustering.

## Documentation

- `docs/evaluation/cloud-provider-selection.md` — provisional first-provider recommendation, evidence, and current prices
- `docs/evaluation/stability-v1.md` — deferred full-corpus stability experiment and retained restart point
- `DESIGN.md` — authoritative product behavior and architecture
- `CONTEXT.md` — canonical domain terminology
- `docs/specifications/ANALYSIS_EVALUATION.md` — analysis-quality corpus format and scoring rules
- `docs/evaluation/pilot-v1.md` — first human-adjudicated evaluation results and limits
- `docs/evaluation/ollama-pilot-v1.md` — local Qwen 3.5 4B/9B contract and performance results
- `docs/steam-data-policy.md` — validated Steam Web API and best-effort storefront obligations
- `docs/source-operation.md` — source installation, configuration, providers, privacy, updates, and recovery
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

### Start the app

Start the backend in one PowerShell terminal:

```powershell
cd backend
uv run uvicorn game_review_analyzer.interfaces.http.app:app --reload
```

Start the frontend in a second PowerShell terminal:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173> in a browser.

For production, build the frontend and run only the backend.

FastAPI serves `frontend/dist/` with the API.

Analysis runs emit redacted JSON timing events through the `game_review_analyzer` logger.

Events time preparation, provider attempts, subprocesses, cache writes, consolidation, and report persistence.

The backend writes these events to `backend/data/game-review-analyzer.log` and rotates three 1 MB backups.

HTTP failures, import failures, analysis failures, and reported browser runtime errors include safe codes and identifiers when available.

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export HTTP and analysis traces. Telemetry excludes review text, prompts, and model output.

The local human evaluation tool is available at `frontend/public/review-labeler.html` or `/review-labeler.html`.

It loads candidate JSON locally and exports reviewed JSON without transmitting review data.

The backend uses a packaged `src/game_review_analyzer/` layout with ownership-based modules.

The frontend shell lives under `frontend/src/app/`. Shared styles use `frontend/src/styles/`, and integration tests use `frontend/tests/`.

## Known constraints

- Rich Steam storefront metadata relies partly on best-effort public storefront sources and may be incomplete.
- Keyed catalog synchronization requires a standard Steam Web API key supplied only to the local backend. Store country is configured with `GAME_REVIEW_ANALYZER_STEAM_COUNTRY`; returned currency and formatted prices are shown without conversion.
- Main and Test Reports require a completed Full Import.
- The Main Report starts with 500 oldest and 500 newest reviews, then grows through explicit 1,000-review extensions.
- A separate Test Report uses 25 oldest and 25 newest reviews without refreshing Steam.
- Full imports and Codex CLI analysis can be slow or quota-intensive for popular games.
- The application data path can be changed only through an environment variable; there is no in-app relocation workflow. Report exports are not complete database backups.
- Reports expose aggregate Theme memberships and deterministic metrics without per-review evidence.
- Existing code still implements the prior Version 2 behavior until the approved redesign is planned and built.
