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

On Windows, start the compiled frontend and API from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-app.ps1
```

Open `http://127.0.0.1:8000`. Port `5173` is not used for normal operation.

Run the launcher from a normal terminal with outbound network access. For agent launches, use an execution environment that permits Steam requests. Detaching the server does not remove inherited sandbox restrictions.

Verify startup from the same terminal:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/games/search?q=hades'
```

Use the selected port when it differs from 8000. Health must return `status: ok`, and search must return game results. If results come from the local catalog, verify outbound Steam access separately:

```powershell
Invoke-RestMethod -Uri 'https://store.steampowered.com/api/storesearch/?term=hades&l=english&cc=US'
```

A healthy backend can still fail Steam requests. HTTP 503 with `steam_search_unavailable` and an underlying Windows socket error `10013` indicate blocked socket access. Check the launch environment before changing application code. Stop the owned instance with the documented stop command, then restart from an environment with outbound network access. Preserve its port and database selection. Repeat the health and search checks before reporting recovery.

The launcher uses the installed backend virtual environment. Restore dependencies before the first launch. Windows `Start-Process` keeps the background process independent of the launching shell. [Microsoft documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process). The PowerShell execution-policy argument applies only to this invocation.

For a custom port and database, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-app.ps1 -Port 8001 -Database .\backend\data\workflow-verification-2026-10-03\verification.sqlite3
```

An explicit `-Database` argument overrides `GAME_REVIEW_ANALYZER_DATABASE` and resolves relative paths from the caller's working directory. Without that argument, the launcher honors the environment setting; relative environment paths resolve under `backend/`. If neither is set, the database is `backend/data/game-review-analyzer.sqlite3` under this repository.

Use the same database when stopping supervision:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-app.ps1 -Action stop -Port 8001 -Database .\backend\data\workflow-verification-2026-10-03\verification.sqlite3
```

The stop command disables restarts before terminating the owned backend process tree. Saved checkpoints remain available on the next start. Stop an existing foreground backend before switching it to the launcher.

An unexpected backend exit triggers up to three restart attempts, with delays of one, two, and four seconds. Startup failures, an occupied port, and duplicate database ownership stop supervision instead of entering a restart loop. After retries are exhausted, correct the logged cause and run the start command again.

Lifecycle diagnostics are stored at `<database>.server.log`, with three rotating backups of up to 1 MB each. They record process IDs, exit codes, restart attempts, and intentional stops without provider output or review text. Exit codes `2`, `3`, and `4` indicate port binding, database ownership, and startup failures respectively. Safe startup stages and exception types are stored in `<database>.server-startup.log`, with the same rotation limits. The application event log remains at the database path with its extension replaced by `.log`.

On Windows, each backend attempt uses a native Job object. Closing that Job removes its remaining subprocesses before another attempt starts. This prevents an abandoned provider process from overlapping checkpoint recovery. [Microsoft documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

Every backend instance holds an operating-system lock for its database before migrations or recovery. Process exit releases the lock automatically. A second backend cannot recover the same database on another port. The supervised backend binds its port before application startup.

Supervision covers backend exits and terminal closure. It does not install a Windows service or start automatically after reboot. If the supervisor itself stops, start the launcher again. Repeated configuration failures require correction.

For foreground operation on another platform, keep the terminal open and run from `backend/`:

```shell
uv run uvicorn game_review_analyzer.interfaces.http.app:app
```

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

Choose a Main Report scope of 1,000, 5,000, or 10,000 English reviews under `Analysis scope` before selecting `Create Report`. Each scope splits equally between oldest and newest reviews without overlap. If fewer usable reviews exist, the report analyzes all of them. The selected size applies to replacement as well as initial creation and remains saved through retries and backend restarts. Extensions still add up to 1,000 unseen reviews. Larger scopes require more provider calls, time, and subscription quota.

### Codex CLI

Install and authenticate Codex CLI outside the application. The app checks readiness but never reads or stores Codex credentials. Each run is explicit, uses the configured pinned model, sends the selected review text to external cloud processing, and records measured token usage when Codex exposes it. Subscription quota and dollar cost remain unknown.

Each Codex call has a 120-second time limit. Temporary execution failures and invalid output have separate retry budgets. One failure of either kind receives an automatic retry; a second failure of the same kind stops the run. This permits at most three calls per batch. Correction instructions remain in effect after an execution retry. Completed batch checkpoints remain available for manual retry if the automatic budget is exhausted.

The merge adapter removes unused new Theme definitions while preserving every explicit candidate assignment and established Theme. An unused definition contributes no review membership. Removal preserves original assignment positions and records only a safe removal count. Missing assignments, invalid references, conflicting targets, and polarity mismatches still fail validation.

The backend console emits redacted JSON timing events for every Codex attempt and analysis stage. `provider.attempt_failed` includes the safe failure code, execution or validation stage, and whether the app retries. Execution failures also include elapsed time. These events include counts and byte sizes, but exclude prompts, review text, model output, credentials, and process stderr. A timeout establishes that the local call exceeded its deadline; these diagnostics do not establish the provider's internal cause.

## Local data and privacy

- Steam metadata, review text, Review Revisions, jobs, and reports are stored in the configured SQLite database.
- Completed reports save automatically and remain available after closing or restarting the application.
- Each game keeps its latest Main Report and Test Report. Successful replacement deletes the superseded report.
- Report exports and imports are outside scope. The application runs locally without hosted storage or user accounts.
- The app retrieves public Steam data and no private Steam-user data.
- Reviewer identity is omitted from analysis requests.
- Report pages and saved-report cards omit analysis engine names.
- Report Theme disclosures load complete supporting reviews from local storage only when opened.
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
