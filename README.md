# Game Review Analyzer

Game Review Analyzer is a planned local web application that turns large sets of Steam reviews into evidence-backed positive and negative game-design themes. It also captures a comprehensive Steam store snapshot so a developer can understand the game, its features, and the review evidence in one report.

The local application shell and direct-AppID metadata preview are complete. The approved Catalog → Split → Timeline → Research workflow is being built incrementally; Steam review retrieval and report generation are not implemented yet.

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

Initial analysis options are Ollama with a user-installed model, OpenAI API, Anthropic Claude API, Google Gemini API, and manual Codex package export/import. The application will not download AI models. API credentials will be session-only by default, with optional operating-system credential-vault and environment-variable support.

Embeddings are not required in the MVP. They remain a future enhancement for semantic clustering.

## Documentation

- `DESIGN.md` — authoritative product behavior and architecture
- `docs/specifications/DOMAIN_GLOSSARY.md` — canonical domain terminology
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

The backend uses a packaged `src/game_review_analyzer/` layout with domain, application, interface, infrastructure, and shared ownership boundaries. The frontend shell lives under `frontend/src/app/`, shared styling under `frontend/src/styles/`, and integration tests under `frontend/tests/`.

## Known constraints

- Rich Steam storefront metadata relies partly on best-effort public storefront sources and may be incomplete.
- A recent-review sample represents that time-biased sample, not all historical opinion.
- Full imports and cloud-provider analysis can be slow or costly for popular games.
- AI grouping is fallible, so reports must retain inspectable evidence and deterministic metrics.
