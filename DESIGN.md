# Game Review Analyzer — Design

## Status

This document describes the approved target behavior. The local application shell and direct-AppID metadata preview are implemented, while review acquisition and report functionality remain under construction. The Catalog, Split, Timeline, and Research prototype directions are approved for implementation; live browser verification remains open.

## Purpose and scope

Game Review Analyzer is a local web application for game developers who want to understand recurring player opinions about one Steam game. It collects Steam store information and reviews, identifies recurring positive and negative game-design themes, and keeps every conclusion traceable to review evidence.

The MVP is distributed from a public GitHub repository under the MIT license and runs on the user's machine. Windows is the first packaged-release target; source-based use should remain portable to macOS and Linux. A public multi-user service is not part of the MVP.

### Goals

- Find a Steam game by name or AppID.
- Capture a comprehensive, time-stamped Steam metadata snapshot.
- Analyze English-language review evidence without requiring the application to download an AI model.
- Support user-selected Codex CLI, Ollama, OpenAI API, Anthropic Claude API, Google Gemini API, and manual Codex analysis behind one provider-neutral contract.
- Present up to 10 reliable positive and 10 reliable negative design themes, with fewer when evidence is insufficient.
- Support quick, full, incremental refresh, filtering, and cohort-specific analysis workflows.
- Keep reports reproducible, inspectable, exportable, and private by default.

### Non-goals for the MVP

- Design recommendations, opportunity scores, or instructions about how the user's game should change.
- Predicting sales or commercial success.
- Cross-game comparison; the data model should permit it later, but the first product is centered on one-game reports.
- Embedding-based clustering. Embeddings remain a future enhancement.
- Automatic model downloads.
- Manual editing of generated themes.
- Automated translation or multilingual analysis.
- Analytics dashboards or application-usage telemetry.
- Review sources other than Steam.
- Public accounts, teams, or multi-tenant hosting.

## Core user experience

### Approved workflow sequence

The approved prototype directions form one continuous flow: Catalog finds or confirms the game; Split configures the review scope, provider, processing location, and estimate; Timeline shows durable acquisition and report-generation progress; Research presents the resulting evidence-backed report. Returning users can open the latest report directly from Catalog, while new or refreshed reports proceed through configuration and progress before opening Research.

The individual prototypes use deliberately different visual treatments to make direction selection clear. Production integration must consolidate them into one shared token system for color, typography, spacing, radii, and motion while preserving each approved interaction model.

### Start and select a game

The approved game-selection direction uses the Catalog's dense search-and-preview workspace. Before a game is selected, the preview area shows a compact list of recent reports rather than an empty prompt. Selecting a catalog result reuses that area for identity confirmation while preserving a stable panel footprint. A clear action returns to the recent-report view.

The home view provides game-name search, direct AppID entry, recent reports, and access to the complete report library. Direct AppID entry and review retrieval work without a Steam Web API key. A securely configured Steam Web API key enables synchronization of Valve's official game catalog for more reliable name search. Best-effort public store search may supplement it but must never be the only way to select a game.

Selecting a game first shows enough identity information to prevent mistakes: title, capsule artwork, developer, release date/status, AppID, and review availability. These fields remain visible when report history exists. A prominent latest-report card appears beneath them, while `Create report` remains the primary action for generating another version; it does not replace the identity information. Games without history show identity confirmation and the `Create report` action.

The report action is labeled **Create report** in the game-selection flow. It means generating a new immutable Report Version, whether it is the first result or a later result for an existing game. The latest report is the prominent entry point; older versions are selected through a lightweight report-history dialog. “Update report” is avoided because it implies mutating an existing result, and “Compare reports” remains reserved for a future comparison feature.

### Configure an analysis

The approved analysis-configuration direction uses a split workspace: configuration controls on one side and a live processing-disclosure panel on the other. The panel keeps selected review volume, expected processing time, approximate paid-provider cost, and local/cloud/manual processing location visible while scope and provider choices change. Quick and Full scopes remain distinct, and creating a report is explicit.

