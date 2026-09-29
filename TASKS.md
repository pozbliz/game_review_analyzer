# Tasks

## 2026-09-29

### Standalone Test Report

- [x] Add failing Version 3 provider-contract tests.
- [x] Implement Theme candidates and internal Theme memberships.
- [x] Add failing aggregate metric tests.
- [x] Implement cohort metrics, thresholds, ranking, caps, and empty results.
- [x] Add repository tests for one independent Test Report slot.
- [x] Implement deterministic 25-oldest and 25-newest selection.
- [x] Connect one-call Codex execution with low reasoning.
- [x] Add API and frontend tests for creating and replacing Test Reports.
- [x] Verify invalid output never changes either report slot.

### First Main Report

- [ ] Add selection tests for 500 oldest and 500 newest reviews.
- [ ] Cover overlap removal, complete text, and oversized-review replacement.
- [ ] Add character-based packing tests with the 250-review limit.
- [ ] Implement map batching and validated checkpoints.
- [ ] Add merge tests for Themes, discarded candidates, and retained 2% candidates.
- [ ] Add repository tests for the single Main Report slot.
- [ ] Build the Main Report API, progress flow, and interface.
- [ ] Verify visible 5% thresholds and valid empty reports.

### Extend and Replace Main Report

- [ ] Add refresh and unseen-review selection tests.
- [ ] Cover new reviews, ignored edits, partial final extensions, and exact reservations.
- [ ] Add concurrency tests preventing duplicate scope reservations.
- [ ] Add extension merge tests for fixed Themes and candidate promotion.
- [ ] Add replacement tests that prohibit prior-analysis reuse.
- [ ] Implement atomic extension and replacement.
- [ ] Add cancellation, retry, restart, and checkpoint-reuse tests.
- [ ] Build Extend and Replace controls with current-report preservation.
- [ ] Verify failures never change the current Main Report.

### Remove Version 2 Behavior

- [ ] Add contract tests for one Main Report and one Test Report.
- [ ] Remove history, Opinion Points, excerpts, and evidence routes.
- [ ] Remove filters, categories, mixed reception, and direction labels.
- [ ] Remove unsupported provider and model controls.
- [ ] Remove unreachable Version 2 repositories and adapters.
- [ ] Add clean Version 3 schema and integrity tests.
- [ ] Update storage deletion for reports, runs, and checkpoints.
- [ ] Remove obsolete frontend views and tests.
- [ ] Run backend, frontend, type, and build checks.

### Version 3 Exports

- [ ] Add aggregate HTML, CSV, and JSON contract tests.
- [ ] Implement sanitized HTML and one-row-per-Theme CSV.
- [ ] Implement JSON with internal revision memberships.
- [ ] Reject imports with missing local revisions.
- [ ] Enforce Main and Test Report slot rules during import.
- [ ] Add privacy and content-injection tests.
- [ ] Update export and import controls.
- [ ] Verify exports contain no review text or reviewer identity.

### Progressive Workflow Verification

- [ ] Run the complete automated test and build suite.
- [ ] Verify restart recovery with reserved scopes and completed batches.
- [ ] Run live 50-review, 1,000-review, and 2,000-review Codex workflows.
- [ ] Record elapsed time and measured token use.
- [ ] Verify Test Report isolation, extension, and replacement in the browser.
- [ ] Verify keyboard, narrow-screen, reduced-motion, and non-color behavior.
- [ ] Update operating documentation for the new workflow.
- [ ] [HUMAN] Review live Theme usefulness before release work resumes.

## Simplify saved-report workflow

