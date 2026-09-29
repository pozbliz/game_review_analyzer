# Game Review Analyzer — Implementation Plan

## Status

The progressive aggregate-report design and this strategic plan are approved. Slices 0–15 record the earlier implementation. Their Version 2 report behavior is superseded where it conflicts with `DESIGN.md`. Slices 16–21 replace that behavior. Slice 16 is the execution frontier. `TASKS.md` still describes the earlier implementation and must be revised through `$create-implementation-tasks` before code changes begin.

## Durable verification seams

Implementation should preserve these stable behavioral boundaries:

- versioned HTTP API contracts between the backend and frontend
- Steam Game Catalog and Steam Metadata adapters
- Review Ingestion with append-only Review Revisions
- durable Job Runner
- versioned Analysis Provider contracts
- deterministic Theme Metrics
- Credential Store
- immutable Report Repository
- versioned Export/Import

Each slice must remain green, independently verifiable, and suitable for an atomic commit.

## Slice 0 — Approve the core workflow prototype

**Outcome:** Approve an implementation-ready direction for game selection, analysis setup, durable progress, reports, evidence, and history.

**Blocked by:** None.

**Scope:** Visual prototype, domain terminology, provider/privacy messaging, responsive behavior, accessibility, and information hierarchy.

**Acceptance:** Multiple genuinely different prototypes use realistic Steam metadata, mixed reception, feature states, and evidence. They are reviewed at laptop and narrow widths, and the user selects or explicitly combines a direction that communicates the workflow without additional explanation.

**Tradeoff:** Production scaffolding waits until the main interaction model is validated.

**Status:** Approved. Connected-browser responsive, accessibility, and interaction verification remains open as follow-up work.

## Slice 1 — Run the local application shell

**Outcome:** Launch a React interface served by FastAPI with SQLite migrations, typed API communication, baseline automated checks, and a production frontend build.

**Blocked by:** Slice 0.

**Scope:** React/TypeScript/Vite, FastAPI/Python, SQLite, the approved two-root repository structure, typed HTTP contracts, reproducible dependency installation, build tooling, health/status behavior, production asset serving, and CI foundations.

**Acceptance:** Committed dependency manifests and lock data support a reproducible clean installation. Backend tests, frontend tests, strict type checking, migrations, and the production build pass. FastAPI serves the compiled frontend, the frontend consumes validated typed health/configuration contracts, and a browser can load the local application and observe backend health. Framework deprecation warnings introduced by the shell are resolved or explicitly constrained with a recorded compatibility decision.

**Tradeoff:** This slice establishes the delivery path but does not yet retrieve Steam data.

**Status:** Complete.

## Slice 2 — Preview a game from its AppID

**Outcome:** Enter a Steam AppID and see enough normalized identity and basic metadata to confirm the correct game, including explicit unknown states.

**Blocked by:** Slice 1, which is complete.

**Scope:** Steam Metadata adapter, normalized metadata contract, initial Game Dataset persistence, API, and game-confirmation interface.

**Acceptance:** Contract fixtures cover valid, invalid, missing, and partially available Steam responses; optional metadata failure does not prevent a valid preview.

**Tradeoff:** Name search and comprehensive storefront fields remain later slices.

**Status:** Complete.

## Slice 3 — Persist a durable Quick review import

**Outcome:** Download and retain the latest 5,000 eligible English reviews with natural recommendation distribution, visible progress, cancellation, retry, and checkpoint resume.

**Blocked by:** None.

**Scope:** Review Ingestion, append-only Review Revision history, Game Dataset ownership, Job Runner, SQLite persistence, progress API, and setup/progress interface.

**Acceptance:** Steam fixtures prove cursor encoding, pagination, pacing, bounded retry, duplicates, append-only updated-review revisions, empty results, and partial failures. Browser refresh and backend restart preserve safe progress; incomplete work never appears complete.

**Tradeoff:** Reviews become locally useful before automated analysis exists.

**Status:** Complete.

## Slice 4 — Produce the first immutable report through Manual Codex

**Outcome:** Export a privacy-minimized Codex package, import valid structured results, compute authoritative Theme metrics, and store a minimal immutable Report Version.

**Blocked by:** None for implementation with explicit provisional thresholds. Production-quality acceptance still requires completion and human approval of the real-game evaluation baseline.

**Scope:** Analysis Provider contract, versioned schemas, Codex export/import, deterministic Theme Metrics, Report Repository, and minimal report presentation.

