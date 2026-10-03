# Game Review Analyzer - Design

## Status

The progressive report design was approved on 2026-09-29.

The deterministic provider-boundary revision was approved on 2026-10-01.

The current application implements the progressive aggregate report design through Slice 20.

Version 2 routes, schemas, storage, controls, and compatibility were removed on 2026-10-02.

The user removed report exports and imports from scope on 2026-10-03. Local SQLite persistence remains the storage model.

## Purpose and scope

Game Review Analyzer is a local web application for game developers. It identifies the main positive and negative opinions across one Steam game's English reviews.

The target favors useful summaries, lower token use, fast recovery, and simple report reading with on-demand access to supporting reviews.

The application runs on the user's machine. Windows is the first packaged-release target. Source-based use should remain portable where dependencies permit.

### Goals

- Find a Steam game by name or AppID.
- Download and retain its available English Steam reviews.
- Produce useful positive and negative Themes through Codex CLI.
- Compare support in the oldest and newest analyzed cohorts.
- Grow one main report in user-requested increments.
- Preserve completed provider work across interruption and retry.
- Restrict Codex to semantic Theme extraction, summarization, polarity, membership, grouping, and discard decisions.
- Derive identifiers, scope completion, provenance, metrics, ordering, and persistence locally.
- Calculate every displayed metric locally from validated memberships.

### Non-goals

- Exact excerpts or Opinion Points.
- Theme categories, mechanic classifications, mixed-reception links, or direction labels.
- Evidence Filters or temporary metric recalculation by review attributes.
- Manual Theme editing, hiding, or correction.
- Design recommendations or predictions about sales.
- Review sources other than Steam.
- Model downloads, automatic provider fallback, or multiple Version 3 providers.
- Version 2 report reading, import, migration, or compatibility.
- Preserved history for superseded main reports or test reports.
- Public accounts, teams, or multi-tenant hosting.
- Report exports, report imports, PDF reports, or Portable Report Archives.

## Core user experience

### Prepare a game

The Catalog supports game-name search and direct AppID entry. It shows enough metadata to prevent selecting the wrong game.

The identity view includes title, capsule artwork, developer, release status, AppID, and review availability when Steam supplies them.

The overall Steam review count remains visible. Users can expand it to load current nonzero review totals for each Steam API language.

Games with retained work expose their current Main Report and Test Report separately. Neither slot presents superseded report history.

A completed Full Import is required before analysis. The Full Import establishes access to the true oldest and newest retained reviews.

The 50-review test is optional. Users may start the main 1,000-review report directly.

### Run a 50-review test

The test analyzes 25 oldest and 25 newest reviews from the current local Full Import. It does not refresh Steam first.

The result is an actual saved report. Each game retains at most one test report, and a later test replaces it.

The test report remains separate from the main report. It cannot be extended, and its provider result is not reused by main analysis.

The test action remains available while a Main Report exists. Running it never changes the Main Report.

The test uses the same Theme candidate contract and metric rules as the main report. A single provider call is used when all reviews fit.

### Create the main report

The first main report analyzes up to 1,000 reviews. It selects up to 500 oldest and 500 newest reviews without overlap.

The main report is the only progressive report for its game. The interface does not expose earlier 1,000-review stages as report history.

A successful 1,000-review main report replaces the visible main report. It does not replace the separate test report.

### Extend the main report

**Extend report** first refreshes Steam. If refresh fails, the extension stops and the current report remains available.

After refresh, selection adds up to 500 oldest and 500 newest unseen review identities. New Steam reviews can therefore enter the newest selection.

Provider, model, analysis contract, and metric policy remain fixed while the Main Report is extended.

For example, 200 new reviews plus 300 previously unseen recent reviews form the next 500-review newest segment.

The extension adds its validated memberships to the current cumulative analysis. It then recalculates metrics over every analyzed membership.

The current report remains readable during processing. A successful extension atomically replaces it with the cumulative report.

A failed or cancelled extension leaves the current report unchanged. Retry resumes from validated checkpoints.

When fewer than 1,000 usable reviews remain before refresh, the action states the current count. The post-refresh selection remains authoritative and analyzes every usable unseen review once.

### Replace the main report

**Replace report** refreshes Steam and starts a fresh analysis over up to 1,000 reviews.

Replacement does not reuse prior main-report memberships, candidates, or completed analysis checkpoints. A retry of the replacement run may reuse its own checkpoints.

The current report remains available until replacement succeeds. Success deletes the superseded main report and makes the new result current.

Replacement is the correction path for a poor Theme taxonomy. It also applies when a future contract or supported model changes.

### Read a report

The report shows up to five positive and five negative Themes. Technical and design feedback compete in the same rankings.

Each Theme shows:

- Title and short summary
- Total support count and percentage
- Oldest-cohort support percentage
- Newest-cohort support percentage
- Percentage-point difference between cohorts
- A collapsible list of every matching review, sorted by helpful votes descending

The evidence list loads from retained local Review Revisions only when opened. Its viewport shows about five reviews before scrolling.

The interface shows no category, excerpt-only evidence, direction label, or AI-classification notice.

Positive and negative lists appear side by side on wide screens and stack on narrow screens. Game metadata follows the Theme summary.

The interface uses text and icons with color, supports keyboard operation, respects reduced motion, and remains usable on narrow screens.

## Steam data and review selection

### Sources and metadata

The review adapter uses Steam cursor pagination, URL-encoded cursors, pacing, bounded retry, checkpointing, and stable identity deduplication.

Rich store metadata comes from replaceable, best-effort Steam storefront sources. Optional metadata failure does not block review analysis.

Missing metadata appears as **Unknown / unavailable**. The application never presents missing data as unsupported.

Each Main Report and Test Report stores its Steam metadata snapshot. Later Steam changes do not alter the visible snapshot until report replacement.

The snapshot retains available identity, description, tags, regional price, release, platform, language, feature, DLC, requirement, and media fields.

Store country and currency remain visible and configurable. The application shows returned prices without silent currency conversion.

Steam-hosted images may appear in reports. Trailers never autoplay, and media navigation requires an explicit user action.

### Acquisition

Steam review acquisition remains paginated, paced, checkpointed, and resumable. It deduplicates reviews by stable Steam review identity.

Full Import retrieves every eligible review available through the terminating Steam cursor flow. Refresh adds new and edited Review Revisions.

Quick Import may remain available for acquisition, but it cannot start a Main Report or Test Report.

Steam-marked off-topic activity remains excluded by default. Analysis uses the Full Import's retained English review scope.

### Deterministic ordering

Review selection uses this stable order:

1. Steam creation time
2. Stable Steam review identity
3. Review Revision identity

The oldest selection starts at the beginning. The newest selection starts at the end after excluding identities already selected or analyzed.

When the boundaries meet, overlap is removed. The application selects each stable review identity at most once for the main report.

### New and edited reviews

The main report has no frozen dataset cutoff. New review identities found by refresh join the unseen selection pool.

An edit to an already analyzed review does not re-enter the progressive report. Its existing membership remains unchanged.

An unseen review uses its latest retained Review Revision when its run reserves the review. Replacement also uses the latest retained revisions.

Reviews imported during an active run wait for the next extension. The active run keeps its exact reserved scope.

### Oversized reviews

Selected reviews use their complete text. The application does not truncate long reviews.

A review that cannot fit within one provider request is skipped. Selection replaces it with the next unseen review when possible.

Skipped review identities remain excluded from that run. The report states the oversized-review count, and denominators include only analyzed reviews.

## Theme analysis

### Provider policy

Version 3 supports Codex CLI with one application-supported model and low reasoning. The application stores provider and model provenance.

Users do not select a model or reasoning level. The application never switches provider or model automatically.

Codex CLI runs serially through the existing isolated subprocess boundary. Other providers remain outside this design.

Codex authentication remains owned by the installed CLI. The application never reads or stores the user's Codex credentials.

The interface labels Codex processing as external cloud work and reports measured token usage when the CLI provides it.

The application does not invent a monetary estimate or claim access to remaining subscription quota.

### Deterministic ownership

Codex is an external semantic dependency. It identifies recurring opinions, writes Theme titles and summaries, assigns polarity, links supporting reviews, and groups or discards candidates.

The application owns request identity, scope digests, contract version, provider and model provenance, completed scope, persistent identifiers, established Theme state, membership deduplication, thresholds, ranking, checkpoints, and persistence.

Provider responses do not repeat application-owned identity or provenance fields. A successful validated response completes the exact request that produced it; the application records that completion locally.

The adapter converts provider output into the internal analysis result. Callers receive application-owned identities and provenance rather than raw provider claims.

### Map contract

Reviews are packed by character capacity first and a maximum of 250 reviews second. Each selected review appears in one map batch.

Every review has a stable zero-based position within its map request. Each map result returns only Theme candidates. Each candidate contains:

- Title and summary
- Positive or negative polarity
- Supporting review positions from that batch

The provider returns no excerpts, Opinion Points, categories, percentages, final counts, or rankings.

The application maps supporting positions to the exact Review Revisions in the request and assigns each candidate an internal identifier. It removes repeated supporting positions because they do not change membership.

The backend rejects out-of-range positions, empty support, unsupported polarity values, and malformed candidates. It derives batch completion, request identity, scope, provider, model, and contract version from the invocation.

### Merge contract

The merge receives established Theme definitions and an ordered list containing retained near-threshold candidates plus candidates from new reviews.

It maps each candidate to an established Theme, a new Theme, or discard. The provider returns one assignment for each candidate in the same order as the request.