- [x] After game selection, load its saved report history and make **Open latest report** the primary action when history exists.
- [x] Show older reports with their creation date and provider/model; keep **Create new report** visually separate and secondary.
- [x] Create another report from the retained local Game Dataset without automatically repeating a Full review download.
- [x] Replace report-view **Dataset maintenance** controls with an explicit new-report flow outside the immutable report; keep low-level maintenance only where required for recovery or storage management.
- [x] Remove **Scope digest** from the visible report summary while retaining it in stored/exported provenance.
- [x] Investigate why the Minishoot Ollama runs produced zero Themes, define when an empty Theme result is legitimate, and prevent misleading empty reports without weakening evidence validation.
- [x] Add API and component coverage for saved-report discovery, dated history, retained-dataset reuse, and the simplified report header.
- [x] Restore the approved recent-report list before game selection.
- [x] Start analysis from a completed Game Dataset when no Report Version exists, without repeating the Full import.
- [x] Restore the latest active or resumable Analysis Run when its game is selected again.
- [x] Closed without execution; Progressive Workflow Verification replaces this Version 2 browser check.

## Oldest-versus-newest cohort comparison

- [x] Persist deterministic, non-overlapping cohorts containing up to the 2,500 oldest and 2,500 newest eligible reviews from a completed full-history import.
- [x] Extract and cache validated Opinion Points from the combined cohort scope in resumable bounded batches.
- [x] Consolidate every non-neutral Opinion Point into canonical shared Themes, including recurring cohort-specific issues.
- [x] Calculate early-versus-recent support, percentage-point change, date ranges, and conservative direction labels without additional model calls.
- [x] Expose acquisition prerequisites, durable progress, comparison metrics, and evidence from both cohorts in the report UI.
- [x] Verify the production UI in the connected browser.
- [x] Closed without execution; the approved design removes direction labels and Version 2 semantic grouping.

## 2026-09-27

### Specific design themes pilot

- [x] Exclude vague overall praise, criticism, and recommendations during Opinion Point extraction.
- [x] Invalidate cached extractions created under the prior generic extraction contract.
- [x] Consolidate pilot Opinion Points semantically into specific Themes with meaningful categories.
- [x] Preserve deterministic support metrics and exact evidence validation after semantic consolidation.
- [x] Run focused and full repository verification, then review the committed scope from `bcb9b6d`.
- [x] Closed without execution; the Standalone Test Report and final human gate replace this pilot.

- [x] Reduce the current Codex CLI default from medium to low reasoning.
- [x] Cache Codex CLI extraction progress every 10 reviews instead of waiting for the full pilot batch.
- [x] Add redacted per-attempt and per-stage timing telemetry for report creation.
- [x] Accept Steam metadata returned under an unexpected outer key when its sole nested AppID matches the requested game.
- [x] Cache Ollama extraction progress every 10 reviews instead of waiting for the full 50-review pilot batch.
- [x] Pace review imports and back off after Steam rate-limit responses without losing checkpoint progress.
- [x] Add an explicit 50-review Codex CLI pilot before the optional 5,000-review run.

## 2026-08-13

- [x] Widen the game catalog and add a user-controlled collapsible selection rail so storefront details can use the full content width.
- [x] Keep the preview pinned to the flexible grid column when the hidden selection panel leaves layout flow.
- [x] Replace the collapsible rail with a two-step full-width game-search and game-details flow.
- [x] Simplify storefront hierarchy with tag chips, explicit feature-status rows, normal-weight values, and fewer decorative labels.
- [x] Replace Steam language asterisks and footnotes with labeled full-audio and interface/subtitle chip groups.
- [x] Open Steam screenshots in a native large-image lightbox with navigation, close controls, and original-image access.
- [x] Closed without execution; Progressive Workflow Verification includes the current browser flow.

## 2026-08-10

- [x] Consolidate approved prototype surfaces around a shared forest-green, sage, neutral, and motion theme.
- [x] Establish shared production design tokens during application scaffolding.
- [x] [HUMAN] Approve the combined Catalog → Split → Timeline → Research workflow as the implementation-ready direction.
- [x] Record the approved prototype direction and update affected design documentation before scaffolding production code.

## 2026-08-11