**Acceptance:** An end-to-end fixture creates a Report Version whose Themes trace through Opinion Points and validated exact excerpt spans to exact Review Revisions. Invalid schema, identifiers, scope, partial output, non-matching excerpts, prompt-injected instructions, and unsupported evidence are rejected. Counts, denominators, polarities, caps, design categories, Technical Themes, mixed reception, and provenance reproduce deterministically.

**Tradeoff:** The first complete analysis remains user-mediated so evidence integrity can be proven before provider automation.

**Status:** Implementation complete with explicit provisional thresholds and fixture-based verification. The user postponed bulk extraction, repeated consolidation, stability scoring, and threshold calibration; production-quality acceptance remains deferred, and prepared local packages remain available for a future approved bulk-inference path.

## Slice 5 — Explore an evidence-rich report

**Outcome:** Read positive and negative rankings, linked mixed reception, categories, representative excerpts, full evidence, playtime, helpfulness, and scope in the approved responsive interface.

**Blocked by:** None for fixture-backed implementation. Connected-browser verification and real-world analysis calibration remain acceptance gates.

**Scope:** Report/evidence API, Theme Metrics presentation, report navigation, accessibility, keyboard behavior, and responsive layout.

**Acceptance:** Every displayed metric reproduces from stored memberships. Component and accessibility verification covers non-color state communication, keyboard operation, reduced motion, and laptop/narrow layouts.

**Tradeoff:** Filters, refresh, and provider automation remain separate to keep report trust independently verifiable.

**Status:** Fixture-backed implementation complete. Connected-browser responsive and accessibility verification remains open, and real-world metrics remain provisional.

## Slice 6 — Export reports safely

**Outcome:** Export single-file HTML, structured JSON, and Theme/evidence CSV with identity-safe defaults and an explicit full-text option.

**Blocked by:** None for contract implementation. Slice 5 connected-browser acceptance remains open.

**Scope:** Versioned Export/Import contracts, privacy policy enforcement, report rendering, and export interface.

**Acceptance:** JSON re-imports only when every matching local Game Dataset and Review Revision is present and rejects missing or mismatched evidence clearly; HTML opens as one file while identifying externally loaded media; CSV preserves Theme/evidence relationships; default artifacts contain neither reviewer identity nor full review text; secret-leak and content-sanitization tests pass.

**Tradeoff:** PDF remains deferred.

**Status:** Complete with versioned HTTP downloads, strict local-evidence JSON re-import, privacy-safe defaults, and content-injection coverage.

## Slice 7 — Refresh into immutable report history

**Outcome:** Add new and updated reviews to an existing Game Dataset and create a new Report Version while older reports remain unchanged.

**Blocked by:** None for fixture-backed implementation. Real-world analysis calibration remains an acceptance gate.

**Scope:** incremental Review Ingestion, durable analysis checkpoints, relevant-corpus reanalysis, Report Repository history, and refresh/history interface.

**Acceptance:** Fixtures prove new-review growth, append-only edited-review revision and reprocessing, deduplication, cancellation, retry, and safe resume. Historical reports, exact source evidence, and metadata snapshots remain byte-for-byte unchanged.

**Tradeoff:** Normal refresh cannot detect deleted Steam reviews; explicit reconciliation remains later.

**Status:** Complete with append-only delta refresh, durable latest-revision reanalysis checkpoints, immutable metadata snapshots, newest-first history, and UI recovery controls.

## Slice 8 — Run automated Codex CLI analysis securely

**Outcome:** Detect an authenticated Codex CLI installation, explicitly run schema-constrained analysis, see external-cloud and quota disclosures, and complete a validated report without handling Codex credentials.

**Blocked by:** None. The user approved Codex CLI with `gpt-5.6-luna` and medium reasoning on 2026-08-12. Slice 4's deferred production-quality gate limits reliability claims but does not block implementation.

**Scope:** shared provider conformance, isolated Codex CLI execution, availability/authentication diagnostics, cancellation and bounded retries, quota disclosure, provider settings, diagnostics redaction, and no-fallback behavior.

**Acceptance:** Provider conformance and failure tests pass; invalid responses cannot create reports; the application never reads or stores Codex credentials; prompts and review text do not enter diagnostics; execution is ephemeral, read-only, cancellable, and isolated; no automatic provider/model fallback occurs; and the requested provider/model plus measured CLI usage are preserved in provenance when available.

**Tradeoff:** Provider breadth waits until one adapter has hardened the shared seam.