Each assignment contains an established Theme reference, a new-Theme result position, or discard. New Theme results contain only a title, summary, and polarity.

The provider does not return candidate keys, persistent Theme identifiers, established Theme definitions, request identity, scope, or provenance. The application retains established Themes unchanged and assigns persistent identifiers to new Themes.

Local validation requires the assignment count to equal the candidate count. It rejects invalid targets, missing new Themes, unused new Themes, and polarity mismatches.

Supporting review memberships remain local. The backend unions distinct memberships and calculates all metrics.

Established Theme identities, titles, summaries, and polarities remain fixed during extension. Extensions do not split or merge established Themes.

A poor established taxonomy requires **Replace report**. Replacement creates its Theme system without reusing the old definitions.

### Near-threshold candidates

A new candidate remains internal when it reaches at least 2% support within either newly analyzed cohort segment.

Smaller candidates are discarded. Retained candidates carry their validated memberships into later merges and remain hidden until promotion.

When a retained candidate reaches the visible threshold, it becomes an established Theme. Its memberships count once per distinct review identity.

The 50-review test does not retain hidden candidates after its report is complete because that report cannot be extended.

### Visible Theme rules

A Theme becomes visible when it reaches at least 5% support in either cumulative cohort.

A visible Theme may disappear from a later cumulative report when both cohort percentages fall below 5%. Its definition remains internal for later mapping.

The report ranks Themes by their higher cohort percentage. Deterministic local tie-breaking produces stable order.

Each polarity shows at most five Themes. The application shows fewer when fewer meet the threshold.

One review may support several Themes. It counts once within each Theme.

An analysis with no qualifying Themes succeeds. The report states that no main Theme met the 5% threshold.

## Metrics

The backend calculates metrics from distinct validated Theme memberships. Provider-supplied counts or percentages are never accepted.

For each Theme:

- Total percentage uses all analyzed reviews as its denominator.
- Oldest percentage uses analyzed oldest-cohort reviews as its denominator.
- Newest percentage uses analyzed newest-cohort reviews as its denominator.
- Percentage-point difference is newest percentage minus oldest percentage.

Unequal cohort sizes are valid when fewer reviews remain or when only new recent reviews are available.

## Progress, recovery, and replacement safety

The main progress sequence is:

1. Refreshing Steam, when required
2. Selecting and reserving reviews
3. Analyzing batches
4. Merging Themes
5. Calculating metrics
6. Saving and replacing the report

Starting an extension opens this progress view automatically. During Steam refresh, the view shows imported reviews as a percentage of the refresh scan limit.

Report pages and saved-report cards omit provider and model names. Provider and model provenance remain internal for validation, extension compatibility, and diagnostics.

Selection and run creation reserve an exact review scope atomically. Concurrent runs cannot reserve the same extension scope.

Each validated batch is checkpointed with its ordered input digest, provider, model, contract version, application-owned result, and measured usage.

Cancellation retains validated checkpoints. Retry processes only incomplete batches and preserves the current visible report.

Transient provider failures receive one automatic retry. A correctable semantic-output validation failure may receive one retry with a specific correction instruction.

The application does not retry an unchanged invalid contract. A second invalid response fails safely and preserves validated checkpoints.

No partial report becomes visible. Report replacement and its review bindings commit atomically.

One shared provider-contract version controls requests, checkpoint lookup, and progress counting. A breaking provider-boundary revision advances this version and does not reuse older in-progress checkpoints.

Existing completed Version 3 aggregate reports remain readable. They retain their stored memberships and can participate in later extension through the revised provider boundary.

Redacted telemetry records stages, durations, usage, retry state, safe failure codes, HTTP failures, background-job failures, and browser runtime failures.

The backend writes bounded rotating JSON logs beside the database. Diagnostics remain a backend support surface rather than a user-facing interface.

Telemetry excludes review text, prompts, model output, raw provider stderr, credentials, and API keys.

## State and ownership

- A **Game Dataset** owns retained Steam reviews and immutable Review Revisions for one AppID.
- A **Main Report** is the one current cumulative report for a game.
- A **Test Report** is the one current 50-review provider test for a game.
- An **Analysis Run** owns one reserved scope, state, checkpoints, usage, and pending result.
- A **Theme Membership** links one Theme to one analyzed Review Revision internally.
- A **Theme Candidate** is hidden merge state that may later become an established Theme.

Main and test report slots are independent. Replacing one never changes the other.

Reports store exact analyzed Review Revision memberships, cohort membership, provider provenance, contract version, metric policy, and Steam metadata.

Version 2 records and exports are unsupported. The target requires no compatibility reader, importer, or migration path.

Application data remains local in the configured SQLite path. Completed reports save automatically and remain available after closing or restarting the application. Storage controls may delete a Main Report, Test Report, inactive run, or Game Dataset.