- [x] Reorganize the application shell into the approved two-root repository structure with ownership-based backend and frontend boundaries.
- [x] [HUMAN] Remove the legacy placeholder `GameReviewAnalyzer.sln` and Rider metadata now that the project uses Python and TypeScript.
- [x] Establish frontend/backend directories, supported runtime versions, dependency manifests, and development commands.
- [x] Write failing backend health and configuration tests, then implement the minimal FastAPI application shell.
- [x] Write failing migration tests, then establish SQLite initialization and migration tooling.
- [x] Write failing frontend shell and backend-health tests, then implement the minimal React/Vite application shell.
- [x] Establish typed frontend/backend API communication and contract verification.
- [x] Write a failing production-serving test, then serve compiled frontend assets through FastAPI.
- [x] Add backend tests, frontend tests, type checking, production builds, and migration checks to CI.
- [x] Verify a clean local installation and document the development workflow.
- [x] Correct the stale Game Dataset schema-version assertion after the review/job migration.

Active implementation checklist derived from the approved `PLAN.md`. Tasks remain in plan-slice order. Mark decisions or editor work requiring user input with `[HUMAN]`.

## 2026-08-12

### Continuation checkpoint — 2026-08-12

- Last production implementation: temporary Evidence Filters recalculate existing Theme metrics and restrict evidence without persistence or model calls.
- Last complete local release gate: locked restores, 114 backend tests, 21 frontend tests, production build, tracked-secret scan, Python and npm advisory scans, and production HTTP smoke passed. GitHub Actions has no recorded runs; connected-browser acceptance could not run because no browser instance was connected.
- Current Codex path: authenticated `gpt-5.6-luna` with low reasoning; the application does not read or store Codex credentials, and the live durable report path is verified.
- Current environment check: Codex CLI `0.147.0` is authenticated through ChatGPT in the normal user context. Sandboxed status checks cannot see the external credential store and may still report `Not logged in`.
- Current environment check: Ollama 0.32.8 is running with Qwen 3.5 4B and 9B installed; Ollama reports CPU-only inference and Windows exposes 15.4 GB visible memory.
- [x] [HUMAN] Install and start Ollama without downloading a model automatically.
- [x] [HUMAN] Approve and download Qwen 3.5 4B and 9B for local benchmarking.
- Slice 8 live verification is complete. A one-attempt diagnostic exposed missing prompt guidance for the two-review Theme-support invariant; after adding it, run `32f549e3-0d1d-4193-8c6d-a7e67c07da89` created and exposed an immutable report for one approved Hades II review. The full contract has high fixed overhead: 15,744 input and 563 output tokens for this tiny scope.
- Ollama implementation and the installed-Qwen benchmark are complete; add hosted API adapters only when requested. Slice 10 retains deterministic Evidence Filters without model calls, while Cohort Analysis and its minimum-size calibration are deferred; do not resume the 60-batch stability experiment unless the user explicitly approves a bulk-inference path.
- Remaining human gates are connected-browser accessibility/responsive verification, the deferred production-quality baseline, MIT copyright-holder confirmation, and source/package release approval.

## 2026-08-09

### Completed requirements and design decisions

- [x] Consolidate the completed requirements interview into the authoritative design.
- [x] Confirm local-web MVP distribution through a public GitHub repository.
- [x] Confirm React/TypeScript/Vite plus FastAPI/Python and SQLite.
- [x] Select MIT as the repository license.
- [x] Select Windows as the first packaged-release target while preserving source portability.
- [x] Confirm provider-neutral analysis using Ollama, OpenAI API, Anthropic Claude API, Google Gemini API, and manual Codex packages.
- [x] Confirm that the app never downloads AI models and that embeddings are deferred.
- [x] Confirm secure credential handling and explicit processing-location labels.
- [x] Confirm immutable single-game reports, durable jobs, incremental refresh, and historical versions.
- [x] Confirm comprehensive best-effort Steam metadata, features, media, and regional price snapshots.
- [x] Confirm evidence-only reports with up to 10 positive and 10 negative design Themes.
- [x] Defer cross-game comparison and detailed visual decisions until after the core single-game workflow.
- [x] Resolve review-history, export, Technical Theme, Evidence Filter, manual Codex disclosure, metric, credential, and untrusted-content design inconsistencies.
- [x] Approve the strategic implementation plan for concrete task expansion.

