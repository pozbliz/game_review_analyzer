# Tasks

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
- [ ] Verify report variant switching, replay, filters, Theme selection, evidence overlay, history, keyboard behavior, and console output in a connected browser.
- [ ] Review all report-exploration variants at laptop and narrow viewport widths with reduced-motion and non-color checks.
- [x] [HUMAN] Select the Research overview with lightweight inline Theme detail accordions and no separate inspector or drawer.
- [x] Build Catalog, Guided, and Library game-selection and identity-confirmation prototypes behind the standard visual picker.
- [x] Integrate compact recent and existing-report access into the Catalog preview without replacing game identity fields.
- [x] Make the latest report the primary Catalog action, add lightweight report history, and standardize the creation action as `Create report`.
- [x] Increase latest-report visual emphasis and restore `Create report` as the primary creation CTA.
- [ ] Verify game-selection variant switching, name/AppID search, result filtering, identity confirmation, library actions, keyboard behavior, console output, and responsive layouts in a connected browser.
- [x] [HUMAN] Select the Catalog direction with Library-style report access integrated into the preview panel.
- [x] Build at least three genuinely different analysis-configuration and processing-disclosure prototypes.
- [x] [HUMAN] Select the Split analysis-configuration direction with side-by-side configuration and processing disclosure.
- [x] Build at least three genuinely different durable progress, cancellation, retry, and resume prototypes.
- [x] [HUMAN] Select the Timeline durable-progress direction with checkpointed stage visibility and calm recovery controls.
- [ ] Review the combined approved workflow at laptop and narrow viewport widths.
- [ ] Review keyboard access, non-color communication, reduced motion, and information hierarchy across the combined workflow.
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

**Blocked by:** Completion and human review of the real-game evaluation corpus, then the analysis-quality approval gate.

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
- [ ] [HUMAN] Approve transmitting the 15,000-review stability corpus through repeated Codex CLI runs and pin the evaluation model.
- [ ] Measure whether the latest 5,000 eligible reviews produce stable headline Themes across representative games.
- [ ] Calibrate provisional absolute support, percentage support, cluster-coherence, and Technical Theme thresholds.
- [ ] Evaluate exact-excerpt validation and resistance to instructions embedded in review text.
- [ ] [HUMAN] Approve the evaluation baseline and provisional reliability thresholds.
- [x] Write failing tests for versioned Analysis Provider request and result schemas.
- [x] Write privacy and disclosure tests, then implement privacy-minimized Manual Codex package export.
- [x] Write import rejection tests for malformed, partial, mismatched, fabricated, non-matching, and prompt-injected results.
- [x] Implement strict Manual Codex result validation against exact Review Revisions and source spans.
- [ ] Write failing deterministic Theme Metrics tests, then implement polarity, denominators, caps, categories, Technical Themes, and mixed reception.
- [ ] Write repository tests, then implement immutable Report Versions bound to exact Review Revisions and provenance.
- [ ] Complete a fixture-driven Codex export, import, metrics, and minimal-report scenario.

### Slice 5 — Explore an evidence-rich report

**Blocked by:** Slices 0 and 4.

- [ ] Write report and evidence API contract tests.
- [ ] Write component tests, then build positive, negative, and secondary Technical Theme presentations.
- [ ] Write interaction tests, then build linked mixed-reception and category exploration.
- [ ] Write evidence-navigation tests, then build representative excerpt and full-review drill-down.
- [ ] Display exact scope, provenance, review context, and metric denominators.
- [ ] Add keyboard, screen-reader, non-color, reduced-motion, laptop, and narrow-width verification.
- [ ] Verify every displayed metric against stored Theme memberships.

### Slice 6 — Export reports safely

**Blocked by:** Slice 5.

- [ ] Define versioned single-file HTML, JSON, and CSV contracts and write failing contract tests.
- [ ] Write missing/mismatched-evidence tests, then implement JSON re-import against matching local Game Datasets and Review Revisions.
- [ ] Write relationship-preservation tests, then implement Theme/evidence CSV export.
- [ ] Write rendering tests, then implement sanitized single-file HTML with explicit external-media behavior.
- [ ] Add explicit full-review-text options with identity and privacy warnings.
- [ ] Add secret, reviewer-identity, unsafe-markup, unsafe-link, and spreadsheet-formula injection tests.
- [ ] Complete export and JSON re-import integration verification.

### Slice 7 — Refresh into immutable report history

**Blocked by:** Slices 3 and 4.

- [ ] Write delta-ingestion tests for new, unchanged, and edited Steam reviews.
- [ ] Implement append-only refresh while preserving exact historical Review Revisions.
- [ ] Write failing checkpoint tests, then implement durable refresh and relevant-corpus reanalysis.
- [ ] Write repository tests for immutable history and newest-Report-Version selection.
- [ ] Write component tests, then build refresh controls, report history, and failure recovery.
- [ ] Verify that refresh leaves historical reports, source evidence, and metadata snapshots byte-for-byte unchanged.

### Slice 8 — Run one automated cloud provider securely

**Blocked by:** Slice 4 and the provider-quality approval gate.

