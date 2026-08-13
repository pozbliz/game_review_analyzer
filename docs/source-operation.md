# Source installation and operation

## Requirements

- Windows with Python 3.12, `uv`, and Node.js 20.19 or newer
- Optional: a standard Steam Web API key for keyed catalog synchronization
- Optional analysis path: authenticated Codex CLI or a separately installed Ollama runtime and model

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

For the production delivery path, run the compiled frontend through FastAPI:

```powershell
cd ../backend
uv run uvicorn game_review_analyzer.interfaces.http.app:app
```

Open `http://127.0.0.1:8000`. The database schema is initialized or migrated automatically at startup.

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

## Analysis providers

### Codex CLI

Install and authenticate Codex CLI outside the application. The app checks readiness but never reads or stores Codex credentials. Each run is explicit, uses the configured pinned model, sends the selected review text to external cloud processing, and records measured token usage when Codex exposes it. Subscription quota and dollar cost remain unknown.

### Ollama

Install Ollama and a compatible model yourself. The app lists already-installed models and runs only the model selected by the user. It never pulls a model or silently falls back. Local Qwen 3.5 4B and 9B are available for explicit experimentation but are not presented as reliable full-analysis defaults on the evaluated CPU-only machine.

### Manual Codex

Export the privacy-minimized package, process it through Codex, then import the structured result. Imports are rejected unless identifiers, exact excerpts, scope, and schema match the local evidence.

## Local data and privacy

- Steam metadata, review text, Review Revisions, jobs, and reports are stored in the configured SQLite database.
- The app retrieves public Steam data and no private Steam-user data.
- Reviewer identity is omitted from analysis packages and report exports.
- Default JSON, CSV, and HTML exports omit full review text. Enabling full text produces a privacy-warned artifact.
- Codex CLI and Manual Codex send selected review text to external cloud processing. Ollama keeps analysis on the local device.
- Deleting a Report Version, inactive incomplete job, or complete Game Dataset requires exact typed confirmation. Game Dataset deletion also removes its owned local reviews, jobs, and reports.

Back up the SQLite database before destructive maintenance or updates. Report exports are not complete database backups.

## Update and recovery

1. Stop the backend and copy the SQLite database to a safe location.
2. Pull the desired source revision.
3. Run `uv sync --locked --extra dev` in `backend/` and `npm ci` plus `npm run build` in `frontend/`.
4. Run both test suites.
5. Start FastAPI; migrations run automatically and preserve existing data.

Interrupted imports and analyses retain durable state. Use the visible retry or cancellation controls rather than editing SQLite. Run the storage integrity check from the Local data section when corruption is suspected. If startup fails, restore the database backup and the previous source revision together.

## Current release limits

- Windows is the first source-release validation target.
- The data directory can be relocated only through `GAME_REVIEW_ANALYZER_DATABASE`; there is no in-app relocation workflow.
- Real-world Theme reliability thresholds remain provisional pending the deferred bulk calibration gate.
- Connected-browser and human assistive-technology acceptance must be completed before release approval.
- Hosted OpenAI, Anthropic, and Google API adapters and Claude Code are not implemented.