### Slice 0 — Approve the core workflow prototype

**Status:** Approved direction. Connected-browser responsive, accessibility, interaction, and console verification remains open.

- [x] Prepare realistic synthetic content for report Themes, mixed reception, Technical Themes, evidence, filtering, metadata identity, and report history.
- [x] Build isolated Research Desk, Editorial Brief, and Evidence Canvas report-exploration prototypes behind the standard visual picker.
- [x] Verify report variant switching, replay, filters, Theme selection, evidence overlay, history, Escape dismissal, and console output in a connected browser.
- [x] Review all report-exploration variants at laptop and narrow viewport widths with reduced-motion and non-color checks.
- [x] Start a new conversation without quitting Codex after restoring `args = ["--disable-sandbox"]`, then open the built-in Browser at the app URL and retry connected-browser acceptance; Codex 26.803.81509 regenerates the plugin-owned argument on full app launch.
- [x] Closed without execution; Progressive Workflow Verification covers the replacement interface.
- [x] [HUMAN] Select the Research overview with lightweight inline Theme detail accordions and no separate inspector or drawer.
- [x] Build Catalog, Guided, and Library game-selection and identity-confirmation prototypes behind the standard visual picker.
- [x] Integrate compact recent and existing-report access into the Catalog preview without replacing game identity fields.
- [x] Make the latest report the primary Catalog action, add lightweight report history, and standardize the creation action as `Create report`.
- [x] Increase latest-report visual emphasis and restore `Create report` as the primary creation CTA.
- [x] Verify game-selection variant switching, name/AppID search, result filtering, identity confirmation, library actions, console output, and responsive layouts in a connected browser.
- [x] [HUMAN] Select the Catalog direction with Library-style report access integrated into the preview panel.
- [x] Build at least three genuinely different analysis-configuration and processing-disclosure prototypes.
- [x] [HUMAN] Select the Split analysis-configuration direction with side-by-side configuration and processing disclosure.
- [x] Build at least three genuinely different durable progress, cancellation, retry, and resume prototypes.
- [x] [HUMAN] Select the Timeline durable-progress direction with checkpointed stage visibility and calm recovery controls.
- [x] Review the combined approved workflow at laptop and narrow viewport widths.
- [x] Closed without execution; Progressive Workflow Verification covers the replacement interface.
- [x] [HUMAN] Approve the combined workflow as an implementation-ready direction.
- [x] Record the approved prototype direction and update affected design documentation before scaffolding production code.

### Slice 1 — Run the local application shell

**Status:** Complete.

- [x] Establish frontend/backend directories, supported runtime versions, dependency manifests, and development commands.
- [x] Write failing backend health and configuration tests, then implement the minimal FastAPI application shell.
- [x] Write failing migration tests, then establish SQLite initialization and migration tooling.
- [x] Write failing frontend shell and backend-health tests, then implement the minimal React/Vite application shell.
- [x] Establish typed frontend/backend API communication and contract verification.
- [x] Write a failing production-serving test, then serve compiled frontend assets through FastAPI.
- [x] Add backend tests, frontend tests, type checking, production builds, and migration checks to CI.
- [x] Establish reproducible dependency installation using committed lock data and frozen CI installs.
- [x] Resolve or explicitly constrain the FastAPI/Starlette test-client deprecation warning.
- [x] Verify a clean local installation and document the development workflow.

### Slice 2 — Preview a game from its AppID

**Status:** Complete.