The approved durable-progress direction uses a reassuring stage timeline. It shows completed, current, and upcoming stages; a percentage and elapsed time; and an explicit statement that completed work is checkpointed locally and safe to resume after closing the browser. Cancellation and resume controls remain visible without making recovery feel like an error state.

After confirming the game, the user chooses review scope and an AI provider/model. The app shows the number of selected reviews when known and an approximate pipeline-wide input size and cost for paid providers. The estimate includes planned extraction, consolidation, and report-generation passes plus expected output tokens when those values can be estimated. It does not enforce spending limits or require a separate cost-confirmation dialog.

The application clearly labels processing location:

- **Local:** review text remains on the machine.
- **Cloud:** selected review text is sent to the named provider.
- **External/manual cloud:** the application creates a local package, and review text may leave the machine when the user explicitly gives that package to Codex. The application does not control Codex transmission or retention.

The chosen provider is explicit for each analysis. The application never silently falls back to another provider, because that could change cost and disclose text to a different service.

### Long-running work

Analysis runs as a durable background job with visible stages:

1. Fetching game metadata
2. Downloading reviews
3. Extracting opinions
4. Building themes
5. Generating the report

Refreshing or closing the browser does not cancel the job. The user can cancel explicitly. Successfully downloaded reviews and completed batches remain available for retry, but incomplete work is never presented as a finished report. Jobs resume from safe checkpoints where the provider and pipeline allow it.

### Read a report

The report prioritizes review analysis, then supporting game information:

1. Game identity and report scope
2. Positive and negative design themes
3. Category-based theme exploration
4. Game metadata and feature overview
5. Steam-hosted media
6. Review evidence browser
7. Report history and refresh controls

On wider screens, positive and negative headline themes appear side by side and stack on narrow screens. Reports are immutable: refreshing or rerunning creates a new report version instead of rewriting the old result.

The approved report-exploration direction uses a dense research-workspace overview with positive and negative Theme rankings visible together. Each complete Theme row is an expandable control with a down-arrow indicator. Selecting it opens a lightweight, neutral detail region directly beneath that Theme with its summary, support metrics, category, representative excerpts, and complete-evidence action. Only one Theme detail region is open at a time. Selecting the open Theme again collapses it. The report does not use a separate drawer or compact always-visible Theme inspector.

Visual styling should feel like a professional research tool rather than a copy of Steam. Use neutral surfaces, restrained semantic color, icons and text in addition to color, system light/dark preference, and reduced-motion support. A compact collapsible top-level navigation may be prototyped; layout choices outside the approved report-exploration interaction remain provisional.

## Steam data

### Sources and reliability

The review adapter uses Steam's documented review-list endpoint with cursor pagination and up to 100 reviews per request. It URL-encodes cursors, paces requests, retries bounded transient failures with backoff, checkpoints progress, and deduplicates reviews by Steam recommendation ID.

Valve does not document one complete public API for all desired store fields. Rich metadata therefore comes from replaceable best-effort Steam storefront adapters. A failure to retrieve optional metadata does not block review analysis. Missing values are shown as **Unknown / unavailable**, never as unsupported.

### Metadata snapshot

Each report version preserves the Steam metadata returned for that report, including when available:

- Title, AppID, developers, publishers, franchise, release date/status, and genres
- Steam's short description unchanged and the full “About This Game” content in a collapsible section
- All retrieved visible tags in Steam's priority order, labeled as a time-sensitive snapshot
- Regional price, discount, currency, country, free-to-play status, demo availability, DLC names/count, in-app purchases, editions, and packages
- Supported platforms, languages, system requirements, age/content information, and other store facts
- Feature support and Steam-hosted media references

Store country and currency default from the machine locale, remain clearly visible and configurable, and are stored with the report. The application does not silently convert currencies.

### Feature overview

Features are grouped for quick scanning:

- **Play modes:** single-player, multiplayer, co-op, PvP, shared/split-screen, and cross-platform play
- **Input:** keyboard/mouse, partial/full controller support, and available Steam Deck information
- **Steam features:** achievements, cloud saves, Workshop, trading cards, leaderboards, stats, and Remote Play
- **Platforms and accessibility:** Windows, macOS, Linux, and accessibility fields Steam exposes