**Status:** Complete with shared validation, isolated CLI execution, bounded retry/cancellation, non-secret readiness diagnostics, durable exact-corpus Analysis Runs, immutable report creation, measured usage, and explicit UI start/progress/completion. Authenticated run `32f549e3-0d1d-4193-8c6d-a7e67c07da89` verified the live path with six exact Opinion Points and no unsupported single-review Themes. Local measurement found the application prompt under 1 KB and generated schema about 4.6 KB versus 15,744 reported input tokens, so the app retains strict validation, makes no quota-efficiency claim, and expects meaningful review scopes to amortize Codex CLI's fixed context. Explicit Codex model selection remains optional while only the pinned model is supported.

## Slice 9 — Add the remaining provider choices

**Outcome:** Explicitly run analysis through Ollama, OpenAI API, Anthropic Claude API, Google Gemini API, or a separately installed Claude Code CLI using the same report contract.

**Blocked by:** Slice 8 and cross-provider evaluation.

**Scope:** Ollama first, followed by evaluated hosted API or CLI adapters, Credential Store for API providers, cost estimation where prices are knowable, installed-model discovery, and provider selection.

**Acceptance:** Every adapter passes the shared contract tests. Ollama absence leaves metadata and review acquisition usable; the app never downloads a model or silently changes providers.

**Tradeoff:** Supporting multiple vendors increases ongoing compatibility and evaluation work.

**Status:** In progress. Local Ollama availability and installed-model discovery, schema-constrained streaming analysis, cancellation, exact validation, durable report integration, measured usage, and explicit provider/model selection are implemented. Qwen 3.5 4B failed the full-analysis trust boundary for all three pilot games, while 9B was stopped after about 20 minutes on the first six-review game because this machine is CPU-only. Neither is a reliable full-analysis default here; bounded extraction remains the sensible future local experiment. Hosted API and Claude Code adapters remain optional later work.

## Slice 10 — Filter report evidence

**Outcome:** Apply temporary Evidence Filters that narrow raw review evidence and immediately recalculate metrics for existing Themes without a model call.

**Blocked by:** None; Slices 5 and 7 are complete.

**Scope:** Theme Metrics, filter query contracts, report evidence APIs, and the filter interface.

**Acceptance:** Tests reproduce every denominator, rerank discovered Themes, hide zero-support Themes, mark below-threshold Themes, constrain raw reviews, excerpts, and drill-down to the filter, preserve report immutability, and reset unsaved filters.

**Tradeoff:** Filters cannot discover Themes that were absent from the original report; Slice 15 adds a fixed default cohort comparison with a bounded residual discovery audit.

**Status:** Complete with strict query validation, deterministic response-time metric recalculation, shared report/evidence restriction, below-threshold markers, and resettable non-persistent controls.

## Slice 11 — Complete game discovery and Steam overview

**Outcome:** Find games by name when configured and inspect comprehensive best-effort tags, regional pricing, descriptions, storefront model, grouped features, DLC, screenshots, and opt-in Steam-hosted trailers.

**Blocked by:** Slice 2 and validation of Steam storefront reliability and obligations.

**Scope:** keyed Game Catalog, unkeyed fallback search, Steam Metadata adapters, regional settings, metadata snapshots, feature overview, and media interface.

**Acceptance:** Catalog synchronization and fallback behavior pass fixtures; country/currency provenance is preserved; optional-source failures produce unknown states without blocking analysis; trailers never autoplay or download.

**Tradeoff:** Some storefront fields remain best-effort because Steam exposes no single complete documented endpoint.

**Status:** Complete with current keyed catalog synchronization, local-first search, replaceable unkeyed fallback, regional immutable storefront snapshots, grouped overview UI, safe media, and documented Steam obligations. Optional storefront sources remain explicitly best-effort.

## Slice 12 — Support Full import, reconciliation, and local data control

**Outcome:** Run resumable Full imports, explicitly reconcile deleted reviews, inspect storage, and safely delete reports, jobs, or complete Game Datasets.

**Blocked by:** Slices 3 and 7.

**Scope:** Full/reconciliation Review Ingestion, Job Runner, storage lifecycle, diagnostics/recovery, data-directory behavior, and destructive confirmations.

**Acceptance:** Large fixtures prove bounded pagination, resume, cancellation, reconciliation, and database integrity. Deletion cascades cannot orphan state and require explicit confirmation.

**Tradeoff:** Full-history operations remain expensive despite checkpointing and reuse.