Destructive deletion requires explicit confirmation. Deleting a Game Dataset also deletes its reports, runs, reviews, and checkpoints.

## Local storage and privacy

Reports remain in the local SQLite database. The application provides no report download or report-file import workflow. Database backups remain an operational responsibility.

Steam metadata, review text, and provider output remain untrusted content. Interfaces escape text and block unsafe markup and URLs.

## Architecture and durable seams

The approved stack remains React, TypeScript, Vite, FastAPI, Python, and SQLite.

Existing module boundaries remain useful:

- **Review Ingestion:** Full Import, refresh, stable identity deduplication, and immutable Review Revisions
- **Job Runner:** durable acquisition progress, cancellation, retry, and recovery
- **Analysis Provider:** narrow versioned contracts for semantic map and merge decisions over untrusted review text
- **Analysis Runner:** review reservation, batching, checkpoints, cancellation, and atomic report replacement
- **Theme Metrics:** pure calculation from scope and membership sets
- **Report Repository:** one main and one test slot per game with exact bindings
- **CLI Runner:** isolated Codex execution, bounded retries, cancellation, usage, and redacted diagnostics

The provider interface remains the main external seam. Its adapter hides raw model output and returns application-bound semantic results.

Selection, identity assignment, scope completion, established Theme retention, membership normalization, thresholds, ranking, metrics, checkpoints, and persistence remain local application behavior.

The React client does not own provider execution, Steam access, authoritative memberships, or metric calculation.

## Failure and edge cases

- Missing Full Import blocks both test and main analysis with an actionable message.
- Failed refresh blocks Extend and Replace while preserving the current reports.
- Empty datasets explain that analysis cannot start.
- Oversized reviews are skipped and replaced when another unseen review exists.
- Invalid provider output fails the run without changing either report slot.
- Repeated valid supporting positions are normalized to one membership.
- An out-of-range supporting position or invalid merge target fails validation.
- A merge result with too few or too many assignments fails validation.
- Provider unavailability never triggers fallback.
- Cancellation preserves validated checkpoints and the current report.
- Backend restart resumes the reserved scope and validated checkpoints.
- A final extension may contain fewer than 1,000 reviews.
- New reviews after full coverage become the next newest-only extension.
- A valid run may produce no visible Themes.
- Replacement failure leaves the prior main report available.

## Testing boundaries and observable scenarios

### Highest-value test seams

- Pure selection tests cover deterministic ordering, overlap removal, new reviews, ignored edits, oversized reviews, and final partial extensions.
- Provider contract tests reject malformed candidates, out-of-range positions, invalid polarity, invalid merge targets, and assignment-count mismatches.
- Provider adapter tests prove that Codex output contains no application-owned IDs, completion claims, scope identity, or provenance.
- Map contract tests cover position binding, repeated-position normalization, out-of-range rejection, and deterministic candidate identifiers.
- Merge contract tests cover ordered assignment binding, established Theme retention, deterministic new Theme identifiers, invalid targets, and assignment-count mismatch.
- Merge tests cover stable Theme definitions, candidate retention, promotion, discard, and membership deduplication.
- Theme Metrics tests cover 5% eligibility, five-item caps, cohort denominators, unequal cohorts, ranking, and empty reports.
- Analysis Runner tests cover atomic reservation, checkpoint reuse, cancellation, restart, refresh failure, and replacement safety.
- Report Repository tests prove one independent main slot and one independent test slot per game.
- Frontend tests cover actions, progress, one-report replacement, test-report separation, empty results, and accessible responsive lists.

### Observable scenarios

- A user completes Full Import, skips testing, and creates a 1,000-review main report.
- A user creates a 50-review test report without refreshing Steam, then later creates an independent main report.
- A later test replaces only the prior test report.
- Extend finds 200 new reviews and combines them with 300 prior unseen reviews in the newest segment.
- A failed extension leaves the existing cumulative report readable and resumes only incomplete batches.
- A successful extension replaces the 1,000-review report with one cumulative 2,000-review report.
- Replace discards prior analysis state, reprocesses its scope, and preserves the old main report until success.
- A Theme qualifies because it reaches 5% in the newest cohort despite lower total support.
- A candidate retained at 2% becomes visible after later extensions.
- A completed run with no qualifying Themes produces a valid empty report.
- A provider repeats a supporting review position; the application stores one membership and continues.
- A provider returns the wrong number of merge assignments; the run fails without changing the current report.
- An application update changes the provider contract; completed reports remain readable while older incomplete checkpoints are not reused.

## Deferred work

- Additional hosted or local analysis providers
- Model and reasoning controls
- Embedding-assisted grouping
- Cross-game comparison
- Automated translation and multilingual analysis
- Public multi-user hosting

## Open questions requiring human judgment

None.