- [ ] Evaluate candidate cloud providers for quality, cost, schema reliability, model identification, and no-embedding behavior.
- [ ] [HUMAN] Approve the first automated cloud provider.
- [ ] Create a shared provider conformance suite with success, malformed-output, retry, cancellation, and no-fallback cases.
- [ ] Write Credential Store contract tests, then implement session, environment, and operating-system-vault adapters.
- [ ] Implement the approved provider against the shared Analysis Provider contract.
- [ ] Write estimator tests, then implement pipeline-wide input, output, repeated-pass, retry-risk, and pricing-age cost estimates.
- [ ] Write component tests, then build provider settings, cloud disclosure, explicit model selection, and cost presentation.
- [ ] Verify secrets never enter SQLite, logs, exports, URLs, frontend assets, backend responses, or diagnostics and that credential submission is not logged.
- [ ] Verify no fallback and exact provider/model provenance end to end.

### Slice 9 — Add the remaining provider choices

**Blocked by:** Slice 8 and cross-provider evaluation readiness.

- [ ] Apply the shared conformance suite to every remaining provider adapter.
- [ ] Implement the remaining OpenAI, Anthropic Claude, and Google Gemini adapters not completed in Slice 8.
- [ ] Write discovery fixtures and tests, then implement Ollama availability and installed-model detection.
- [ ] Verify the application never initiates an Ollama model installation or download.
- [ ] Add compatible-model guidance and copyable commands that run only through explicit user action outside the app.
- [ ] Test explicit provider/model selection and no-fallback behavior across all adapters.
- [ ] Evaluate no-embedding quality, token use, and pipeline-wide approximate cost across the initial providers.

### Slice 10 — Filter evidence and create Cohort Analyses

**Blocked by:** Slices 5 and 7 plus calibrated minimum Review Cohort sizes.

- [ ] Define the versioned Review Cohort scope contract and write contract tests.
- [ ] Calibrate and record minimum Review Cohort sizes.
- [ ] Write deterministic Evidence Filter metric and denominator tests.
- [ ] Implement reranking, zero-support hiding, below-threshold markers, and evidence restriction without new Theme discovery.
- [ ] Write component tests, then build resettable Evidence Filter controls.
- [ ] Write failing minimum-size and scope tests, then implement Cohort Analysis validation.
- [ ] Implement Cohort Analysis jobs and immutable, explicitly scoped Report Versions.
- [ ] Write interaction tests, then build clearly differentiated filter and Cohort Analysis actions.
- [ ] Verify that Evidence Filters never discover Themes and Cohort Analyses can discover cohort-specific Themes.

### Slice 11 — Complete game discovery and Steam overview

**Blocked by:** Slice 2 plus validated Steam storefront reliability and obligations.

- [ ] Validate and document Steam retention, attribution, and request-rate expectations before release.
- [ ] Create fixtures for catalog search, fallback search, tags, descriptions, regional prices, features, DLC, editions, packages, and media.
- [ ] Write synchronization tests, then implement the keyed Steam Game Catalog.
- [ ] Write fallback behavior tests, then implement replaceable unkeyed game search.
- [ ] Expand normalized Steam Metadata Snapshots with source-status and missing-field provenance.
- [ ] Write regional-setting tests, then implement visible and configurable country/currency behavior without silent conversion.
- [ ] Write component tests, then build grouped feature, storefront, DLC, description, and media views.
- [ ] Verify unknown states, content sanitization, safe links, and explicit non-autoplay trailer behavior.

### Slice 12 — Support Full import, reconciliation, and local data control

**Blocked by:** Slices 3 and 7.

- [ ] Write large-corpus Full import tests covering bounded pagination, checkpoints, cancellation, retry, and resume.
- [ ] Implement resumable Full review acquisition.
- [ ] Write reconciliation tests, then implement explicit deletion detection without mutating historical evidence.
- [ ] Write storage diagnostics tests, then expose storage use and the current application-data location.
- [ ] Write deletion-cascade tests for Report Versions, incomplete jobs, and complete Game Datasets.
- [ ] Build explicit destructive confirmations and recovery guidance.
- [ ] Run database-integrity and orphan-detection verification after interruption and deletion scenarios.
- [ ] Document data-directory relocation as unavailable until the deferred operation is designed.

### Slice 13 — Publish the source-based MVP

**Blocked by:** Slices 5–12, Steam-policy validation, accessibility/security gates, copyright-holder confirmation, and release approval.

- [ ] Complete Steam-policy, security, privacy, accessibility, and analysis-quality release gates.
- [ ] Add and test a secret-free `.env.example`.
- [ ] [HUMAN] Confirm the copyright holder for the MIT license.
- [ ] Add the MIT license and source-release metadata.
- [ ] Write source installation, provider, Ollama, Codex, storage, privacy, export, update, and recovery documentation.
- [ ] Run a clean-Windows source installation through representative AppID, Codex/cloud, refresh, filtering, history, and export workflows.
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
- [ ] Add cross-game and cross-version comparison.
- [ ] Add automated translation and multilingual analysis with original-text provenance.
- [ ] Add PDF export.
- [ ] Add a privacy-warned Portable Report Archive for restoring complete reports without an existing local Game Dataset.
- [ ] Evaluate public multi-user hosting as a separate product phase.
- [ ] Evaluate additional review sources after the Steam workflow is mature.
- [ ] Add manual Theme correction tools.
- [ ] Add statistical analytics dashboards.
- [ ] Decide how future taxonomy revisions are exposed while historical Report Versions remain immutable.