- [x] Create valid, invalid, missing, malformed, and partially available Steam metadata fixtures.
- [x] Write normalized Steam Metadata contract and explicit unknown-state tests.
- [x] Implement the replaceable Steam Metadata adapter against the tested contract.
- [x] Write persistence tests, then store the initial Game Dataset and metadata preview.
- [x] Write API tests, then expose AppID validation and preview behavior.
- [x] Write component tests, then build the game-confirmation interface.
- [x] Verify that optional metadata failures do not block a valid preview.

### Slice 3 — Persist a durable Quick review import

**Status:** Complete.

- [x] Write migration and integrity tests for reviews, immutable Review Revisions, Analysis Jobs, and checkpoints.
- [x] Create fixtures and failing tests for pagination, cursor encoding, eligibility, pacing, bounded retries, cursor repetition, and source exhaustion.
- [x] Implement the paginated Steam Review Ingestion adapter.
- [x] Write failing deduplication and edited-review tests, then implement append-only Review Revision behavior.
- [x] Write failing Job Runner state-transition tests, then implement checkpoints, cancellation, retry, and restart recovery.
- [x] Write API tests, then expose import progress, cancellation, and retry behavior.
- [x] Write component tests, then build the analysis-setup and progress interface.
- [x] Verify browser-refresh and backend-restart recovery with an interrupted Quick import.

### Slice 4 — Produce the first immutable report through Manual Codex

**Blocked by:** None for implementation with explicit provisional thresholds. Production-quality acceptance remains blocked by the deferred analysis-quality approval gate.

- [x] [HUMAN] Approve Hades II, Stardew Valley, and Cyberpunk 2077 as the real-game evaluation corpus.
- [x] Keep raw review text and reviewed annotations local under the gitignored `evaluation-data/` directory.
- [x] [HUMAN] Confirm the user will independently review candidate gold labels.
- [x] Build a local browser-based label-review tool with button corrections, keyboard shortcuts, autosave, progress, and reviewed-JSON export.
- [x] Fix live Steam metadata and review requests to pass `urllib` timeouts by keyword.
- [x] Skip blank recommendation-only Steam entries that contain no analyzable review text.
- [x] Write balanced-subset selection tests and add the repeatable local evaluation-corpus acquisition script.
- [x] Download the approved 60-review local pool and prepare an 18-review, 38-Opinion-Point pilot candidate round.
- [x] [HUMAN] Visually verify the local gold-label review tool with the first real candidate corpus.
- [x] Adjudicate all 38 Opinion Point candidates and record honest pilot precision and sentiment results.
- [x] Extend the local labeler with reusable button-only quality judgment rounds.
- [x] Prepare the 35-item pilot follow-up for completeness, grouping, summaries, opposing links, and review classification.
- [x] [HUMAN] Complete and export the pilot quality follow-up round.
- [x] Define the provider-independent evaluation format, scoring rubric, and synthetic conformance fixture without treating it as calibration evidence.

