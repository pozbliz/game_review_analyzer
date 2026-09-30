# Game Review Analyzer - Design

## Status

Approved on 2026-09-29. This document describes the target behavior.

The current application still implements evidence-heavy immutable reports, Opinion Points, categories, filters, and Version 2 contracts.

Those behaviors remain implemented until the new design is planned and built.

## Purpose and scope

Game Review Analyzer is a local web application for game developers. It identifies the main positive and negative opinions across one Steam game's English reviews.

The target favors useful summaries, lower token use, fast recovery, and simple report reading. It does not provide per-review proof for Theme assignments.

The application runs on the user's machine. Windows is the first packaged-release target. Source-based use should remain portable where dependencies permit.

### Goals

- Find a Steam game by name or AppID.
- Download and retain its available English Steam reviews.
- Produce useful positive and negative Themes through Codex CLI.
- Compare support in the oldest and newest analyzed cohorts.
- Grow one main report in user-requested increments.
- Preserve completed provider work across interruption and retry.
- Calculate every displayed metric locally from validated memberships.
- Export aggregated reports without review text or reviewer identity.

### Non-goals

- Per-review evidence, exact excerpts, Opinion Points, or evidence drill-down.
- Theme categories, mechanic classifications, mixed-reception links, or direction labels.
- Evidence Filters or temporary metric recalculation by review attributes.
- Manual Theme editing, hiding, or correction.
- Design recommendations or predictions about sales.
- Review sources other than Steam.
- Model downloads, automatic provider fallback, or multiple Version 3 providers.
- Version 2 report reading, import, migration, or compatibility.
- Preserved history for superseded main reports or test reports.
- Public accounts, teams, or multi-tenant hosting.

## Core user experience

### Prepare a game

The Catalog supports game-name search and direct AppID entry. It shows enough metadata to prevent selecting the wrong game.

The identity view includes title, capsule artwork, developer, release status, AppID, and review availability when Steam supplies them.

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

When fewer than 1,000 usable reviews remain, the action states the remaining count. It analyzes every usable unseen review once.

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

### Map contract

Reviews are packed by character capacity first and a maximum of 250 reviews second. Each selected review appears in one map batch.

Every map result returns completed review identifiers and Theme candidates. Each candidate contains:

- Candidate identifier
- Title and summary
- Positive or negative polarity
- Supporting review identifiers from that batch

The provider returns no excerpts, Opinion Points, categories, percentages, final counts, or rankings.

The backend rejects incomplete batches, unknown review identifiers, duplicate identifiers, empty support, and unsupported polarity values.

### Merge contract

The merge receives established Theme definitions, retained near-threshold candidates, and candidates from the new reviews.

It maps each new candidate to an established Theme, a new Theme, or discard. The provider returns mappings rather than calculated support.

The merge result contains Theme definitions and one assignment item per candidate key. Each item contains a returned Theme ID or `null` for discard. Local validation rejects missing, unknown, or duplicate candidate keys.

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

Selection and run creation reserve an exact review scope atomically. Concurrent runs cannot reserve the same extension scope.

Each validated batch is checkpointed with its ordered input digest, provider, model, contract version, result, and measured usage.

Cancellation retains validated checkpoints. Retry processes only incomplete batches and preserves the current visible report.

Only transient provider failures receive one automatic retry. Validation failures do not repeat the unchanged request.

No partial report becomes visible. Report replacement and its review bindings commit atomically.

One shared contract-version value controls provider requests, checkpoint lookup, and progress counting.

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

Application data remains local in the configured SQLite path. Storage controls may delete a Main Report, Test Report, inactive run, or Game Dataset.

Destructive deletion requires explicit confirmation. Deleting a Game Dataset also deletes its reports, runs, reviews, and checkpoints.

## Exports and privacy

Version 3 exports contain aggregated Themes and metrics.

- HTML contains the readable report without review evidence.
- CSV contains one row per Theme with total and cohort metrics.
- JSON contains the report and internal revision memberships for local backup and re-import.

Default exports contain no review text, excerpts, reviewer name, avatar, or SteamID.

JSON import requires the matching local Game Dataset and Review Revisions. Imported Version 3 reports use the same main or test slot rules.

Steam metadata, review text, and provider output remain untrusted content. Interfaces and exports escape text and block unsafe markup and URLs.

## Architecture and durable seams

The approved stack remains React, TypeScript, Vite, FastAPI, Python, and SQLite.

Existing module boundaries remain useful:

- **Review Ingestion:** Full Import, refresh, stable identity deduplication, and immutable Review Revisions
- **Job Runner:** durable acquisition progress, cancellation, retry, and recovery
- **Analysis Provider:** versioned map and merge contracts over untrusted review text
- **Analysis Runner:** review reservation, batching, checkpoints, cancellation, and atomic report replacement
- **Theme Metrics:** pure calculation from scope and membership sets
- **Report Repository:** one main and one test slot per game with exact bindings
- **Export/Import:** Version 3 aggregated formats and strict local membership validation
- **CLI Runner:** isolated Codex execution, bounded retries, cancellation, usage, and redacted diagnostics

The provider interface remains the main external seam. Selection, merging, and metrics remain local application behavior.

The React client does not own provider execution, Steam access, authoritative memberships, or metric calculation.

## Failure and edge cases

- Missing Full Import blocks both test and main analysis with an actionable message.
- Failed refresh blocks Extend and Replace while preserving the current reports.
- Empty datasets explain that analysis cannot start.
- Oversized reviews are skipped and replaced when another unseen review exists.
- Invalid provider output fails the run without changing either report slot.
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
- Provider contract tests reject incomplete batches, duplicate identifiers, unknown memberships, invalid polarity, and malformed mappings.
- Merge tests cover stable Theme definitions, candidate retention, promotion, discard, and membership deduplication.
- Theme Metrics tests cover 5% eligibility, five-item caps, cohort denominators, unequal cohorts, ranking, and empty reports.
- Analysis Runner tests cover atomic reservation, checkpoint reuse, cancellation, restart, refresh failure, and replacement safety.
- Report Repository tests prove one independent main slot and one independent test slot per game.
- Export tests prove aggregated content, local JSON validation, and absence of review text or reviewer identity.
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

## Deferred work

- Additional hosted or local analysis providers
- Model and reasoning controls
- Embedding-assisted grouping
- Cross-game comparison
- Automated translation and multilingual analysis
- PDF export
- Portable archives containing raw review text
- Public multi-user hosting

## Open questions requiring human judgment

None.