**Status:** Complete with resumable terminating-cursor acquisition, non-destructive reconciliation, storage diagnostics, integrity checks, and exact-confirmation deletion controls. Data-directory relocation remains explicitly unavailable.

## Slice 13 — Publish the source-based MVP

**Outcome:** A new GitHub user can install the local web application, securely configure one analysis path, and maintain trustworthy reports without developer assistance.

**Blocked by:** Slice 21, Steam policy validation, accessibility and security gates, and copyright-holder confirmation.

**Scope:** integration and security verification, documentation, CI, MIT license, clean-install workflow, and source release.

**Acceptance:** A clean Windows environment completes installation, Full Import, Test Report, Main Report, extension, replacement, recovery, and export scenarios. Documentation covers Codex CLI, data paths, privacy, and recovery.

**Tradeoff:** Packaged releases and advertised macOS/Linux support remain outside this release gate.

**Status:** Blocked by Slice 21 and copyright-holder confirmation.

## Slice 14 — Package and validate distribution

**Outcome:** Windows users can run a packaged release without Node.js or Python development toolchains, while source portability is verified before other operating systems are advertised.

**Blocked by:** Slice 13 after the progressive workflow release gate passes.

**Scope:** Windows packaging of the established frontend/backend delivery path, migration/update guidance, clean-machine validation, and macOS/Linux source checks.

**Acceptance:** Clean Windows install, first run, analysis, restart recovery, export, update, data preservation, and uninstall checks pass. macOS/Linux support claims match recorded source validation.

**Tradeoff:** Packaged macOS and Linux releases remain deferred.

**Status:** Blocked.

## Slice 15 — Compare the oldest and newest available reviews

**Outcome:** Default reports compare issues in up to the 2,500 oldest and 2,500 newest eligible reviews from a completed full-history Steam import.

**Blocked by:** Slices 4, 8, and 12. Production-quality direction labels remain subject to the analysis-quality gate.

**Scope:** deterministic cohort selection, immutable cohort membership, resumable cached Opinion Point extraction, shared Theme consolidation, bounded residual cohort audits, deterministic comparison metrics, progress disclosure, and report presentation.

**Acceptance:** Tests prove non-overlapping chronological selection, smaller-corpus splitting, exact review completion and evidence validation, checkpoint reuse after failure, cohort-specific residual discovery, distinct-review denominators, percentage-point changes, immutable date ranges, and no additional model calls for comparison metrics. The report shows early and recent evidence without claiming that review changes prove causation or a software fix.

**Tradeoff:** A true oldest cohort requires a potentially long full-history Steam scan, and the middle of corpora larger than 5,000 reviews is intentionally excluded from model analysis.

**Status:** Implemented with resumable bounded extraction, deterministic canonical-subject consolidation, immutable cohort metrics, progress/retry controls, report presentation, and an explicitly incomplete 25-plus-25 Ollama pilot. Representative-game semantic calibration remains open.

This slice records superseded Version 2 behavior. Slices 16–21 replace its report model and user workflow.

## Slice 16 — Produce a standalone Test Report

**Outcome:** Create one saved aggregate Test Report from 25 oldest and 25 newest reviews without changing the Main Report.

**Blocked by:** None. Full Import, Codex CLI execution, durable analysis runs, and report persistence already exist.

**Scope:** Version 3 Theme candidate contracts, internal Theme memberships, deterministic aggregate metrics, one Test Report slot per game, API changes, and the test-report interface.

**Acceptance:** A completed Full Import can produce one 50-review Test Report in one provider call. The report uses non-overlapping oldest and newest cohorts, shows Themes at 5% support, caps each polarity at five, and replaces only the prior Test Report. Invalid provider output creates no report. The Test Report cannot be extended and never changes the Main Report.

**Tradeoff:** The Main Report continues to use the superseded implementation until Slice 17.

**Status:** Approved; execution frontier.

## Slice 17 — Produce the first Main Report

**Outcome:** Create the first aggregate Main Report from 500 oldest and 500 newest reviews.

**Blocked by:** Slice 16.

**Scope:** One Main Report slot per game, deterministic cohort selection, character-bounded map calls, Theme merging, retained candidates, durable batch checkpoints, aggregate metrics, report API, progress, and interface changes.

**Acceptance:** Tests prove exact non-overlapping selection, full-text input, a 250-review call ceiling, character-based packing, and replacement of oversized reviews with the next eligible unseen review. Restarts reuse validated batches. Candidates with at least 2% support in either cohort remain internal. Themes with at least 5% support in either cohort become visible. An empty visible report is valid.