- [x] Define the labeled evaluation-set format and create representative samples spanning several games and review styles.
- [x] [HUMAN] Complete and export the four-item missing-Opinion-Point correction round.
- [x] Add and complete a missing-Opinion-Point review round before calculating extraction recall.
- [x] Evaluate Opinion Point extraction, Opinion Sentiment, neutral exclusion, paraphrase grouping, categories, summary faithfulness, and exact excerpts.
- [x] Evaluate opposing-Theme linkage and review-level liked/disliked/mixed classification.
- [x] [HUMAN] Resolve the Slice 4 ordering cycle: the stability experiment requires provider runs, while provider implementation is blocked by baseline approval.
- [x] Download and validate the natural-distribution 5,000-review stability corpus for each approved game.
- [x] [HUMAN] Approve transmitting the 15,000-review stability corpus through repeated Codex CLI runs and pin `gpt-5.6-luna` with medium reasoning.
- [x] Prepare and validate contiguous, interleaved, and hashed full-corpus inputs plus the strict stability-result schema.
- [x] Complete the Luna-medium synthetic conformance run and first valid 5,000-review stability run.
- [x] [HUMAN] Choose and validate targeted evidence-only repair after three Hades II Luna outputs failed exact-evidence validation.
- [x] [HUMAN] Stop monolithic 5,000-review discovery runs and approve bounded extraction plus deterministic-support consolidation.
- [x] Define and validate an Opinion Point-only batch contract and prepare 60 isolated 250-review packages covering the 15,000-review corpus.
- [x] [HUMAN] Postpone bulk inference after the 250-review Codex CLI pilot exceeded five minutes and failed exact-excerpt validation.
- [x] Closed without execution; Version 3 removes Opinion Point extraction and this stability workflow.
- [x] Closed without execution; Version 3 removes Opinion Point consolidation.
- [x] Closed without execution; progressive 1,000-review verification replaces this experiment.
- [x] Closed without execution; Version 3 defines fixed candidate and visibility thresholds.
- [x] Evaluate exact-excerpt validation and resistance to instructions embedded in review text.
- [x] Closed without execution; the Version 3 live Theme review is the approved quality gate.
- [x] Write failing tests for versioned Analysis Provider request and result schemas.
- [x] Write privacy and disclosure tests, then implement privacy-minimized Manual Codex package export.
- [x] Write import rejection tests for malformed, partial, mismatched, fabricated, non-matching, and prompt-injected results.
- [x] Implement strict Manual Codex result validation against exact Review Revisions and source spans.
- [x] Write failing deterministic Theme Metrics tests, then implement polarity, denominators, caps, categories, Technical Themes, and mixed reception.
- [x] Write repository tests, then implement immutable Report Versions bound to exact Review Revisions and provenance.
- [x] Complete a fixture-driven Codex export, import, metrics, and minimal-report scenario.

### Slice 5 — Explore an evidence-rich report

**Blocked by:** None for fixture-backed implementation. Connected-browser verification and real-world analysis calibration remain acceptance gates.

- [x] Write report and evidence API contract tests.
- [x] Write component tests, then build positive, negative, and secondary Technical Theme presentations.
- [x] Write interaction tests, then build linked mixed-reception and category exploration.
- [x] Write evidence-navigation tests, then build representative excerpt and full-review drill-down.
- [x] Display exact scope, provenance, review context, and metric denominators.
- [x] Closed without execution; Progressive Workflow Verification covers the replacement interface.
- [x] Verify every displayed metric against stored Theme memberships.

### Slice 6 — Export reports safely

**Blocked by:** None for contract implementation. Slice 5 connected-browser acceptance remains open.

- [x] Define versioned single-file HTML, JSON, and CSV contracts and write failing contract tests.
- [x] Write missing/mismatched-evidence tests, then implement JSON re-import against matching local Game Datasets and Review Revisions.
- [x] Write relationship-preservation tests, then implement Theme/evidence CSV export.
- [x] Write rendering tests, then implement sanitized single-file HTML with explicit external-media behavior.
- [x] Add explicit full-review-text options with identity and privacy warnings.
- [x] Add secret, reviewer-identity, unsafe-markup, unsafe-link, and spreadsheet-formula injection tests.
- [x] Complete export and JSON re-import integration verification.

### Slice 7 — Refresh into immutable report history

**Blocked by:** None for fixture-backed implementation. Real-world analysis calibration remains an acceptance gate.

- [x] Write delta-ingestion tests for new, unchanged, and edited Steam reviews.
- [x] Implement append-only refresh while preserving exact historical Review Revisions.
- [x] Write failing checkpoint tests, then implement durable refresh and relevant-corpus reanalysis.
- [x] Write repository tests for immutable history and newest-Report-Version selection.
- [x] Write component tests, then build refresh controls, report history, and failure recovery.
- [x] Verify that refresh leaves historical reports, source evidence, and metadata snapshots byte-for-byte unchanged.

### Slice 8 — Run automated Codex CLI analysis securely