Every feature uses one of four explicit states: **Supported**, **Partial**, **Not supported**, or **Unknown / unavailable**. Color is supplemented by text and iconography. Additional feature fields returned by Steam are retained rather than discarded.

### Media

Reports may display Steam-hosted capsule artwork, screenshots, and trailer thumbnails. Media is not rehosted. Trailers never autoplay and are not downloaded; playback or navigation occurs only after an explicit user action through Steam-hosted media.

## Review acquisition and scope

### Import modes

- **Quick:** the latest 5,000 eligible reviews by default, preserving their natural recommended/not-recommended distribution. Users can choose another cap. The report states when this is a small fraction of all matching reviews.
- **Full:** every eligible review available through cursor pagination. The UI warns that this can be slow or costly.
- **Refresh:** adds new reviews and reprocesses updated reviews without redownloading the known corpus. A Quick dataset grows after refresh; it does not discard older reviews to maintain a rolling 5,000-review window.
- **Full reconciliation:** an explicit later operation that scans the current Steam corpus to identify reviews no longer returned by Steam. Normal refresh cannot reliably detect deletions.

For acquisition, **eligible** means English-language reviews matching the configured off-topic and Review Scope controls. Quick acquisition continues pagination until it reaches the selected number of matching reviews or Steam returns no more reviews. When the Steam recommendation scope is `all`, the application does not balance or resample Recommended and Not Recommended reviews.

Steam-marked off-topic activity is excluded by default. Users may include it explicitly, and the choice is recorded in the report scope. All purchase sources are included by default.

### Review scope controls

The analysis scope can restrict:

- Steam recommendation: all, Recommended, or Not Recommended
- Steam purchase, received-for-free status, and written-during-Early-Access status
- Playtime, defaulting to playtime at review with current total playtime as an alternative
- Review date: last 30 days, 90 days, one year, or a custom range

Review date is evidence timing, not proof of the exact game version the reviewer played.

### Evidence Filter and Cohort Analysis

An **Evidence Filter** temporarily restricts an existing report and recalculates metrics only for already discovered Themes. It reranks those Themes, hides Themes with zero support, marks Themes that fall below the report's headline thresholds, and limits excerpts and evidence drill-down to reviews inside the filter. It never discovers a new Theme. It is resettable and is not saved automatically.

A **Cohort Analysis** intentionally reruns theme discovery for a selected Review Cohort. It is stored as a separate immutable result with its exact scope. Minimum cohort-size rules must be calibrated before release.

## Analysis and evidence rules

### Analysis unit

A complete review can discuss several unrelated subjects. The pipeline therefore extracts sentence- or clause-level **Opinion Points** before grouping recurring ideas. **Opinion Sentiment** is determined for each point independently of the review's overall **Steam Recommendation**.

Neutral or purely factual points do not support a theme and do not contribute to theme prevalence or sentiment splits. The original review text remains preserved for evidence.

### No-embedding MVP pipeline

The MVP does not require embeddings. The selected AI provider:

1. Extracts structured, normalized Opinion Points from review batches.
2. Consolidates differently worded but equivalent points into candidate Themes over multiple bounded passes.
3. Assigns Opinion Sentiment, a primary category, optional related categories, and representative evidence.
4. Produces a concise descriptive title and summary supported by the linked points.

Provider responses must conform to versioned structured schemas and reference only supplied review/point identifiers. Review and storefront text is untrusted data, never provider instructions. Prompts isolate it as quoted source material, and import validation rejects unknown identifiers, invented evidence, non-matching excerpts, and unsupported claims rather than silently accepting them. Embeddings may later assist clustering behind the same analysis boundary without changing stored report contracts.

### Theme rules

A **Theme** is a recurring player opinion supported by Opinion Points from multiple distinct reviews. It is more specific than its category. Each Theme contains:

- A specific title and concise evidence-based description
- A positive or negative polarity supported by Opinion Points of that polarity
- Exactly one primary category and zero or more related-category labels
- Distinct-review support count and percentage, using all distinct reviews in the exact Report Version scope as the percentage denominator
- Three to five representative excerpts stored as validated exact spans of source review text
- Complete scope and provenance
- Drill-down to every matched Opinion Point and its full locally stored source review