**Tradeoff:** The Main Report cannot grow or reset through the interface until Slice 18.

**Status:** Approved; blocked by Slice 16.

## Slice 18 — Grow or replace the Main Report safely

**Outcome:** Extend the Main Report by up to 1,000 unseen reviews or replace it with a fresh 1,000-review analysis.

**Blocked by:** Slice 17.

**Scope:** Required Steam refresh, exact run reservations, cumulative Theme memberships, stable Theme definitions, candidate promotion, replacement runs, atomic report replacement, cancellation, retry, and restart recovery.

**Acceptance:** Extensions select up to 500 oldest and 500 newest unseen review identities after refresh. New reviews can enter the newest cohort. Edits to analyzed identities do not re-enter it. The final extension can contain fewer than 1,000 reviews. Concurrent runs cannot reserve the same scope. Validated batches survive retry and restart. Failed or cancelled work leaves the current Main Report unchanged. Successful work replaces it atomically. Replacement does not reuse the prior Main Report's analysis artifacts.

**Tradeoff:** Theme definitions stay fixed during extension. A poor taxonomy requires replacement.

**Status:** Approved; blocked by Slice 17.

## Slice 19 — Remove superseded report behavior

**Outcome:** Expose one Main Report and one Test Report per game without Version 2 report behavior.

**Blocked by:** Slice 18.

**Scope:** Catalog and report routes, report history, Opinion Points, excerpts, evidence APIs, Evidence Filters, categories, mixed reception, mechanic classifications, provider controls, legacy schemas, and obsolete adapters.

**Acceptance:** Removed report paths and controls are unavailable. The interface exposes only Test, create Main, Extend, Replace, export, cancel, and retry actions where valid. Version 2 reports cannot be read, imported, or extended. Backend and frontend checks pass after dead paths are deleted.

**Tradeoff:** Deleted Version 2 data and behavior cannot be restored through the application.

**Status:** Approved; blocked by Slice 18.

## Slice 20 — Export aggregate Version 3 reports

**Outcome:** Export and import the current aggregate report format without review evidence.

**Blocked by:** Slices 18 and 19.

**Scope:** Version 3 HTML, CSV, and JSON contracts, local JSON re-import, report-slot rules, sanitization, and download controls.

**Acceptance:** HTML and CSV contain aggregate Themes and cohort metrics. Default exports contain no review text, excerpt, or reviewer identity. JSON retains internal revision memberships for local validation and rejects import when required local revisions are absent. Import cannot create report history beyond the Main and Test slots.

**Tradeoff:** JSON remains tied to a compatible local Game Dataset and is not a portable data backup.

**Status:** Approved; blocked by Slices 18 and 19.

## Slice 21 — Verify the progressive workflow

**Outcome:** Verify the 50-review, 1,000-review, and 2,000-review workflows before release work resumes.

**Blocked by:** Slices 16–20.

**Scope:** Live Codex CLI runs, token and timing measurements, restart recovery, connected-browser checks, exports, automated checks, and operating documentation.

**Acceptance:** Verification proves Test Report isolation, first Main Report creation, one extension, replacement, truthful progress, recovery, and safe exports. Backend tests, frontend tests, type checking, and the production build pass. A human reviews the live Theme output for usefulness before release approval.

**Tradeoff:** Poor live speed, token use, or Theme quality can block release and require a design revision.

**Status:** Approved; blocked by Slices 16–20.

## Deferred

- Embedding-assisted semantic grouping
- Cross-game and cross-version comparison
- Automated translation and multilingual analysis
- PDF export
- Portable Report Archives containing the complete evidence required to restore reports on another installation
- Public multi-user hosting
- Additional review sources
- Manual Theme correction
- Statistical analytics dashboards
- Additional providers and user-selectable models
- Automatic splitting or merging of established Themes during extension

## Approval gates

- **Design:** satisfied; the progressive aggregate-report design is approved.
- **Plan:** satisfied; Slices 16–21 and their order are approved.
- **Tasks:** revise `TASKS.md` through `$create-implementation-tasks` before Slice 16 implementation.
- **Analysis quality:** review live Theme usefulness after Slice 21 verification.
- **Steam:** existing policy validation remains required for release.
- **Release:** complete Slice 21, confirm the MIT copyright holder, and approve the release candidate before Slice 13 publication.