**Blocked by:** None. Deferred Slice 4 calibration limits quality claims but does not block implementation.

- [x] Evaluate candidate cloud providers for quality, cost, schema reliability, model identification, and no-embedding behavior.
- [x] [HUMAN] Approve automated Codex CLI with `gpt-5.6-luna` and medium reasoning as the first provider path.
- [x] Create a shared provider conformance suite with success, malformed-output, retry, cancellation, and no-fallback cases.
- [x] Write CLI-runner tests, then implement isolated, ephemeral, read-only execution with availability checks and cancellation.
- [x] [HUMAN] Log in through Codex CLI before the first live end-to-end provider run.
- [x] Implement Codex CLI against the shared Analysis Provider contract.
- [x] Integrate Codex CLI into a durable Analysis Run that creates an immutable validated Report Version.
- [x] Write usage-disclosure tests, then present measured CLI token use when available and explicit quota uncertainty instead of a dollar estimate.
- [x] Write component tests, then build explicit start, durable progress, cancellation, completion, and external-cloud disclosure.
- [x] Closed without implementation; Version 3 defers model controls.
- [x] Verify through automated tests that the application never reads or stores Codex credentials and that prompts, review text, and CLI output do not enter diagnostics.
- [x] Verify no fallback and exact provider/model provenance through the automated seam.
- [x] Complete one live authenticated end-to-end run and inspect the resulting report. Run `32f549e3-0d1d-4193-8c6d-a7e67c07da89` completed in one attempt with six exact Opinion Points, a mixed review classification, no unsupported single-review Themes, and an immutable Report Version.
- [x] Measure the full-contract fixed overhead and avoid advertising Codex CLI as quota-efficient: the smallest live run used 15,744 input tokens, while the application prompt was under 1 KB and the generated schema about 4.6 KB, so weakening the strict contract would not materially address CLI overhead.

### Slice 9 — Add the remaining provider choices

**Blocked by:** No implementation blocker. Live model evaluation requires a user-installed Ollama runtime and compatible models.

- [x] Closed without implementation; Version 3 supports only Codex CLI.
- [x] Implement Ollama as the next provider using its local structured-output API.
- [x] Benchmark installed Qwen 3.5 9B and 4B models against the human-reviewed pilot; record 4B contract failures and 9B CPU infeasibility.
- [x] Closed without implementation; Version 3 removes Opinion Point extraction and defers local providers.
- [x] Closed without implementation; Version 3 defers additional providers.
- [x] Closed without implementation; Version 3 has no API-provider credential path.
- [x] Closed without implementation; Version 3 has no paid API-provider estimator.
- [x] Write discovery fixtures and tests, then implement Ollama availability and installed-model detection.
- [x] Verify the application never initiates an Ollama model installation or download.
- [x] Add compatible-model guidance and copyable commands that run only through explicit user action outside the app.
- [x] Test explicit provider/model selection and no-fallback behavior across the implemented Codex CLI and Ollama adapters.
- [x] Closed without execution; Progressive Workflow Verification measures the supported Codex path.

### Slice 10 — Filter report evidence

**Blocked by:** None; Slices 5 and 7 are complete.

- [x] [HUMAN] Retain deterministic Evidence Filters in the source MVP and defer Cohort Analysis plus minimum-size calibration.
- [x] Define the Evidence Filter query contract and write contract tests.
- [x] Write deterministic Evidence Filter metric and denominator tests.
- [x] Implement reranking, zero-support hiding, below-threshold markers, and raw review/evidence restriction without new Theme discovery or model calls.
- [x] Write component tests, then build resettable Evidence Filter controls.
- [x] Verify that Evidence Filters never discover Themes, persist automatically, or invoke an analysis provider.

### Slice 11 — Complete game discovery and Steam overview

**Blocked by:** Slice 2 plus validated Steam storefront reliability and obligations.

**Status:** Complete.

