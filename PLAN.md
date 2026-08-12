# Game Review Analyzer — Implementation Plan

## Status

The product design and this strategic plan are approved. Slices 1–7, 11, and 12 are implemented, while Slice 4 retains a deferred production-quality calibration gate. Slice 8 is active with Codex CLI approved as the first automated provider path, Slice 9 follows with Ollama first, and calibration blocks Slice 10; the concrete, dependency-ordered action checklist is maintained in `TASKS.md`.

## Durable verification seams

Implementation should preserve these stable behavioral boundaries:

- versioned HTTP API contracts between the backend and frontend
- Steam Game Catalog and Steam Metadata adapters
- Review Ingestion with append-only Review Revisions
- durable Job Runner
- provider-neutral Analysis Provider
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

**Status:** Implementation complete with shared validation, isolated CLI execution, bounded retry/cancellation, non-secret readiness diagnostics, durable exact-corpus Analysis Runs, immutable report creation, measured usage, and explicit UI start/progress/completion. The installed Codex CLI is not authenticated, so live verification awaits user login; explicit model selection remains an optional follow-up while API-key credential storage and per-token cost estimation move to later hosted-provider work.

## Slice 9 — Add the remaining provider choices

**Outcome:** Explicitly run analysis through Ollama, OpenAI API, Anthropic Claude API, Google Gemini API, or a separately installed Claude Code CLI using the same report contract.

**Blocked by:** Slice 8 and cross-provider evaluation.

**Scope:** Ollama first, followed by evaluated hosted API or CLI adapters, Credential Store for API providers, cost estimation where prices are knowable, installed-model discovery, and provider selection.

**Acceptance:** Every adapter passes the shared contract tests. Ollama absence leaves metadata and review acquisition usable; the app never downloads a model or silently changes providers.

**Tradeoff:** Supporting multiple vendors increases ongoing compatibility and evaluation work.

**Status:** Blocked.

## Slice 10 — Filter evidence and create Cohort Analyses

**Outcome:** Apply temporary Evidence Filters with immediate deterministic recalculation or deliberately create a separately scoped Cohort Analysis that can discover new Themes.

**Blocked by:** Slices 5, 7, and calibrated minimum cohort sizes.

**Scope:** Theme Metrics, Review Cohort scope contracts, Analysis Provider reuse, Report Repository, and filter/cohort interface.

**Acceptance:** Tests distinguish temporary filters from saved analyses, reproduce every denominator, rerank discovered Themes, hide zero-support Themes, mark below-threshold Themes, constrain excerpts and drill-down to the filter, preserve report immutability, reset unsaved filters, and enforce minimum cohort requirements.

**Tradeoff:** Small cohorts may be rejected rather than presented with misleading findings.

**Status:** Blocked.

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

**Blocked by:** Slices 5–12, Steam policy validation, accessibility/security gates, and copyright-holder confirmation.

**Scope:** integration and security verification, documentation, CI, MIT license, clean-install workflow, and source release.

**Acceptance:** A clean Windows environment completes installation and representative AppID, Codex/cloud, refresh, filtering, history, and export scenarios. Documentation covers credentials, Ollama, Codex, data paths, privacy, and recovery.

**Tradeoff:** Packaged releases and advertised macOS/Linux support remain outside this release gate.

**Status:** Blocked; copyright holder requires human confirmation.

## Slice 14 — Package and validate distribution

**Outcome:** Windows users can run a packaged release without Node.js or Python development toolchains, while source portability is verified before other operating systems are advertised.

**Blocked by:** Slice 13.

**Scope:** Windows packaging of the established frontend/backend delivery path, migration/update guidance, clean-machine validation, and macOS/Linux source checks.

**Acceptance:** Clean Windows install, first run, analysis, restart recovery, export, update, data preservation, and uninstall checks pass. macOS/Linux support claims match recorded source validation.

**Tradeoff:** Packaged macOS and Linux releases remain deferred.

**Status:** Blocked.

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

## Approval gates

- **Prototype:** satisfied; the Catalog → Split → Timeline → Research direction is approved. Connected-browser verification remains tracked separately.
- **Analysis quality:** fixture-based Slice 4 implementation may proceed with explicit provisional thresholds; approve the real-game baseline before production-quality acceptance or reliability claims.
- **Provider:** approve the first automated provider after quality/cost evaluation before Slice 8.
- **Steam:** resolve retention, attribution, and request-rate obligations before Slices 11 and 13.
- **Release:** confirm the MIT copyright holder and approve the release candidate before Slice 13 publication.
