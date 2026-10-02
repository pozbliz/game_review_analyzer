# Source installation and operation

## Requirements

- Windows with Python 3.12, `uv`, and Node.js 20.19 or newer
- Optional: a standard Steam Web API key for keyed catalog synchronization
- Analysis path: authenticated Codex CLI

The application never downloads an AI model and does not accept cloud-provider API keys yet.

## Install and verify

From the repository root:

```powershell
cd backend
uv sync --locked --extra dev
uv run pytest

cd ../frontend
npm ci
npm test
npm run build
```

## Normal operation

From the repository root, build the frontend after each frontend change:

```powershell
cd frontend
npm run build
```

Run the compiled frontend and API from `backend/`:

```powershell
cd ../backend
uv run uvicorn game_review_analyzer.interfaces.http.app:app
```

Open `http://127.0.0.1:8000`. Port `5173` is not used for normal operation.

The database schema is initialized or migrated automatically at backend startup.

Opening the game-page review-language disclosure requests current summary totals for Steam's supported API languages. The application does not store these totals.

## Development operation

When editing backend code, run the backend from `backend/` with reload enabled:

```powershell
uv run uvicorn game_review_analyzer.interfaces.http.app:app --reload
```

Run `npm run dev` from `frontend/` in another terminal. Open `http://localhost:5173`; Vite sends `/api` requests to `http://127.0.0.1:8000`.

Rebuild the frontend before returning to normal operation.

## Configuration

The application reads process environment variables; it does not automatically load `.env` files. `.env.example` lists every supported setting. In PowerShell, set a value for the current process before starting the backend:

```powershell
$env:GAME_REVIEW_ANALYZER_STEAM_COUNTRY = "JP"
$env:GAME_REVIEW_ANALYZER_STEAM_WEB_API_KEY = "your-key"
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `GAME_REVIEW_ANALYZER_ENV` | `development` | Environment label exposed by the non-secret config endpoint |
| `GAME_REVIEW_ANALYZER_DATABASE` | `data/game-review-analyzer.sqlite3` | Local SQLite database path, relative to the backend working directory unless absolute |
| `GAME_REVIEW_ANALYZER_FRONTEND_DIST` | `../frontend/dist` | Compiled frontend directory served by FastAPI |
| `GAME_REVIEW_ANALYZER_STEAM_COUNTRY` | `US` | Two-letter Steam store country used for regional storefront data |
| `GAME_REVIEW_ANALYZER_STEAM_WEB_API_KEY` | unset | Optional Steam key used only by the local backend |

Do not commit real keys. The public configuration API reveals only whether a Steam key is configured.

## Analysis

### Codex CLI

Install and authenticate Codex CLI outside the application. The app checks readiness but never reads or stores Codex credentials. Each run is explicit, uses the configured pinned model, sends the selected review text to external cloud processing, and records measured token usage when Codex exposes it. Subscription quota and dollar cost remain unknown.

The backend console emits redacted JSON timing events for every Codex attempt and analysis stage. `provider.attempt_failed` includes the safe failure code and whether the app retries. These events include counts and byte sizes, but exclude prompts, review text, model output, credentials, and process stderr.

## Local data and privacy

- Steam metadata, review text, Review Revisions, jobs, and reports are stored in the configured SQLite database.
- The app retrieves public Steam data and no private Steam-user data.
- Reviewer identity is omitted from analysis requests.
- Report pages and saved-report cards omit analysis engine names.
- Codex CLI sends selected review text to external cloud processing.
- Deleting a report also deletes its completed run and checkpoints.
- Deleting an inactive import job or complete Game Dataset requires exact typed confirmation. Game Dataset deletion removes all owned local data.

Back up the SQLite database before destructive maintenance or updates.

## Update and recovery

1. Stop the backend and copy the SQLite database to a safe location.
2. Pull the desired source revision.
3. Run `uv sync --locked --extra dev` in `backend/` and `npm ci` plus `npm run build` in `frontend/`.
4. Run both test suites.
5. Start FastAPI; migrations run automatically.

The Version 3-only migration deletes legacy Version 2 reports, runs, and Opinion Point caches. Back up the database before updating from a Version 2 build.

Interrupted imports and analyses retain durable state. Extend and Replace resume their owned Steam refresh, exact reserved scope, and valid provider checkpoints. Starting Extend opens the analysis progress screen. Steam refresh shows progress toward its 5,000-review scan limit.

Use the visible retry or cancellation controls rather than editing SQLite. A failed or cancelled report update leaves the current report available. The interface shows a safe failure code and recovery instruction without storing provider output or review text.

Run the storage integrity check from the Local data section when corruption is suspected. If startup fails, restore the database backup and the previous source revision together.

## Current release limits

- Windows is the first source-release validation target.
- The data directory can be relocated only through `GAME_REVIEW_ANALYZER_DATABASE`; there is no in-app relocation workflow.
- Real-world Theme reliability thresholds remain provisional pending the deferred bulk calibration gate.
- Connected-browser and human assistive-technology acceptance must be completed before release approval.
- Hosted OpenAI, Anthropic, and Google API adapters and Claude Code are not implemented.