Each source review counts at most once per Theme, even if it repeats the opinion. Every distinct review has equal weight. Playtime and helpfulness remain visible context and never become hidden frequency multipliers.

Headline results contain up to 10 positive and 10 negative design Themes across the complete report, not per category. Themes must meet both an absolute-support and percentage threshold; exact values require evaluation with real games. The app never pads the report with weak findings. Lower-frequency evidence may remain searchable without being stated as a report conclusion.

Reports are evidence-only. Generated text describes recurring player opinions and does not recommend design changes.

### Categories

The shared design taxonomy is:

1. Gameplay and mechanics
2. Progression and rewards
3. Difficulty and balance
4. Content, variety, and replayability
5. Controls, interface, and onboarding
6. Narrative, characters, and world
7. Multiplayer and social experience
8. Visuals and audio
9. Accessibility
10. Monetization and value
11. Game-specific

**Game-specific** is used only when no shared category accurately fits. Category overlap never duplicates a Theme or its counts.

Rare crashes, performance problems, save corruption, and similar technical defects do not receive a special alert or occupy the headline design lists. Genuinely frequent technical feedback becomes a **Technical Theme**, using the same evidence and metric contract as a Theme but appearing in a distinct secondary report section outside the design taxonomy and headline rankings. Its display threshold must be calibrated independently and should be high enough that technical findings do not distract from the product's design-learning purpose.

### Mixed reception

Semantically opposing positive and negative Themes about the same mechanic are linked but remain present in their respective rankings. Opening either entry shows one combined evidence view. The compact summary format is:

`65% liked · 28% disliked · 7% mixed · Mentioned by 12% (214/1,800)`

Liked, disliked, and mixed use distinct opinionated reviews about that mechanic as the denominator. A mixed review expresses both positive and negative points about it. “Mentioned by” uses all distinct reviews in scope as the denominator and excludes neutral-only mentions from the numerator.

## Evidence presentation and privacy

Representative evidence displays Steam recommendation, review date, playtime at review, current playtime, helpful votes, and applicable Early Access, received-free, and Steam-purchase labels. Full source text expands locally.

The normal interface and default exports omit reviewer names, avatars, and SteamIDs. An optional link may open the original public review on Steam, where Steam may reveal reviewer identity.

Steam metadata, review text, provider output, and imported analysis files are all treated as untrusted content. The interface and exports escape plain text, sanitize permitted markup with an explicit allowlist, block executable content and unsafe URLs, and protect external navigation against opener access.

## AI providers and credentials

### Provider contract

The analysis pipeline is provider-neutral. Initial adapters are:

- Codex CLI using the user's existing local installation and login
- Ollama using a model the user installed independently
- OpenAI API
- Anthropic Claude API
- Google Gemini API
- Manual Codex analysis package export/import

The automated Codex adapter runs `codex exec` non-interactively in an isolated temporary directory with an ephemeral session, read-only sandbox, explicit output schema, bounded retries, cancellation, and no provider fallback. The application supplies the analysis instructions; users do not prepare prompts or move files manually. Codex authentication remains owned by the separately installed CLI and is never read or stored by the application. Review text is processed by OpenAI under the user's Codex account and is labeled external cloud processing.

The application never downloads an Ollama model. It detects Ollama, lists installed compatible models, recommends model names, and displays copyable commands that the user chooses to run outside the app. Ollama structured output is called directly through its local API rather than through an agentic CLI. If Codex or Ollama is unavailable, Steam lookup, metadata retrieval, and review downloading still work; analysis waits for another configured provider.

### Credentials

Credentials never appear in SQLite, report files, exports, logs, URLs, analytics, error payloads, frontend assets, or backend-to-frontend responses. A key entered in Settings exists transiently in client memory and in the dedicated local credential-submission request, is excluded from request logging and diagnostics, and is cleared from the client after the backend accepts it. Supported sources are:

- Session-only memory, the default for keys entered in Settings
- An explicit **Remember securely** option backed by the operating system credential vault
- Environment variables

After entry, the full secret is never displayed again. Secret values are redacted from diagnostics. Provider requests originate from the local backend rather than being embedded in frontend assets.

### Cost estimate

For paid providers, the UI estimates approximate total cost from selected review text, the chosen model, planned repeated passes, and expected input and output tokens. Estimates are advisory because tokenization, generated output, retry behavior, and provider pricing can vary. The estimate states what it includes and when pricing data was last updated. The app does not add mandatory spending confirmations or a local spending cap.

Subscription-backed CLI providers do not receive a fabricated dollar estimate. Their disclosure states that the run consumes the user's provider quota, reports measured token usage when the CLI exposes it, and explains that remaining quota and monetary value are unavailable to the application.

### Manual Codex workflow

The app creates an analysis folder containing:

- An agent instruction file
- A manifest describing game, report scope, schema version, and review batches
- Review batch files with minimized identity data
- A strict structured-output schema

Before export, the application labels this workflow **External/manual cloud**, identifies the review text included, and warns that Codex processing and retention occur outside the application's control. The user opens the folder in a Codex session and follows the supplied task. Codex writes result files back into the folder. The application validates schema, identifiers, completeness, exact evidence spans, and report-version matching before import. Invalid or partial output does not become a completed report.

## State, ownership, and lifecycle

- A **Game Dataset** owns downloaded Steam reviews for one AppID and is reused across report versions. Each observed state of a Steam review is stored as an immutable **Review Revision**; refresh adds a revision instead of overwriting prior evidence.
- An **Analysis Job** owns durable acquisition and processing checkpoints until it completes, fails, is cancelled, or is deleted.
- A **Report Version** is an immutable result tied to an exact review scope, exact Review Revision membership, metadata snapshot, schema and prompt versions, pipeline configuration, provider and model identifiers, and creation time.
- A **Cohort Analysis** is a Report Version whose scope is an explicit Review Cohort.
- The newest Report Version opens by default; older versions remain in history until manually deleted.
- Refresh creates a new Report Version after adding reviews, recording new Review Revisions for changed reviews, and reclustering the relevant stored corpus. Historical reports continue to resolve their original Review Revisions.

Application data lives in the operating system's standard application-data directory by default. Settings show storage use and allow deletion of one report version, an incomplete job, or an entire game dataset and its reports. Destructive deletion requires explicit confirmation. Changing the data directory is a later supported operation.

## Exports

The MVP exports:

- **Single-file HTML:** a readable report containing representative excerpts and externally referenced Steam-hosted media; the report file is standalone, but external media still requires a network connection
- **JSON:** structured report data suitable for later re-import when the matching Game Dataset and Review Revisions are present locally
- **CSV:** themes and evidence for further inspection

Default exports omit full review text and reviewer identifiers. JSON import validates the schema and every referenced Game Dataset and Review Revision, and fails clearly if matching local evidence is absent. Full review text can be included only through an explicit JSON/CSV export option, but those exports are not a complete portable backup. A self-contained **Portable Report Archive** with all required evidence and explicit privacy warnings is deferred. PDF export is deferred.

## Architecture and durable seams

The approved stack is React, TypeScript, and Vite for the interface; FastAPI and Python for ingestion, jobs, analysis orchestration, and exports; and SQLite for local persistence. Compiled frontend assets are served by the local backend in production use.

Durable module boundaries are:

- **Game Catalog:** official keyed catalog plus replaceable fallback search
- **Steam Metadata:** normalized snapshot contract over best-effort store sources
- **Review Ingestion:** paginated acquisition, normalization, deduplication, append-only Review Revisions, and refresh
- **Job Runner:** durable stages, cancellation, retry, resume, and progress events
- **Analysis Provider:** versioned structured request/response independent of vendor
- **Theme Metrics:** deterministic counts and percentages computed from stored memberships, never trusted from generated prose
- **Credential Store:** session, operating-system vault, and environment adapters
- **CLI Runner:** isolated non-interactive provider processes with availability checks, cancellation, bounded output, and redacted diagnostics
- **Report Repository:** immutable report versions and evidence provenance
- **Export/Import:** versioned schemas with strict validation