- [x] Validate and document Steam retention, attribution, and request-rate expectations before release.
- [x] Create fixtures for catalog search, fallback search, tags, descriptions, regional prices, features, DLC, editions, packages, and media.
- [x] Write synchronization tests, then implement the keyed Steam Game Catalog.
- [x] Write fallback behavior tests, then implement replaceable unkeyed game search.
- [x] Expand normalized Steam Metadata Snapshots with source-status and missing-field provenance.
- [x] Write regional-setting tests, then implement visible and configurable country/currency behavior without silent conversion.
- [x] Write component tests, then build grouped feature, storefront, DLC, description, and media views.
- [x] Verify unknown states, content sanitization, safe links, and explicit non-autoplay trailer behavior.

### Slice 12 — Support Full import, reconciliation, and local data control

**Blocked by:** Slices 3 and 7.

**Status:** Complete.

- [x] Write large-corpus Full import tests covering bounded pagination, checkpoints, cancellation, retry, and resume.
- [x] Implement resumable Full review acquisition.
- [x] Write reconciliation tests, then implement explicit deletion detection without mutating historical evidence.
- [x] Write storage diagnostics tests, then expose storage use and the current application-data location.
- [x] Write deletion-cascade tests for Report Versions, incomplete jobs, and complete Game Datasets.
- [x] Build explicit destructive confirmations and recovery guidance.
- [x] Run database-integrity and orphan-detection verification after interruption and deletion scenarios.
- [x] Document data-directory relocation as unavailable until the deferred operation is designed.

### Slice 13 — Publish the source-based MVP

**Blocked by:** Slices 5–12, Steam-policy validation, accessibility/security gates, copyright-holder confirmation, and release approval.

- [ ] Complete Steam-policy, security, privacy, accessibility, and analysis-quality release gates.
- [x] Add and test a secret-free `.env.example`.
- [ ] [HUMAN] Confirm the copyright holder for the MIT license.
- [ ] Add the MIT license and source-release metadata.
- [x] Write source installation, provider, Ollama, Codex, storage, privacy, export, update, and recovery documentation.
- [ ] Run a clean-Windows source installation through Full Import, Test Report, Main Report, extension, replacement, recovery, and export.
- [ ] Run full CI, dependency, secret-leak, sanitization, accessibility, and release-artifact checks.
- [ ] [HUMAN] Review and approve the source-release candidate.

### Slice 14 — Package and validate distribution

**Blocked by:** Slice 13.

- [ ] Evaluate Windows packaging options against startup, migration, signing, update, and clean-machine requirements.
- [ ] Record the selected packaging design and verification strategy.
- [ ] Build a Windows release containing the compiled frontend and backend runtime without development-tool dependencies.
- [ ] Test first run, restart recovery, migrations, update, export, and data preservation.
- [ ] [HUMAN] Confirm expected application-data retention after uninstall.
- [ ] Validate installation and uninstall behavior on a clean Windows environment.
- [ ] Validate source-based operation on macOS and Linux before advertising support.
- [ ] Publish only operating-system support claims demonstrated by recorded checks.
- [ ] [HUMAN] Review and approve the packaged-release candidate.

### Deferred work

**Blocked by:** Promotion through design and implementation planning after the single-game MVP is reliable.

- [ ] Explore embeddings as an optional semantic-grouping enhancement.
- [x] Closed without implementation; Version 3 reports include fixed oldest and newest cohorts.
- [ ] Add cross-game and cross-version comparison.
- [ ] Add automated translation and multilingual analysis with original-text provenance.
- [ ] Add PDF export.
- [ ] Add a privacy-warned Portable Report Archive for restoring complete reports without an existing local Game Dataset.
- [ ] Evaluate public multi-user hosting as a separate product phase.
- [ ] Evaluate additional review sources after the Steam workflow is mature.
- [ ] Add manual Theme correction tools.
- [ ] Add statistical analytics dashboards.
- [x] Closed without implementation; Version 3 uses Replace Report instead of immutable report history.