The React client does not own credentials, Steam integration logic, provider SDK calls, or authoritative metrics.

## Failure and edge cases

- An invalid AppID produces a specific validation error before a job starts.
- Empty review scopes complete metadata retrieval but explain that no analysis can be generated.
- Steam timeouts, throttling, malformed pages, and cursor repetition stop with an actionable retry state while preserving checkpoints.
- Optional metadata failures produce unknown fields and source-status details without blocking review analysis.
- Provider unavailability never causes automatic fallback.
- Invalid provider output is retried only within a bounded policy, then preserved as a failed job with diagnostics that exclude secrets and review text where unnecessary.
- A cancelled or failed job can reuse safe completed work but never appears as a final report.
- Historical reports and their exact source evidence remain unchanged when Steam metadata, reviews, taxonomy, prompts, models, or provider behavior later changes.
- Full-history imports and very large paid-provider runs show time, volume, and approximate-cost warnings before work begins.

## Testing boundaries and acceptance behavior

### Highest-value test seams

- Steam fixtures test pagination, cursor encoding, retries, duplicate IDs, append-only updated-review revisions, empty sets, and partial metadata.
- Fake AI providers test schema validation, unsupported evidence references, partial batches, deterministic retries, and no-fallback behavior.
- Pure Theme Metrics tests reproduce all support, prevalence, mixed-reception, and Evidence Filter calculations from memberships.
- Job Runner tests verify checkpoint/resume/cancel behavior across process and browser interruption.
- Credential Store contract tests verify that secrets never enter database records, logs, exports, URLs, frontend assets, or backend-to-frontend responses and that the dedicated submission path cannot be logged.
- Report and Codex import tests reject schema/version/scope mismatches and unsupported claims.
- Content-safety tests verify output escaping, markup sanitization, safe external links, and rejection of prompt-injected or fabricated evidence.
- Accessibility tests verify feature states without color, keyboard access, reduced motion, and responsive evidence navigation.

### Observable scenarios

- A user enters an AppID without any keys, downloads metadata and reviews, exports a Codex package, imports valid results, and inspects evidence-backed Themes.
- A user with an authenticated Codex CLI installation explicitly starts analysis, sees the external-cloud and quota disclosure, and receives a validated report without manually preparing instructions or moving result files.
- A user configures a cloud provider session key, sees a cloud-processing label and approximate cost, completes analysis, and cannot retrieve the key from storage or diagnostics.
- A Quick report starts with the latest 5,000 eligible English reviews, later refreshes with new or revised reviews, and creates a new immutable report version over the grown dataset while the old report still resolves its original Review Revisions.
- Filtering for high-playtime reviews recalculates and reranks existing Theme metrics immediately, limits visible evidence to the filter, and marks below-threshold Themes; running a Cohort Analysis instead creates a separately scoped result that can discover new Themes.
- Missing screenshots or feature metadata appear as unknown while the review report still completes.
- A mixed mechanic displays the agreed sentiment/prevalence line and every percentage reproduces from distinct-review evidence.

## Deferred work

- Embedding-assisted semantic matching and clustering
- Cross-game and cross-version comparison views
- Automated translation and multilingual analysis with original-text provenance
- PDF export
- Portable Report Archives containing all evidence needed for restore on another installation
- Packaged macOS and Linux releases
- Public multi-user hosting, authentication, quotas, and hosted persistence
- Additional review platforms
- Manual theme correction tools
- Statistical analytics dashboards

## Open questions requiring evidence or later judgment

- What support and coherence thresholds produce reliable design Themes across games of different sizes?
- What minimum cohort size supports meaningful recalculation and new discovery?
- What threshold makes technical feedback genuinely frequent enough for the secondary section?
- How accurately does the no-embedding pipeline group paraphrases across the initial AI providers?
- How should future taxonomy revisions be exposed while preserving immutable historical reports?
- What Steam retention, attribution, and request-rate practices are required before a public release?
- Who should be named as the copyright holder in the MIT license file?
