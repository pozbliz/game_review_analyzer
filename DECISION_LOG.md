# Decision Log

## 2026-09-30 - Merge assignments use a bounded flat list

**What changed:**

- Replaced the dynamic assignment object with one flat assignment item per candidate.
- Bounded the list to the exact candidate count and restricted candidate keys to the request scope.
- Reject missing, unknown, or duplicate candidate assignments after parsing.

**Why:**

- Codex rejected the live 174-property output schema before inference and returned no output.
- A fixed assignment schema keeps the provider contract small while local validation preserves exact coverage.

**New issues:**

- JSON Schema cannot enforce unique candidate keys within the assignment list.

**Needs human judgment:**

- None.

---

## 2026-09-30 - Merge results use one assignment per candidate

**What changed:**

- Replaced grouped candidate-key arrays with an assignment object keyed by every candidate.
- Each assignment targets one returned Theme ID or uses `null` for discard.
- Kept assignment scope, Theme existence, polarity, provenance, and request validation local.

**Why:**

- Two live 174-candidate merges mapped at least one candidate into multiple Themes despite schema enums and explicit prompt checks.
- JSON object keys guarantee one response slot per candidate without the unsupported `uniqueItems` keyword.

**New issues:**

- Large merges require one JSON property per candidate, increasing the generated schema size.

**Needs human judgment:**

- None.

---

## 2026-09-30 - Codex batches receive a process deadline

**What changed:**

- Limited each Codex process attempt to 120 seconds with one transient retry.
- Launched Windows npm installations through their Node script instead of the short-lived command shim.
- Stopped the complete Windows process tree on cancellation or timeout.

**Why:**

- A live Main Report stopped at 207 reviews when batch 4 held two HTTPS connections open without CPU activity or a response.
- The command shim exited before its Node and Codex children, so cancellation could not reach the orphaned processes.

**New issues:**

- Telemetry cannot identify the upstream reason that the Codex response stream stopped.

**Needs human judgment:**

- None.

---

## 2026-09-30 - Provider output schemas bound to each request

**What changed:**

- Restricted completed-review and Theme-membership identifiers to the current batch in the Codex output schema.
- Restricted completed, mapped, and discarded merge keys to the current candidate set.
- Added safe merge-specific validation codes for request, scope, uniqueness, polarity, and provenance failures.
- Required Codex to check that each candidate key appears once across all mapped and discarded keys.
- Kept the existing post-response scope validation.

**Why:**

- A live 1,000-review run failed when Codex returned one membership identifier outside its first 63-review batch.
- The resumed live run completed all map batches, then returned an invalid merge contract from 174 candidates.
- The prompt requested exact identifiers, but the generated schema previously accepted any non-empty string.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-09-30 - First progressive Main Report implemented

**What changed:**

- Added deterministic selection of up to 500 oldest and 500 newest reviews.
- Added full-text map batches capped by character capacity and 250 reviews.
- Added durable validated map checkpoints and one candidate merge call.
- Retained candidates at 2% cohort support and exposed Themes at 5% support.
- Added one current Main Report slot, API routes, progress, evidence, and interface access.
- Replaced oversized reviews when possible and disclosed the skipped count.
- Blocked recreation while the current slot exists; Slice 18 owns replacement.
- Kept retained 2% Theme candidates internal by limiting evidence to visible Themes.
- Counted only oversized reviews skipped while filling the selected cohorts.

**Why:**

- Slice 17 requires the first resumable 1,000-review report before extension work can start.
- Local memberships and metrics keep provider output limited to semantic grouping.

**New issues:**

- Main Report extension and replacement remain unavailable until Slice 18.

**Needs human judgment:**

- None. Live Theme-quality review remains the Slice 21 gate.

---

## 2026-09-29 - Aggregate Themes expose retained review evidence

**What changed:**

- Added an on-demand evidence endpoint for Version 3 Theme memberships.
- Added an accessible Theme toggle with a five-review-height scrolling evidence area.
- Sorted matching reviews by helpful votes descending with deterministic tie-breaking.

**Why:**

- Support counts must remain auditable against the complete reviews that produced them.
- Loading evidence on demand avoids expanding the base report response, especially for future Main Reports.

**New issues:**

- Main Reports must reuse this evidence route when Slice 17 adds their report endpoint.

**Needs human judgment:**

- None.

---

## 2026-09-29 - Report creation control follows the selected scope

**What changed:**

- Removed the separate `Run 50-review test` button.
- Routed the shared `Create report` action to the Version 3 Test Report for the 50-review scope.
- Replaced the obsolete 5,000-review option with a disabled 1,000-review Main Report option.

**Why:**

- The scope selector already communicates which report the user intends to create.
- The 1,000-review Main Report backend remains scheduled for Slice 17 and must not use the Version 2 path.

**New issues:**

- The 1,000-review option remains unavailable until Slice 17 is complete.

**Needs human judgment:**

- None.

---

## 2026-09-29 - Application-wide redacted diagnostics added

**What changed:**

- Added bounded rotating JSON logs beside the application database.
- Kept diagnostics in backend logs without a user-facing read API or panel.
- Added safe failure events for HTTP requests, imports, analysis, and browser runtime errors.
- Split Version 3 request, scope, and provenance contract failures into distinct codes.
- Added exact Theme-scope instructions to reduce invalid provider responses.
- Kept uniqueness in provider instructions and post-response validation because Codex CLI rejects the JSON Schema `uniqueItems` keyword.
- Added distinct codes for duplicate candidate, completion, and membership identifiers.

**Why:**

- The UI exposed only `Analysis failed`, while the underlying Version 3 contract rejection was discarded with the temporary provider output.
- Local users need enough redacted context to diagnose failures without reading a server terminal.
- Adding JSON Schema `uniqueItems` made Codex CLI exit before inference with no output, so the supported schema cannot express those rules directly.

**New issues:**

- Diagnostics identify the failed contract rule but intentionally omit raw provider output and user review content.

**Needs human judgment:**

- None.

---

## 2026-09-29 - Standalone Version 3 Test Report implemented

**What changed:**

- Added Version 3 Theme candidates, internal memberships, and local aggregate metrics.
- Added one replaceable Test Report slot with deterministic 25-oldest and 25-newest selection.
- Added one-call Codex execution, aggregate API output, and a separate Test Report interface.
- Kept Version 2 report history separate while the Main Report remains on the earlier path.
- Added one retry for transient Theme-call failures. Invalid output still fails without retry.
- Cleared obsolete run links atomically when a later Test Report replaces its slot.

**Why:**

- Slice 16 establishes the smallest complete path for the approved aggregate report design.
- Separate storage lets users rerun the Test Report without changing the Main Report.

**New issues:**

- Character-based map packing and oversized-review handling remain in Slice 17.
- The Version 2 Main Report stays active until Slice 17 replaces it.

**Needs human judgment:**

- None. Live Theme-quality review remains the final gate in Slice 21.

---

## 2026-09-29 - Progressive report implementation plan approved

**What changed:**

- Preserved Slices 0–15 as implementation history.
- Added Slices 16–21 for Test Report, Main Report, extension and replacement, cleanup, exports, and verification.
- Set Slice 16 as the execution frontier.
- Blocked source release and packaging until progressive workflow verification passes.

**Why:**

- The redesign needs a staged replacement path that keeps each intermediate state testable.
- Test Report behavior provides the smallest vertical slice for the new contracts and metrics.
- Release work must use the approved report workflow instead of superseded Version 2 behavior.

**New issues:**

- `TASKS.md` still describes the earlier implementation and needs regeneration from the approved plan.

**Needs human judgment:**

- None. The user approved the slice order, blockers, and execution frontier on 2026-09-29.

---

## 2026-09-29 - Progressive aggregate reports replace evidence-heavy history

**What changed:**

- Replaced immutable report history with one progressive Main Report and one separate 50-review Test Report per game.
- Defined 1,000-review main analysis steps using oldest and newest unseen review identities after Steam refresh.
- Replaced Opinion Points and excerpts with internal Theme memberships, compact Theme candidates, and local metrics.
- Limited visible results to five Themes per polarity that reach 5% support in either cohort.
- Removed categories, Evidence Filters, mixed-reception linkage, direction labels, per-review evidence, and Version 2 compatibility.
- Limited the new provider path to one supported Codex CLI model with low reasoning.
- Cleared existing local application data while retaining the gitignored evaluation corpus.

**Why:**

- The user values fast, token-conscious summaries of the main review opinions over per-review auditability.
- One current cumulative report matches the user's workflow better than saved reports for every 1,000-review stage.
- A separate test report permits repeatable 50-review checks without changing the Main Report.

**New issues:**

- The implemented report, provider, metrics, export, and interface contracts still represent the superseded design.
- Removing evidence means users cannot inspect individual Theme assignments.
- Full review text and Codex CLI fixed overhead may still make large extensions slow or quota-intensive.

**Needs human judgment:**

- None. The user approved the revised `DESIGN.md` on 2026-09-29.

---

## 2026-09-27 — Pilot reports require specific design evidence

**What changed:**

- Restricted extraction to opinions about a concrete design or technical element and its observed effect.
- Replaced exact-subject grouping with one semantic consolidation pass over validated Opinion Points.
- Kept deterministic support metrics and the existing exact-evidence validation after consolidation.
- Advanced the extraction contract version so prior generic cache entries are not reused.

**Why:**

- Generic findings such as “this game is amazing” do not help a developer understand a reusable design strength or weakness.
- Equivalent observations can use different wording, so exact normalized subjects split one finding into several weak Themes.

**New issues:**

- Semantic consolidation adds provider time and tokens to each report with retained Opinion Points.

**Needs human judgment:**

- Review one new 50-review pilot before approving this analysis-quality direction.

---

## 2026-09-27 — Report creation exposes stage and provider timing

**What changed:**

- Added redacted JSON timing events for preparation, provider subprocesses, validation attempts, extraction cache writes, consolidation, and report persistence.
- Included safe failure codes and retry state for every rejected Codex result.

**Why:**

- One 50-review Codex pilot took 6 minutes 32 seconds and used 53,087 input plus 6,374 output tokens.
- The first two batches took 44 and 39 seconds; later hidden retries caused 193-second and 80-second gaps.
- Existing telemetry recorded only run start and completion, so it could not identify provider retries.

**New issues:**

- At the measured rate, 2,500 reviews take about 5.4 hours and 5,000 take about 10.9 hours.
- Codex CLI remains unsuitable for the larger report scope without a faster bulk provider path.

**Needs human judgment:**

- Select a faster hosted batch provider before treating the larger scope as practical.

---

## 2026-09-27 — Codex extraction checkpoints every 10 reviews

**What changed:**

- Limited Codex extraction batches to 10 reviews, matching the Ollama checkpoint size.
- Preserved each completed batch in the existing extraction cache.

**Why:**

- A 50-review Codex call kept progress at zero until the full call returned.
- Smaller batches expose durable progress and reduce repeated work after interruption.

**New issues:**

- Five CLI calls add fixed token and process overhead to a 50-review pilot.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Codex CLI defaults to low reasoning

**What changed:**

- Changed the current `gpt-5.6-luna` Codex CLI default from medium to low reasoning.
- Kept historical evaluation records at medium reasoning unchanged.

**Why:**

- The user chose lower latency for current report generation.

**New issues:**

- Low reasoning has not received the prior medium-setting quality evaluation.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Catalog restores recent reports and retained work

**What changed:**

- Restored the six newest saved reports beside the initial game search.
- Added per-game workspace discovery for completed Full acquisition and the latest Analysis Run.
- Reused completed Game Datasets instead of repeating Full acquisition.
- Added a default 50-review Codex CLI pilot and retained the 5,000-review option.
- Let users resume a cancelled analysis or choose another provider.
- Limited automatic browser restore to queued or running work, so terminal work does not replace the Catalog.

**Why:**

- The approved recent-report panel existed only in the prototype.
- Report history was an incorrect proxy for whether reviews had already been acquired.
- Returning to game search hid an unfinished analysis without cancelling it.
- CPU-only Ollama analysis was too slow for normal use on this machine.

**New issues:**

- The 50-review Codex pilot remains provisional and can miss Themes found by the larger scope.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Steam review imports back off after rate limits

**What changed:**

- Increased the delay between Steam review pages from 0.5 seconds to 2 seconds.
- Made HTTP 429 retries honor numeric `Retry-After` values, with 30-second and 60-second fallbacks.
- Retained the existing three-attempt limit and durable import checkpoints.

**Why:**

- A Full import saved 14,936 reviews before Steam returned HTTP 429.
- The prior one-second and two-second retries repeated the request too quickly.

**New issues:**

- Full imports now take about 2.5 extra minutes per 100 pages.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Ollama extraction progress uses 10-review batches

**What changed:**

- Limited Ollama extraction batches to 10 reviews while retaining 50-review batches for other providers.
- Preserved each completed Ollama batch in the existing extraction cache.

**Why:**

- The 50-review pilot previously showed zero progress until one long CPU-bound generation completed.
- Ten-review batches provide five accurate progress updates without per-review model calls.

**New issues:**

- Repeating the extraction prompt can increase total Ollama runtime.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Steam metadata identity follows the nested AppID

**What changed:**

- Accepted a sole Steam metadata record under an unexpected outer key when its nested `steam_appid` matches the request.
- Kept mismatched, missing, and ambiguous responses invalid.

**Why:**

- Steam returned Hades II and Hades under unrelated outer keys while preserving the correct nested AppID and game data.
- The outer key mismatch caused valid previews to fail with HTTP 502.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-09-27 — History failures cannot trigger acquisition

**What changed:**

- Made report-history failures nonfatal while viewing an already loaded report.
- Disabled report creation when the catalog cannot determine whether saved reports exist.
- Bound preview and history responses to the latest game selection.
- Added the report-scope percentage threshold to the empty-Theme explanation.

**Why:**

- An auxiliary history failure must not hide an immutable report or masquerade as an empty history.
- Treating an unknown history as empty could start an unnecessary Full import.
- Out-of-order responses must not show saved reports from a previously selected game.
- Theme conclusions require both distinct-review support and a minimum scope percentage.

**New issues:**

- Connected-browser verification remains open because this session has no available browser.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Empty Theme reports disclose extraction yield

**What changed:**

- Added total and non-neutral Opinion Point counts to the report API scope.
- Replaced repeated empty category messages with one report-level explanation when no Themes exist.
- Defined a valid empty result as no same-subject, same-polarity support across at least two distinct reviews.

**Why:**

- The three Minishoot Ollama runs each extracted one Opinion Point from 50 reviews. The evidence rule then correctly rejected that unsupported point as a Theme.
- Showing the extraction yield distinguishes shallow model output from a genuine absence of player opinions.

**New issues:**

- None. The existing human calibration task still covers semantic grouping quality.

**Needs human judgment:**

- None beyond the existing calibration task.

---

## 2026-09-27 — Immutable reports route creation through the catalog

**What changed:**

- Removed refresh, Full import, and reconciliation controls from the report header.
- Added a selected-game **Create new report** link into the catalog workflow.
- Removed the visible scope digest while retaining it in the report contract and exports.
- Kept report deletion and Game Dataset storage controls for recovery and local data management.

**Why:**

- Acquisition changes the input corpus and belongs before report creation, not inside an immutable result.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-09-27 — Catalog reuses retained reviews for new reports

**What changed:**

- Loaded newest-first saved reports after game selection and made the latest report the primary action.
- Added dated provider/model history and a secondary **Create new report** action.
- Started later analysis runs directly from the retained full-history dataset without another Full import.

**Why:**

- Returning users should reach saved work before starting more acquisition.
- Immutable reports can reuse the exact locally retained review corpus.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-14 — Saved reports lead a one-time preparation workflow

**What changed:**

- Approved a catalog flow that shows the latest saved report first, dates every history entry, and separates **Create new report** as a secondary action.
- New reports reuse retained local reviews by default; acquiring newer reviews is explicit rather than an automatic Full download.
- Removed Dataset maintenance and the scope digest from the normal report-view specification while retaining recovery/storage controls and stored provenance outside that view.
- Recorded the zero-Theme Minishoot Ollama result as an analysis-quality defect requiring a bounded follow-up.

**Why:**

- Existing immutable reports and local reviews should be discoverable before the application offers duplicate acquisition work.
- The intended use is prepare once and read the report; maintenance terminology and internal digests add clutter without helping that workflow.

**New issues:**

- The current production UI does not yet implement this simplified flow.
- Empty Theme reports need an explicit validity rule and user-facing failure behavior.

**Needs human judgment:**

- Calibrate when a genuinely sparse review scope may validly contain zero Themes.

---

## 2026-08-14 — Direct report URLs fall back to the React application

**What changed:**

- Made the production static-file host return `index.html` for missing client-side routes such as `/reports/{id}` while preserving normal static assets and API routes.
- Kept explicit `null` values in report metadata and accepted `null` for optional cohort comparisons in the frontend report parser.

**Why:**

- Report links use browser navigation, and Starlette's default HTML static-file mode returns a JSON 404 for nested React routes instead of bootstrapping the client application.
- The report endpoint had stripped unknown metadata fields that the shared Steam metadata parser requires explicitly, so the React page failed after its API request succeeded.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-14 — Analysis controls survive import recovery

**What changed:**

- Persisted the selected analysis provider in browser-local state so a Full-import reload cannot silently switch an Ollama pilot back to Codex.
- Added direct UI coverage proving a running analysis exposes **Cancel analysis**, calls the run cancellation endpoint, and renders the cancelled state.

**Why:**

- Provider selection and cancellation are safety controls: losing either across a long import can start the wrong compute path or make expensive work appear unstoppable.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-13 — Ollama testing uses a 25-plus-25 pilot scope

**What changed:**

- Limited Ollama runs started by the application UI to the 25 oldest and 25 newest eligible reviews after a completed Full import.
- Kept the standard Codex report scope at up to 2,500 oldest and 2,500 newest reviews.

**Why:**

- Both installed Qwen models exceeded one minute without completing a strict two-review live extraction on CPU-only hardware.
- A 50-review pilot exercises real chronological selection, durable extraction, and report generation without presenting the result as comprehensive.

**New issues:**

- The Ollama extraction prompt and schema need profiling before increasing the local pilot scope.

**Needs human judgment:**

- Decide whether pilot speed and extraction quality justify a larger local scope after the first completed report.

---

## 2026-08-13 — Resumable cohort analysis uses bounded extraction and deterministic consolidation

**What changed:**

- Added restart-safe 50-review/32,000-character extraction batches whose validated Opinion Points are cached per review and reused after failure.
- Consolidated normalized canonical subjects locally across both cohorts, then calculated cohort support and conservative direction labels without another model request.
- Added redacted JSON analysis events and optional OTLP/HTTP traces for HTTP requests, runs, and extraction batches.

**Why:**

- Bounded requests make a 5,000-review scope recoverable and prevent one failure from repeating completed Codex work.
- Deterministic consolidation protects quota and makes metrics reproducible while preserving source evidence.
- Safe operational metadata is sufficient to diagnose run phase, provider failures, timing, and token usage without retaining review content.

**New issues:**

- Differently worded canonical subjects may remain separate without embeddings or a bounded semantic merge pass.
- Direction thresholds and canonical-subject consistency need representative-game calibration.

**Needs human judgment:**

- Approve production-quality thresholds after representative-game evaluation.

---

## 2026-08-13 — Default reports compare the oldest and newest available reviews

**What changed:**

- Approved a default report scope of up to the 2,500 oldest and 2,500 newest eligible reviews selected from a completed full-history Steam import.
- Approved one shared Theme system over the combined scope, followed by a bounded audit of unassigned cohort-specific Opinion Points and deterministic cohort comparison metrics.

**Why:**

- The comparison should reveal issues prominent near the beginning that appear improved, persistent, or worse in recent reviews.
- Reading each review once and reusing validated extraction preserves completeness while limiting repeated Codex quota use.

**New issues:**

- A full-history Steam scan is required before the app can identify the genuinely oldest available reviews.
- Direction labels require calibrated thresholds and must not claim causation or a proven software fix.

**Needs human judgment:**

- Confirm calibrated direction-label thresholds after representative-game evaluation.

---

## 2026-08-13 — Steam screenshots open in a native lightbox

**What changed:**

- Made Steam screenshot thumbnails explicit buttons that open the selected image in a native dialog.
- Added cyclic previous/next controls, image position, close and backdrop dismissal, Escape support through the dialog, and an original-image link.

**Why:**

- The responsive thumbnail grid is useful for browsing but too small for inspecting screenshot detail.
- A native dialog provides the required large view and modal behavior without adding a lightbox dependency.

**New issues:**

- None.

**Needs human judgment:**

- Confirm image sizing, backdrop dismissal, and Escape behavior visually in Chrome after a hard reload.

---

## 2026-08-13 — Steam language notation becomes labeled support groups

**What changed:**

- Parsed Steam's trailing full-audio footnote and per-language asterisks at the storefront presentation boundary.
- Rendered full-audio and remaining interface/subtitle languages as separate labeled chip groups, with regional hyphen notation normalized to parentheses.

**Why:**

- The raw comma-delimited language string and trailing asterisk explanation were difficult to scan and made full-audio support easy to miss.
- Keeping the conversion in the shared storefront component applies consistently to catalog previews and immutable report views without changing stored Steam snapshots.

**New issues:**

- None.

**Needs human judgment:**

- Confirm the rebuilt language groups visually in Chrome after a hard reload.

---

## 2026-08-13 — Storefront metadata favors scanning over decorative hierarchy

**What changed:**

- Removed the `STEAM SNAPSHOT` and `CONFIRM IDENTITY` decorative labels.
- Changed store-fact values to normal weight, rendered tags as compact Steam-like chips, and separated feature names from explicit support-status badges.
- Hid the successful backend status visually while preserving its live status announcement; loading and unavailable states remain visible.

**Why:**

- Dense bold values, comma-delimited tags, and punctuation-delimited feature states made the full-width details harder to scan than necessary.
- Successful connectivity is background system state, while loading or failure still needs visible explanation.

**New issues:**

- None.

**Needs human judgment:**

- Confirm the rebuilt storefront hierarchy visually in Chrome after a hard reload.

---

## 2026-08-13 — Game selection and details use separate full-width states

**What changed:**

- Replaced the collapsible catalog rail with a full-width game-search state followed by a full-width game-details state after successful preview.
- Added a compact `Game search` back control that restores the preserved search form without browser routing or persisted UI state.
- Kept durable import and analysis restoration on the details state.

**Why:**

- The permanent rail still looked like primary application navigation even though selecting a game is a setup step.
- Separate states give dense storefront facts the full catalog width and match the natural select-then-analyze workflow.

**New issues:**

- None.

**Needs human judgment:**

- Confirm the rebuilt two-step flow visually in Chrome after a hard reload.

---

## 2026-08-13 — Collapsed catalog preserves explicit grid placement

**What changed:**

- Pinned the selection panel, toggle rail, and preview panel to their intended grid columns, with a one-column override at the existing mobile breakpoint.

**Why:**

- The hidden selection panel leaves CSS grid layout flow. Automatic placement then moved the toggle into the zero-width column and the preview into the 48-pixel rail instead of the flexible details column.

**New issues:**

- None.

**Needs human judgment:**

- Confirm the rebuilt collapsed layout visually in Chrome after a hard reload.

---

## 2026-08-13 — Catalog selection collapses into a narrow rail

**What changed:**

- Increased the catalog and header maximum width from 1,180 to 1,500 CSS pixels.
- Replaced the fixed two-column catalog with a 420-pixel selection panel, a 48-pixel native toggle rail, and a flexible details panel.
- Kept the selection panel expanded by default and made collapse state page-local, with explicit expanded state and controls metadata on the toggle.

**Why:**

- The previous nested three-column storefront layout was compressed inside a details panel that received less than half of the available laptop width.
- A user-controlled rail preserves quick access to game selection while letting dense storefront metadata use nearly the full page.

**New issues:**

- None.

**Needs human judgment:**

- Confirm the rebuilt expanded and collapsed layouts visually in Chrome; the browser extension was unavailable for automated Chrome inspection.

---

## 2026-08-13 — Source-release operation and configuration documented

**What changed:**

- Added a secret-free `.env.example` covering every supported runtime setting, with an automated check that the optional Steam key remains blank.
- Added one source-operation guide covering locked installation, production startup, configuration, Codex CLI, Ollama, Manual Codex, local storage, privacy, updates, recovery, and current release limits.
- Corrected the README constraint: the database path is configurable through the environment, but no in-app relocation workflow exists.

**Why:**

- A source release needs one reliable operational path without duplicating setup details across provider-specific files.
- Testing the example against the supported settings prevents configuration drift and accidental example secrets.

**New issues:**

- None.

**Needs human judgment:**

- The MIT copyright holder, assistive-technology acceptance, analysis-quality release gate, and final release approval remain human gates.

---

## 2026-08-13 — Evidence Filters reuse the approved review-scope dimensions

**What changed:**

- Added one strict, immutable Evidence Filter query contract covering Steam recommendation, Steam purchase, received-free and Early Access state, playtime range and basis, and review-created date range.
- Defined absent optional values as no restriction, kept playtime-at-review as the default basis, and rejected unknown fields, negative bounds, and inverted ranges.
- Kept relative date presets out of the backend contract; clients resolve them to explicit inclusive timestamps before querying.
- Reused the existing Theme Metrics calculator over matching reviews and Opinion Points; a valid zero-match filter returns zero-support metrics and empty presentation groups without weakening the non-empty immutable-report invariant.
- Applied the same query parameters to the existing report-summary and Theme-evidence endpoints instead of creating parallel filtered resources; response-time recalculation never writes a Report Version or other state.
- Filtered presentation reranks matching Themes, hides zero-support Themes, marks those below the immutable report's thresholds, and restricts representative and complete review evidence to the same matching set.
- Added native resettable report controls that serialize only active values and clear cached evidence whenever membership changes.
- Aligned the evidence HTTP and frontend contracts with the existing nullable playtime-at-review domain value, displaying it as unknown instead of failing or inventing zero hours.

**Why:**

- Reusing the already approved review-scope dimensions avoids an immediately incomplete high-playtime-only API and a later breaking contract expansion.
- Explicit timestamps make repeated filter requests deterministic and remove backend clock behavior from the contract.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-13 — Browser acceptance findings fixed at shared boundaries

**What changed:**

- Deduplicated repeated Steam category descriptions in first-seen order at the shared metadata normalizer.
- Added narrowly scoped padding and minimum-height rules so measured production links, disclosure summaries, and provider controls meet the 24 CSS-pixel minimum target size.
- Rechecked live Hades II metadata and fixture-backed reports at 390px: controller labels appear once, every visible interactive target is at least 24 pixels, no horizontal overflow occurs, and browser consoles remain clean.

**Why:**

- Normalizing repeated source descriptions once prevents every UI and export consumer from needing its own duplicate guard.
- Styling only the measured selectors preserves the dense research layout while meeting the accessibility baseline.

**New issues:**

- None.

**Needs human judgment:**

- Native keyboard and screen-reader acceptance remain tracked separately.

---

## 2026-08-12 — Connected-browser acceptance resumed with two follow-ups

**What changed:**

- Restored the required built-in browser connection in the fresh conversation and completed the executable production and prototype acceptance matrix at laptop and 390px widths.
- Verified variant switching, filters, Theme disclosure, evidence and history flows, name/AppID selection, provider/scope disclosure, progress cancellation/resume, semantic labels, non-color text, reduced-motion CSS branches, and clean browser consoles.
- Kept the overall accessibility gate open because several production links, disclosure summaries, and the provider selector render between 17.6 and 21.6 CSS pixels tall, below the 24-pixel minimum target size.
- Kept native Tab and Enter/Space verification open because the connected-browser controller dispatches key events but does not reproduce those browser default actions; Escape dismissal was verified.
- Traced duplicate Hades II DualShock and DualSense feature rows to `normalize_features`, which preserves repeated Steam category descriptions.

**Why:**

- Restoring browser registration clears the environment blocker, but connected-browser acceptance cannot close while a measured accessibility failure remains.
- Feature descriptions should be deduplicated once at the shared Steam normalization boundary instead of hidden by individual frontend consumers.

**New issues:**

- Increase undersized production interaction targets and recheck at 390px width.
- Deduplicate repeated Steam category descriptions and recheck the live controller-feature list.
- Complete native Tab and Enter/Space verification manually.

All three issues are tracked in `TASKS.md`.

**Needs human judgment:**

- None.

---

## 2026-08-12 — Evidence Filters retained and Cohort Analysis deferred

**What changed:**

- Retained temporary Evidence Filters in the source MVP for raw review evidence and deterministic recalculation of existing Theme metrics without model calls.
- Deferred Cohort Analysis, its minimum-size calibration, and cohort-specific Theme discovery.
- Revised Slice 10 to contain only the approved Evidence Filter behavior.

**Why:**

- Filtering and reranking already discovered Themes is deterministic, useful for raw-review exploration, and does not spend provider quota.
- Cohort-specific discovery requires additional model runs and minimum-size calibration that are not justified for the source MVP.

**New issues:**

- None.

**Needs human judgment:**

- None; the user explicitly approved this scope revision.

---

## 2026-08-12 — Connected-browser registration remains unavailable

**What changed:**

- Retried the required in-app browser controller twice after confirming the installed helper exists and its Node runtime starts.
- Replaced the stale `os error 3` task diagnosis with the current failure: both connections report `Browser is not available: iab`.
- Recorded the independently reproduced Windows Codex sandbox failure, `CreateRestrictedToken failed: 87`, which matches open OpenAI Codex issue #18451.
- Recorded the user's explicit approval to run the `node_repl` MCP server with `args = ["--disable-sandbox"]`; `codex mcp list` validates the saved configuration.
- Retried after a full Codex restart: `node_repl` runs, but browser discovery returns an empty list and the required `iab` surface remains unavailable.
- Confirmed the browser plugin is enabled and configured for `iab`, but the installed native computer-use broker is not running and its configured named pipe does not exist; the `node_repl` request consequently contains no browser registration metadata.
- Confirmed the local app URL had been opened in Chrome rather than Codex's built-in Browser; Chrome correctly did not launch the required in-app-browser broker. The built-in Browser activation path remains untested.
- After updating to Codex 26.803.81509 and opening the built-in Browser, found that Codex regenerates the plugin-owned MCP configuration as `args = []` on full app launch, removing the approved `--disable-sandbox` workaround.
- Restored the argument after startup; because the running MCP process cannot hot-reload it, the next retry must use a new conversation without quitting the desktop app.
- Kept every connected-browser acceptance task open.

**Why:**

- The sandbox failure occurs outside this repository. The approved workaround restores the execution surface, but the desktop app regenerates its plugin-owned configuration at launch and the running MCP process cannot hot-reload edits.
- Disabling the `node_repl` sandbox gives its browser automation the current Windows user's permissions rather than restricted-token isolation; the user explicitly approved that security tradeoff to restore the required acceptance surface.
- Substituting another browser would not verify the previously approved acceptance boundary.

**New issues:**

- Start a new conversation without quitting Codex so a fresh MCP process reads the restored argument, open the built-in Browser at the local app URL, verify broker registration, and complete the pending acceptance flow.

This issue remains tracked in `TASKS.md`.

**Needs human judgment:**

- None; the sandbox-disable workaround is explicitly approved.

---

## 2026-08-12 — Connected-browser acceptance blocked by controller startup

**What changed:**

- Started the local production-serving path for connected-browser acceptance, then stopped it after the in-app browser controller failed before opening a tab.
- Verified Node 24.15.0 and the installed browser helper exist; repeated controller startup still returned Windows `os error 3`.

**Why:**

- Browser interaction, responsive layout, keyboard behavior, reduced motion, and console state cannot be accepted without the required connected browser surface.
- Substituting a different automation mechanism would not satisfy the selected browser workflow's verification boundary.

**New issues:**

- Restore the in-app browser controller before connected-browser acceptance resumes.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- None unless the browser environment cannot be restored and a different acceptance surface must be approved.

---

## 2026-08-12 — Codex CLI fixed overhead accepted without weakening validation

**What changed:**

- Measured the one-review application prompt at under 1 KB and the generated strict result schema at about 4.6 KB, compared with 15,744 input tokens reported by the live CLI run.
- Closed the quota-overhead task by retaining the strict schema and explicitly avoiding quota-efficiency claims.

**Why:**

- The application-controlled text is too small to explain most of the measured input, so stripping schema constraints would trade evidence integrity for little likely savings.
- Meaningful multi-review runs amortize the CLI's fixed context better than tiny diagnostic runs.

**New issues:**

- None.

**Needs human judgment:**

- None; further cloud runs remain separately user-approved.

---

## 2026-08-12 — Slice 10 release dependency made explicit

**What changed:**

- Corrected the implementation plan to record completed Codex authentication, live verification, and local Qwen benchmarking.
- Added an explicit human gate for retaining Slice 10 in the source MVP or moving it to deferred scope through an approved plan/design revision.

**Why:**

- Deferred calibration blocks Slice 10, while Slice 13 still depends on Slices 5–12; the release path therefore requires a visible scope decision rather than an implied assumption.

**New issues:**

- Decide the source-MVP scope of Cohort Analysis before release work proceeds.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- Keep Slice 10 in the source MVP and resume calibration, or approve moving it to deferred scope.

---

## 2026-08-12 — Authenticated Codex report flow verified with explicit Theme support

**What changed:**

- Added the existing two-distinct-review Theme-support invariant to the shared analysis instruction after a one-attempt diagnostic returned `insufficient_theme_support`.
- Completed and inspected live run `32f549e3-0d1d-4193-8c6d-a7e67c07da89`: six exact Opinion Points, one mixed classification, no unsupported Themes, and an immutable Report Version.
- Limited both diagnostic and verification runs to one review, one attempt, and a three-minute cancellation cap.

**Why:**

- The validator enforced the invariant, but the provider prompt did not state it; making both agree fixes the cause instead of weakening validation.
- One-review verification exercises the complete durable path with minimum review-data transmission.

**New issues:**

- The full structured contract used 15,744 input tokens for one review, so its fixed prompt/schema overhead is not quota-efficient.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- None for the completed live gate; approve further cloud runs separately.

---

## 2026-08-12 — First authenticated Codex run retained safe failure diagnostics

**What changed:**

- Authenticated Codex CLI 0.147.0 through the user's ChatGPT account.
- Ran one approved Hades II review through the real API, durable Analysis Run, and Codex CLI path; both attempts failed validation and no Report Version was created.
- Preserved the shared validator's non-content failure code instead of collapsing every final validation failure to `invalid_result`.

**Why:**

- Retrying or changing prompts without knowing whether the failure is schema, scope, evidence, or relationship related would spend quota blindly.
- Existing validator codes contain no review text or model output, so they improve diagnosis without weakening the privacy boundary.

**New issues:**

- One fresh live run is needed to capture the specific safe validation code before any prompt change.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- Approve another live Codex attempt when quota is available.

---

## 2026-08-12 — Local Qwen full-analysis candidates rejected

**What changed:**

- Downloaded the verified Ollama Qwen 3.5 4B and 9B model tags after explicit approval.
- Added a reproducible exact-evidence benchmark runner and tested the 18-review human-reviewed pilot with a 16,384-token context.
- Rejected 4B as a full-analysis default after all three games failed validation, and stopped 9B after roughly 20 minutes on the first six-review game at 100% CPU.
- Added stable local timeout handling and documented the benchmark results.

**Why:**

- 4B produced incomplete scopes or broken Theme references even after one retry; invalid output cannot become a report.
- 9B consumed 6.6 GB at 100% CPU with only about 2.1 GB physical memory remaining and did not finish a practical batch.

**New issues:**

- A future local-model evaluation should use bounded Opinion Point extraction rather than the complete full-analysis contract.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- Approve another local-model experiment before spending more inference time.

---

## 2026-08-12 — Ollama runtime installed without models

**What changed:**

- Installed the verified official Ollama 0.32.8 Windows package and confirmed its local API at `127.0.0.1:11434`.
- Kept model installation separate; the local Ollama store remains empty.

**Why:**

- Runtime installation makes the implemented provider path available while preserving explicit approval for multi-gigabyte model downloads.

**New issues:**

- Qwen 3.5 4B/9B benchmarking still requires explicit model downloads.

This issue is tracked in `TASKS.md`.

**Needs human judgment:**

- Approve which Qwen model or models to download.

---

## 2026-08-12 — Ollama local-provider path implemented

**What changed:**

- Added local-only Ollama service discovery and listing of models already installed by the user.
- Added schema-constrained streaming analysis with bounded malformed-output retry, cancellation, measured token use, and the existing exact-scope/evidence validator.
- Added explicit Codex CLI versus installed Ollama model selection and local-processing disclosure in the analysis interface.
- Added inert Qwen 3.5 4B/9B installation commands that the user must copy and run outside the application.

**Why:**

- The same durable Analysis Run and immutable Report Version path can support a cheap local model without a new orchestration system or dependency.
- Restricting selection to `/api/tags` results prevents the application from silently pulling a model or changing providers.

**New issues:**

- This machine has neither an Ollama CLI nor a running local service, so Qwen 3.5 4B/9B quality and performance cannot yet be benchmarked.

Both issues are tracked in `TASKS.md`.

**Needs human judgment:**

- Install and start Ollama plus the desired Qwen model before requesting the benchmark.

---

## 2026-08-12 — Durable Codex CLI analysis flow completed

**What changed:**

- Added a separate durable Analysis Run record that snapshots exact Review Revisions, provider/model, explicit provisional metric thresholds, cancellation, usage, and the resulting Report Version.
- Added restart recovery and a runner that reuses the shared request validator, deterministic metrics, and immutable report repository.
- Added authenticated start, progress, cancellation, measured-token disclosure, and completed-report navigation to the local web flow.

**Why:**

- Acquisition jobs contain cursor and import checkpoints, while provider runs need exact corpus, token usage, and report provenance; keeping the records separate avoids ambiguous state.
- The provisional thresholds of two reviews and one percent remain visible and uncalibrated rather than becoming a hidden reliability claim.

**New issues:**

- A live run still requires the user to authenticate the installed Codex CLI.
- Explicit model selection is unnecessary while only the pinned first model is supported, but remains a task if another Codex model is needed.

Both issues are tracked in `TASKS.md`.

**Needs human judgment:**

- Log in through Codex CLI before the first live end-to-end analysis run.

---

## 2026-08-12 — Codex CLI provider foundation completed

**What changed:**

- Generalized the exact-scope result validator so automated providers reuse the Manual Codex trust boundary.
- Added isolated `codex exec` execution with an ephemeral session, read-only sandbox, explicit schema and model, captured output, bounded retry, cancellation, model verification, and measured token usage.
- Added non-secret installation/login diagnostics plus external-cloud and unknown-subscription-quota disclosure in the analysis setup UI.

**Why:**

- One validator prevents provider-specific evidence rules from drifting.
- A shell-free isolated process keeps review text out of command arguments and diagnostics while allowing the local web backend to automate the user's CLI.

**New issues:**

- Durable analysis-job and Report Version integration remains required before the UI can start a real run.
- The installed Codex CLI is not authenticated, so live verification cannot run yet.

Both issues are tracked in `TASKS.md`.

**Needs human judgment:**

- Log in through Codex CLI before the first live end-to-end analysis run.

---

## 2026-08-12 — Codex CLI-first provider path approved

**What changed:**

- Replaced the planned first OpenAI API adapter with automated use of the user's separately installed and authenticated Codex CLI.
- Kept the versioned Analysis Provider contract vendor-neutral and selected Ollama as the next adapter and evaluation path, followed only as needed by hosted APIs or Claude Code.
- Replaced the inapplicable CLI dollar estimate with measured usage when available and an explicit subscription-quota uncertainty disclosure.
- Selected Qwen 3.5 9B and 4B as initial local candidates to benchmark against the existing human-reviewed pilot without embeddings.

**Why:**

- The user already has Codex CLI access and does not intend to configure an OpenAI API key.
- Automating schema-constrained CLI execution preserves the local web workflow without requiring manual prompt preparation or result-file movement.
- Cheap models may be sufficient for bounded extraction and summaries, but paraphrase grouping and exact-evidence behavior must be measured rather than assumed.

**New issues:**

- CLI subscription quota and remaining allowance are not reliably available as monetary cost.
- Local model feasibility depends on hardware that has not yet been confirmed.
- Codex CLI `0.147.0` is installed in the current environment but is not authenticated.

These issues are tracked in `TASKS.md` through the Slice 8 login and quota-disclosure tasks and the Slice 9 compatible-hardware benchmark task.

**Needs human judgment:**

- Log in through Codex CLI before the first live end-to-end analysis run.

---

## 2026-08-11 — Implementation continuation checkpoint recorded

**What changed:**

- Reconciled the README, plan, and task tracker with completed Slices 1–7, 11, and 12.
- Clarified that Slice 4 implementation is complete while its production-quality calibration remains explicitly deferred.
- Recorded the latest verification gate, exact next approval, implementation order, deferred work, and remaining human gates in `TASKS.md`.
- Closed the exact-evidence and embedded-instruction evaluation task based on the completed synthetic conformance run and rejection tests.

**Why:**

- A new session can now resume from the task tracker without reconstructing state from conversation history.
- Deferred reliability claims should not be mistaken for an implementation blocker to the first cloud adapter.

**New issues:**

- None.

**Needs human judgment:**

- Approve OpenAI `gpt-5.6-luna` with medium reasoning as the first automated provider.
- Complete the already tracked browser, calibration, copyright, and release gates when their slices are reached.

---

## 2026-08-11 — First cloud provider evaluated

**What changed:**

- Compared OpenAI GPT-5.6 Luna, Google Gemini 3.5 Flash-Lite, and Anthropic Claude Haiku 4.5 using current official capability, model-versioning, structured-output, and pricing documentation.
- Recommended OpenAI `gpt-5.6-luna` with medium reasoning as the first automated adapter, subject to explicit human approval and direct-API conformance testing.
- Kept quality claims provisional: only Luna has project-specific evidence, and that evidence came through Codex CLI rather than the direct Responses API.

**Why:**

- Luna has the lowest listed standard input and output prices of the compared candidates and is the only candidate whose failure modes have already been exercised against this project's corpus.
- Existing exact-evidence validation rejected Luna's fabricated or incomplete evidence, so provider automation can reuse the proven trust boundary without embeddings or silent fallback.

**New issues:**

- None beyond the existing cross-provider evaluation and production-quality calibration tasks.

**Needs human judgment:**

- Approve OpenAI `gpt-5.6-luna` with medium reasoning as the first automated provider, or select a different evaluated candidate.

---

## 2026-08-11 — Steam discovery and regional storefront snapshots completed

**What changed:**

- Replaced the deprecated catalog assumption with paginated incremental `IStoreService/GetAppList` synchronization and protected header-based key submission.
- Added durable local catalog search plus a replaceable best-effort unkeyed Steam Store fallback.
- Expanded immutable Steam Metadata Snapshots with regional price provenance, descriptions, publishers, genres, tags, features, platforms, DLC/demo/package facts, and safe Steam-hosted media.
- Added grouped storefront presentation to previews and reports, with plain-text sanitization, explicit unknown states, ordinary Steam attribution links, and user-activated trailer navigation.
- Documented Steam key, privacy, attribution, request ceiling, as-is, and termination-cleanup obligations.

**Why:**

- Valve documents `IStoreService/GetAppList` as the scalable replacement for deprecated `ISteamApps/GetAppList` and provides incremental timestamps and cursor pagination.
- Optional Store endpoints and HTML are undocumented, so their replaceable adapter never blocks direct-AppID analysis and records missing provenance rather than inventing support.
- Preserving Steam's formatted regional price and country avoids silent or inaccurate currency conversion.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Full acquisition and local data lifecycle completed

**What changed:**

- Added resumable Full acquisition and explicit reconciliation jobs to the existing durable runner.
- Recorded reconciliation presence and missing review identifiers without deleting Review Revisions or changing historical reports.
- Added local storage diagnostics, database-integrity checks, and exact-confirmation deletion for Report Versions, inactive incomplete jobs, and complete Game Datasets.
- Added UI controls for maintenance, recovery guidance, storage inspection, and destructive confirmation.
- Retained Steam's `recent` cursor mode for complete scans because its official API documentation identifies `recent` or `updated` as the modes that eventually return an empty page; `all` is limited to a 365-day window and continually returns results.

**Why:**

- Reusing the durable job runner provides checkpoints, cancellation, retry, and restart recovery without a second ingestion pipeline.
- SQLite ownership cascades and a write-locked active-job check make deletion small, explicit, and orphan-safe.
- Historical evidence remains immutable even when Steam no longer returns a previously retained review.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Append-only refresh and immutable report history completed

**What changed:**

- Added refresh jobs that reuse durable acquisition checkpoints while appending only new or edited Review Revisions.
- Checkpointed the exact latest retained revision for every review at refresh completion and built provider-neutral reanalysis requests from that corpus.
- Added Report Version 2.0 with an owned Steam metadata snapshot and migrated stored 1.0 snapshots so later dataset changes cannot alter historical presentation.
- Added newest-first report-history persistence and HTTP contracts plus native report-history, refresh, progress, and retry controls.
- Verified a fixture refresh through new Report Version creation while historical report, evidence, and metadata bytes remained unchanged.

**Why:**

- Reusing one durable job mechanism keeps cancellation, retry, restart recovery, and page checkpoints consistent across initial and refresh acquisition.
- Metadata must live inside the typed report snapshot; reading mutable current Game Dataset metadata would make historical reports change after refresh.
- Pre-2.0 snapshots are upgraded once with the current retained metadata because the earlier schema did not preserve their historical metadata value.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Safe report export and local-evidence re-import completed

**What changed:**

- Added versioned JSON, relationship-preserving CSV, and escaped standalone HTML report exports through HTTP download endpoints.
- Added strict JSON re-import that fingerprints normalized evidence and resolves every exact matching local Review Revision before appending a Report Version.
- Kept full review text opt-in for JSON and CSV with an explicit privacy warning; default artifacts omit full text and reviewer identity.
- Added unsafe markup, unsafe media URL, undeclared secret/identity field, and spreadsheet-formula injection coverage.
- Allowed fixture-backed refresh implementation to proceed while real-world analysis calibration remains an acceptance gate.

**Why:**

- Known versioned contracts and exact local evidence matching provide useful portability without misrepresenting default JSON as a self-contained backup.
- Standard-library JSON, CSV, HTML escaping, and URL parsing cover the approved formats without a new export dependency.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Fixture-backed report exploration completed

**What changed:**

- Added a dependency-free report route with ranked positive, negative, and Technical Theme presentations.
- Added category filtering, single-open Theme details, linked mixed reception, representative evidence, and on-demand full-review context.
- Displayed immutable report scope, provenance, support denominators, and calibration status from the report API.
- Allowed export-contract implementation to proceed while connected-browser report acceptance remains a human gate.

**Why:**

- Native links, controls, and CSS provide the approved evidence exploration without adding a router or UI dependency.
- The unavailable connected-browser runtime should not block independently testable export contracts.

**New issues:**

- None.

**Needs human judgment:**

- Complete the existing connected-browser responsive and accessibility acceptance task when that runtime is available.

---

## 2026-08-11 — Report summary and evidence APIs added

**What changed:**

- Added a bounded immutable report summary endpoint with game identity, exact scope, provenance, ranked design and Technical Themes, mixed reception, categories, support denominators, and representative evidence.
- Added a separate complete-evidence endpoint that joins every Theme Opinion Point to its exact locally stored Review Revision and context.
- Allowed fixture-backed Slice 5 implementation to proceed while retaining connected-browser and real-world calibration acceptance gates.

**Why:**

- Separating bounded summaries from complete evidence keeps initial report payloads manageable without weakening traceability.

**New issues:**

- None.

**Needs human judgment:**

- None until the existing browser and calibration gates resume.

---

## 2026-08-11 — Provisional Manual Codex report path completed

**What changed:**

- Added one application operation that validates a Manual Codex result, calculates deterministic metrics, creates a typed provisional snapshot, and appends it to the Report Version repository.
- Verified the complete path with the approved synthetic evaluation fixture and exact persisted Review Revision bindings.
- Fixed a migration test that unnecessarily hard-coded the previous schema version.

**Why:**

- One narrow orchestration boundary proves the backend stages compose without adding report HTTP or UI surfaces prematurely.

**New issues:**

- None.

**Needs human judgment:**

- None until real-world calibration resumes.

---

## 2026-08-11 — Typed immutable Report Versions persisted

**What changed:**

- Added frozen domain contracts for metric values and complete Report Version snapshots.
- Added schema migration 4 with foreign-key bindings to exact Review Revisions and a repository that only inserts or loads snapshots.
- Added transactional ownership and analysis-scope checks, plus load-time binding verification.
- Rejected duplicate Report Version identifiers instead of replacing historical snapshots.

**Why:**

- Historical reports must preserve the validated analysis, calculated metrics, explicit threshold policy, calibration status, provider provenance, and exact evidence scope as one reproducible value.

**New issues:**

- Whole-snapshot JSON retrieval is intentionally not optimized for cross-report analytics.

No task was added because cross-report analytics is outside the approved single-game MVP scope.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Deterministic Theme metrics implemented

**What changed:**

- Derived Theme support from distinct Review Revision memberships and the complete report scope.
- Added global positive and negative headline caps, separate Technical Theme thresholds, taxonomy retention, and deterministic ranking.
- Derived liked, disliked, mixed, and mentioned denominators directly from opposing Theme memberships.
- Required callers to supply all currently provisional thresholds explicitly.

**Why:**

- Generated counts cannot be authoritative. Keeping threshold policy outside the calculation prevents deferred calibration values from becoming hidden defaults.

**New issues:**

- None.

**Needs human judgment:**

- Calibrate and approve threshold inputs before production-quality acceptance.

---

## 2026-08-11 — Slice 4 implementation unblocked from calibration

**What changed:**

- Allowed deterministic metrics, immutable report persistence, and fixture-based end-to-end implementation to proceed with explicit provisional thresholds.
- Kept real-game baseline approval as a production-quality acceptance gate rather than a prerequisite for writing Slice 4 code.

**Why:**

- Postponing expensive calibration should prevent reliability claims, not prevent implementation whose behavior can be verified with deterministic fixtures.

**New issues:**

- Provisional thresholds must remain visibly identified and must not be presented as calibrated defaults.

The existing deferred threshold-calibration and baseline-approval tasks cover this issue.

**Needs human judgment:**

- Approve calibrated thresholds before production-quality acceptance.

---

## 2026-08-11 — Bulk calibration postponed

**What changed:**

- Deferred the remaining 59 extraction batches, bounded consolidation runs, stability scoring, and threshold calibration.
- Retained the local corpus, prepared packages, and rejected pilot output for a future approved bulk-inference path.

**Why:**

- The user chose not to spend further time or provider cost after the Codex CLI pilot exceeded five minutes and failed exact-evidence validation.

**New issues:**

- None beyond the existing unsatisfied analysis-quality gate.

**Needs human judgment:**

- Resume calibration and approve a bulk-inference path before the analysis-quality baseline can be approved.

---

## 2026-08-11 — Codex CLI rejected for bulk extraction

**What changed:**

- Ran one 250-review Hades II extraction pilot and added a reusable batch-output validator.
- Stopped before the remaining 59 batches after the pilot exceeded five minutes and failed exact-excerpt validation.

**Why:**

- At the observed runtime, sequential extraction would take hours, and the first output still required repair. The agentic file-driven CLI is not an economical bulk-inference surface.

**New issues:**

- Bulk extraction needs an explicitly approved execution path, preferably a direct structured-output API.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Choose direct API inference or postpone the 15,000-review calibration.

---

## 2026-08-11 — Stability evaluation restored to batch-first analysis

**What changed:**

- Stopped monolithic 5,000-review discovery runs before scoring or threshold calibration.
- Added an Opinion Point-only batch contract that reuses exact-scope and exact-excerpt validation.
- Prepared 60 isolated 250-review extraction packages covering all 15,000 approved reviews once.
- Moved repeated stability trials to bounded consolidation over validated Opinion Points, with deterministic support calculation afterward.

**Why:**

- Monolithic runs were slow and returned sampled support memberships, which cannot produce auditable support counts or threshold calibration. The approved design already requires batch extraction before cross-batch consolidation.

**New issues:**

- Cross-batch consolidation must preserve every assigned Opinion Point identifier while merging paraphrases over bounded passes.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Approve the resulting stability metrics and provisional thresholds after the revised experiment completes.

---

## 2026-08-11 — Empty stability results rejected

**What changed:**

- Required every stability result to contain 1–60 Themes after Hades II interleaved returned an empty Theme list.
- Preserved that first output as rejected and regenerated all isolated run schemas before retrying.

**Why:**

- A structurally valid but empty result cannot measure headline-Theme stability and must fail at the provider boundary.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Evidence-only stability repair approved

**What changed:**

- Added a strict repair contract containing only explicitly rejected Theme keys and replacement representative excerpts.
- Added a deterministic merge that preserves all other result fields and revalidates the complete result against the exact run input.
- Repaired the single invalid Hades II contiguous Theme on the first targeted attempt; the resulting 16-Theme output passed strict validation.

**Why:**

- Whole-result regeneration allowed Luna to change valid evidence while fixing one rejected excerpt. A narrow contract makes unrelated mutation structurally impossible.

**New issues:**

- None.

**Needs human judgment:**

- None until the repeated-run metrics and provisional thresholds are ready.

---

## 2026-08-11 — Luna stability run stopped after three evidence failures

**What changed:**

- Isolated each repeated stability run in a filesystem root containing only its input and schema after detecting that a run could see prior outputs.
- Completed three valid independent Stardew Valley partitions.
- Stopped the Hades II contiguous run after three strict-validation failures and did not start the remaining five runs.

**Why:**

- Repeated runs must be independent, and invalid evidence cannot be silently corrected or included in stability metrics.
- The final full-result repair changed unrelated evidence, showing that whole-result regeneration is too broad for a one-excerpt correction.

**New issues:**

- Luna needs either a targeted evidence-only repair contract that cannot alter unrelated Themes or replacement by a stronger model for this experiment.

The new issue above was added to `TASKS.md` as a human decision.

**Needs human judgment:**

- Approve the targeted repair contract or select a stronger model and rerun strategy.

---

## 2026-08-11 — Luna medium selected for stability evaluation

**What changed:**

- Pinned the approved stability provider to `gpt-5.6-luna` with medium reasoning.
- Added three deterministic full-corpus partition strategies and privacy-minimized run inputs.
- Added a strict stability-result schema and validator for run metadata, unique support membership, known Review Revisions, and exact excerpts.
- Preserved two rejected first-run outputs before accepting the third provider-repaired result.

**Why:**

- Luna reduces repeated-run cost while directly testing whether the cheaper intended option can produce stable evidence-backed Themes.
- Provider-generated evidence must pass the same exact-source boundary as production analysis; silent local correction would invalidate the experiment.

**New issues:**

- Luna may require a bounded schema-preserving repair pass to satisfy cross-field evidence relationships on 5,000-review results.

The existing provider reliability and malformed-output tasks cover this issue.

**Needs human judgment:**

- None until the repeated-run metrics and provisional thresholds are ready.

---

## 2026-08-11 — Natural-distribution stability corpus acquired

**What changed:**

- Extended the existing evaluation acquisition script with a natural, source-ordered per-game cap while retaining its balanced human-review mode.
- Downloaded and validated 5,000 unique eligible reviews for each approved game into the gitignored local evaluation directory.
- Deferred all model runs pending explicit approval for external processing and a pinned evaluation model.

**Why:**

- Headline stability must be measured on the actual recent recommendation distribution rather than the deliberately balanced human-label pilot.

**New issues:**

- The repeated Codex experiment will transmit approximately 10.95 MB of public Steam review data and consume substantial provider quota.

The new issue above was added to `TASKS.md` as a human approval gate.

**Needs human judgment:**

- Approve external processing and the exact Codex model before the nine-run minimum begins.

---

## 2026-08-11 — Minimal Manual Codex evaluation path moved before quality approval

**What changed:**

- Added strict versioned Analysis Provider request and result contracts.
- Added privacy-minimized Manual Codex package export with a deterministic exact-scope digest.
- Added one strict import boundary for schema, scope, completion, identifier, exact-excerpt, Theme-membership, polarity, opposition, and classification validation.
- Kept report persistence, metrics, and UI integration behind the analysis-quality approval gate.

**Why:**

- The user approved resolving the gate-order cycle by moving only the provider path needed to perform the required repeated stability experiment.

**New issues:**

- Deterministic validation cannot prove semantic summary faithfulness; it remains a human/provider evaluation check.

The existing summary-faithfulness evaluation task covers this issue.

**Needs human judgment:**

- Approve the evaluation baseline and provisional thresholds after the repeated provider runs.

---

## 2026-08-11 — Analysis-quality gate ordering cycle identified

**What changed:**

- Recorded that the 5,000-review stability requirement cannot run in the current Slice 4 order.
- Made no change to the approved gate or implementation order.

**Why:**

- The evaluation specification requires at least three provider runs, but the Analysis Provider schema and Manual Codex workflow are currently blocked until that evaluation baseline is approved.

**New issues:**

- The Slice 4 gate must permit a minimal evaluation-only provider path before stability and threshold calibration can be completed.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Approve moving the versioned provider schema and Manual Codex export/import validation ahead of the stability experiment, or revise the experiment requirement.

---

## 2026-08-11 — Pilot extraction recall established

**What changed:**

- Added the two human-approved missing Opinion Point spans to a local extraction-only gold artifact.
- Recorded pilot extraction precision of 100%, recall of 95.0%, and F1 of 97.4%.
- Kept sentiment, category, and Theme labels absent from the new spans because the correction round did not ask the reviewer to judge those fields.

**Why:**

- Extraction recall requires human-reviewed missing spans, while inventing unreviewed semantic labels would weaken the gold set.

**New issues:**

- None.

**Needs human judgment:**

- None until the broader evaluation baseline and provisional thresholds are ready for approval.

---

## 2026-08-11 — Pilot quality follow-up completed

**What changed:**

- Recorded all 35 human quality judgments: 17 of 18 reviews had complete Opinion Point coverage, and every selected grouping, summary, opposing-link, and review-classification case passed.
- Prepared a four-button correction round for the exact candidate spans omitted from the one incomplete Hades II review.
- Kept extraction recall unreported until those missing spans are human-adjudicated.

**Why:**

- A completeness failure identifies an incomplete review but does not by itself define the gold Opinion Points needed for recall scoring.

**New issues:**

- None.

**Needs human judgment:**

- Accept or reject the four proposed missing Opinion Points before extraction recall is calculated.

---

## 2026-08-11 — Follow-up quality judgments made button-only

**What changed:**

- Extended the local labeler to run generic choice-based quality rounds alongside Opinion Point correction rounds.
- Prepared 35 explicit completeness, grouping, summary, opposing-link, and review-classification judgments from the adjudicated pilot.
- Removed the proposed Hades difficulty opposition after the human-neutral correction eliminated its negative Theme.

**Why:**

- Explicit pair and completeness judgments close measurement gaps without asking the reviewer to author labels in a terminal or blank form.

**New issues:**

- None.

**Needs human judgment:**

- Complete and export the prepared pilot quality round.

---

## 2026-08-11 — First Opinion Point pilot adjudicated

**What changed:**

- Converted all 38 reviewed candidate decisions into a local adjudicated corpus.
- Recorded candidate precision and field-level agreement, including the corrected neutral difficulty description.
- Kept extraction recall, pairwise grouping, summaries, opposing links, and thresholds explicitly unmeasured.

**Why:**

- Candidate approval is useful evidence, but treating an anchored review round as a complete accuracy evaluation would overstate reliability.

**New issues:**

- The next human round needs explicit missing-point, pairwise grouping, opposing-link, and summary-faithfulness judgments.

**Needs human judgment:**

- Review those follow-up judgments before approving the evaluation baseline.

---

## 2026-08-11 — First real-game human review round prepared

**What changed:**

- Added deterministic source-order selection for equal Recommended and Not Recommended evaluation quotas.
- Fixed both live Steam adapters to pass `urllib` timeouts by keyword and skipped blank recommendation-only review entries.
- Downloaded a local 60-review pool and prepared an 18-review pilot containing 38 candidate Opinion Points for the browser labeler.

**Why:**

- A small balanced pilot exposes sentiment and usability failures before expanding human labeling, while the later 5,000-review stability evaluation preserves natural recommendation distribution.

**New issues:**

- None. Both live-data defects found during acquisition were fixed at the shared adapter boundary with regression coverage.

**Needs human judgment:**

- Visually verify the labeler, review the pilot candidates, and export the completed JSON.

---

## 2026-08-11 — Human gold-label review moved into a local browser tool

**What changed:**

- Added a self-contained review-labeling page with candidate approval, button corrections, keyboard shortcuts, autosave, progress, rejection, and reviewed-JSON export.
- Kept raw corpus and reviewed files under the gitignored `evaluation-data/` directory.

**Why:**

- Human review should feel like a short classification round rather than terminal data entry, while the exported JSON provides a deterministic handoff back to Codex.

**New issues:**

- Connected-browser visual verification remains unavailable in the current tool runtime; jsdom interaction coverage and the production build are the automated boundary.

**Needs human judgment:**

- The user must visually confirm the local labeling experience when the first real candidate corpus is ready.

---

## 2026-08-11 — Evaluation games and human reviewer approved

**What changed:**

- Approved Hades II, Stardew Valley, and Cyberpunk 2077 for the initial real-game evaluation corpus.
- Confirmed the user will independently review candidate gold labels.
- Clarified that the benchmark evaluates prompts, schemas, validation, and thresholds; it does not train a model.

**Why:**

- The three games provide different design and technical feedback patterns, while independent human review prevents provider output from defining its own ground truth.

**New issues:**

- The raw-review storage policy is still unresolved.

**Needs human judgment:**

- Decide whether raw review text remains local and gitignored or is committed to the repository.

---

## 2026-08-11 — Provider-independent evaluation format established

**What changed:**

- Defined versioned gold labels and deterministic scoring for extraction, sentiment, neutrality, grouping, categories, evidence, opposing links, and review classification.
- Added three synthetic conformance cases with an integrity test.

**Why:**

- The corpus can now be labeled consistently before any provider schema exists, while synthetic examples remain explicitly excluded from real-game threshold calibration.

**New issues:**

- None beyond the existing real-corpus and independent-annotation approval gate.

**Needs human judgment:**

- The recorded corpus, storage, and gold-label decisions remain open.

---

## 2026-08-11 — Analysis-quality evaluation corpus requires approval

**What changed:**

- Recorded a human gate for the real-game review corpus, its repository/storage policy, and an independent gold-label process before Slice 4 evaluation begins.

**Why:**

- The approved design requires real-game calibration. Synthetic samples cannot establish headline stability, and provider-generated labels cannot serve as independent ground truth for evaluating that provider.

**New issues:**

- No legally/privacy-reviewed real-review corpus or independent annotation process is currently available in the repository.

**Needs human judgment:**

- Select the corpus source and games, decide whether review text may be committed or must remain local, and identify who approves gold labels.

---

## 2026-08-11 — Durable Quick import slice completed

**What changed:**

- Added browser-refresh reattachment through one stored job identifier.
- Verified application restart resumes an interrupted import from its persisted cursor.
- Marked Slice 3 complete and advanced the documented implementation frontier to Slice 4.

**Why:**

- The backend remains authoritative for job state while the browser stores only enough identity to reconnect.

**New issues:**

- None.

**Needs human judgment:**

- Slice 4 still requires explicit approval of the evaluation baseline and provisional reliability thresholds.

---

## 2026-08-11 — Quick setup and durable progress added to the Catalog

**What changed:**

- Added a configurable Quick review limit and in-place queued, running, failed, cancelled, and completed states.
- Added polling plus cancellation and retry controls against the durable job API.

**Why:**

- Extending the confirmed-game panel delivers the current slice without creating a separate setup route before provider configuration exists.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Quick import API made asynchronous and recoverable

**What changed:**

- Added start, progress, cancellation, and retry endpoints backed by one process-local import worker.
- Startup requeues interrupted jobs from their last durable checkpoint.
- Corrected a stale Game Dataset test that still assumed the pre-job schema version.

**Why:**

- A standard-library single-worker executor keeps HTTP requests responsive without introducing a second queue or concurrency model.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Durable Quick Job Runner implemented

**What changed:**

- Added queued/running/terminal transitions, durable cancellation, retry, restart requeue, and atomic review-page checkpoints.
- Kept the runner with its SQLite and Steam infrastructure behind one `run(job_id)` interface instead of adding an unused persistence port.

**Why:**

- Atomic page persistence prevents review evidence and progress cursors from diverging after interruption.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Steam Review Revisions made append-only

**What changed:**

- Added duplicate-safe review ownership and content-hashed immutable revision insertion.
- Same-timestamp content edits append a distinct revision instead of mutating prior evidence.

**Why:**

- A canonical JSON hash gives exact change detection with less code than comparing every review field.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Paginated Steam review adapter added

**What changed:**

- Added normalized English review pages with cursor encoding, off-topic filtering, pacing, three bounded attempts, source exhaustion, and repetition detection.
- Kept reviewer identity out of the normalized review contract.

**Why:**

- Page-sized output is the smallest seam that supports durable checkpoints and privacy-minimized local persistence.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Durable import schema established

**What changed:**

- Added schema migration 3 for Game Dataset-owned reviews, immutable Review Revisions, Analysis Jobs, and ordered checkpoints.
- Added SQLite constraints for ownership, valid scopes/states, counters, and cancellation flags.

**Why:**

- Durable import correctness belongs in the database so every runner and recovery path shares the same invariants.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Direct-AppID preview slice completed

**What changed:**

- Marked Slice 2 complete and advanced durable Quick review import to the next execution frontier.

**Why:**

- Valid, invalid, missing, malformed, and partial fixtures now prove normalization, persistence, API behavior, and the confirmation interface without optional-source failures blocking a valid preview.

**New issues:**

- None.

**Needs human judgment:**

- None.

**Verification:**

- Backend: 22 tests passed.
- Frontend: 3 tests passed; strict type checking and production build passed.
- Connected-browser automation was unavailable in this environment; the existing Slice 0 browser checks remain open.

---

## 2026-08-11 — Steam capsule sources restricted

**What changed:**

- Normalized capsule artwork only from HTTPS `steamstatic.com` hosts; other optional media becomes unavailable.
- Renamed the adapter test module to prevent full-suite collection collisions.

**Why:**

- Store metadata is untrusted input and must not make the frontend request arbitrary URLs.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Direct-AppID Catalog confirmation built

**What changed:**

- Replaced the placeholder shell with the first production Catalog surface for direct AppID preview and identity confirmation.
- Established shared forest, sage, neutral, spacing, radius, shadow, and motion tokens with responsive and reduced-motion behavior.

**Why:**

- Slice 2 needs identity confirmation now; name search and report setup remain owned by later slices.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Direct-AppID preview API exposed

**What changed:**

- Added validated direct-AppID preview behavior with explicit not-found, malformed-source, and temporary-source responses.
- Successful previews persist before returning to the frontend.

**Why:**

- One synchronous metadata request is bounded and does not need the durable Job Runner introduced in Slice 3.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Initial Game Dataset preview persisted

**What changed:**

- Added schema migration 2 and SQLite round-trip persistence for one current normalized metadata preview per AppID.

**Why:**

- Slice 2 needs durable game identity without prematurely creating immutable Report Version snapshot history.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Steam storefront metadata adapter added

**What changed:**

- Added a replaceable, timeout-bounded storefront adapter that normalizes one AppID through the tested metadata contract.
- Kept missing games, malformed responses, and transient source failures distinct.

**Why:**

- The standard-library HTTP boundary is sufficient for one best-effort request and avoids a new runtime dependency.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Steam preview unknowns made explicit

**What changed:**

- Added a normalized Steam Metadata contract with nullable optional values, an exact `missing_fields` set, and complete/partial source status.

**Why:**

- Consumers can distinguish unavailable source data from unsupported features without a wrapper type around every field.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Application-shell slice completed

**What changed:**

- Marked Slice 1 complete and advanced Slice 2 to the next execution frontier.
- Documented the frozen local development and production-serving workflow.

**Why:**

- Fresh locked installs, all suites, the production build, advisory checks, and real-server frontend/API requests now satisfy the shell delivery gates.

**New issues:**

- None.

**Needs human judgment:**

- None.

**Verification:**

- Backend: 5 tests passed with no warnings.
- Frontend: 2 tests passed; strict type checking and production build passed.
- Dependency audit: 0 frontend vulnerabilities; both lockfiles verified through frozen installs.
- Runtime: the locked FastAPI process returned `200` for the compiled frontend and `ok` from `/api/health`.

---

## 2026-08-11 — Shell API prefix made stable

**What changed:**

- Removed the backend-only API-prefix environment override and made `/api` a literal backend/frontend contract.

**Why:**

- A compiled frontend must know the prefix before it can request configuration, so a runtime override could only make the shell unreachable.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Dependency installation frozen and warnings resolved

**What changed:**

- Added a cross-platform `uv.lock` and changed backend CI to `uv sync --locked`.
- Changed frontend CI to `npm ci` with the existing lockfile.
- Replaced deprecated `httpx` test-client compatibility with `httpx2`.
- Updated Vite, Vitest, the React plugin, and jsdom to supported releases after a frozen install exposed five advisories.

**Why:**

- Frozen installs must resolve the same tested dependency graph locally and in CI without retaining known high or critical advisories.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — FastAPI serves the compiled frontend

**What changed:**

- Mounted an available compiled frontend directory at `/` after registering API routes.
- Added a configurable frontend distribution path for source and packaged layouts.

**Why:**

- FastAPI's native static-file support provides the production delivery path without a second server or custom file handling.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Shell API contracts validated at runtime

**What changed:**

- Added explicit FastAPI response models for health and public configuration.
- Added small TypeScript response validators and required both shell endpoints before reporting backend connectivity.

**Why:**

- Static TypeScript types alone cannot validate untrusted HTTP payloads, while code generation is unnecessary for two stable endpoints.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Implementation plan and task frontier synchronized

**What changed:**

- Marked Slice 0 approved and Slice 1 as the current execution frontier.
- Added the approved two-root structure, typed API contracts, production asset serving, reproducible dependency installation, and framework compatibility to Slice 1 scope and acceptance.
- Made the analysis-quality and first-provider human approvals explicit blockers in their respective slices.
- Removed initial frontend-serving responsibility from the packaging slice and marked the prototype approval gate satisfied.
- Corrected the design status to acknowledge the implemented application shell.

**Why:**

- The strategic plan and live checklist had stale frontier and approval language after prototype approval and shell implementation began.
- Clean installation is not reproducible until Python dependency resolution and frozen CI installation are defined.

**New issues:**

- Establish reproducible dependency locking and frozen CI installation.
- Resolve or explicitly constrain the FastAPI/Starlette test-client deprecation warning.

Both issues are tracked in the current `2026-08-11` Slice 1 activity checklist in `TASKS.md`.

**Needs human judgment:**

- None at the current frontier.

---

## 2026-08-11 — Legacy .NET and Rider artifacts removed

**What changed:**

- Removed the empty `GameReviewAnalyzer.sln` placeholder from the abandoned .NET setup.
- Removed project-local `.idea/` Rider metadata and added `.idea/` to `.gitignore`.

**Why:**

- The approved implementation uses Python/FastAPI and TypeScript/React, so the solution file and IDE metadata no longer describe or support the build.
- Ignoring IDE-local metadata prevents machine-specific workspace state from returning to source control.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-11 — Two-root repository structure approved and applied

**What changed:**

- Retained separate `backend/` and `frontend/` roots for Python and TypeScript tooling.
- Reorganized backend code into a packaged `src/game_review_analyzer/` layout with domain, application, interface, infrastructure, and shared boundaries.
- Moved the React shell under `frontend/src/app/`, global styling under `frontend/src/styles/`, and integration coverage under `frontend/tests/`.
- Normalized maintained specifications under lowercase `docs/specifications/` and documented the structure in `AGENTS.md`.

**Why:**

- This keeps each language ecosystem conventional while preserving the ownership and dependency boundaries recommended by the initialization workflow.
- Directories are added only when they own real content, avoiding empty structural placeholders.

**New issues:**

- `GameReviewAnalyzer.sln` is a legacy placeholder from before the Python/TypeScript stack was established and no longer represents the build.

The issue is tracked in `TASKS.md` for explicit cleanup approval.

**Needs human judgment:**

- Decide whether the legacy solution file should be removed.

**Verification:**

- Backend characterization suite: 3 passed.
- Frontend characterization suite: 1 passed.
- Strict TypeScript checking and Vite production build passed.
- Editable backend package reinstall succeeded after allowing pip network access for isolated build dependencies.

---

## 2026-08-11 — Slice 1 application shell started

**What changed:**

- Added the initial FastAPI backend with `/api/health` and public `/api/config` endpoints.
- Added SQLite schema initialization with a versioned migration table and a minimal metadata table.
- Added the React/Vite frontend shell with backend-health status feedback and the approved neutral/forest-green foundation.
- Added backend/frontend test and build commands plus a GitHub Actions CI workflow.

**Why:**

- The combined workflow is approved, so the project can now establish a verifiable local delivery path before Steam and analysis features are added.
- Health, configuration, and migration seams provide a small vertical slice without prematurely coupling the app to Steam or an analysis provider.

**New issues:**

- Typed API contracts, production asset serving, and clean-install verification remain open Slice 1 tasks.
- Dependencies have since been installed locally. Backend tests pass (3 tests), frontend tests pass (1 test), and the frontend type-check plus production build pass. The first sandboxed frontend run was blocked by esbuild path permissions; the elevated retry succeeded.

These issues remain tracked in `TASKS.md`.

**Needs human judgment:**

- None for the application shell.

---

## 2026-08-10 — Combined workflow approved

**What changed:**

- Approved the combined prototype flow: Catalog → Split configuration → Timeline progress → Research report.
- Confirmed that this direction is ready to guide implementation, while the individual prototype files remain retained for reference.
- Confirmed that production code and shared design tokens are still deferred until the user explicitly starts implementation.

**Why:**

- The four approved surfaces now describe one coherent journey from game selection through report reading.
- Separating approval from implementation preserves the user's quota and keeps the implementation gate explicit.

**New issues:**

- Connected-browser verification for laptop, narrow-width, keyboard, non-color, reduced-motion, and console behavior remains open.
- Shared production design tokens remain an implementation-foundation task.

Both issues remain tracked in `TASKS.md`.

**Needs human judgment:**

- None for the combined workflow. A later explicit implementation request is required before production code changes.

---

## 2026-08-10 — Approved prototype theme consolidated

**What changed:**

- Aligned the approved Split configuration surface with the Catalog, Timeline, and Research visual language.
- Replaced Split's blue palette with the shared forest-green brand color, sage disclosure surfaces, warm-neutral page background, and matching border hierarchy.
- Left unselected Editorial and Canvas explorations unchanged as historical alternatives.

**Why:**

- The approved workflow should feel like one research tool even though each surface has a different interaction model.
- Preserving unselected variants keeps the original design exploration intact while making the approved path coherent.

**New issues:**

- Production implementation still needs shared design tokens rather than per-prototype CSS values.

The follow-up remains covered by the production scaffolding task in `TASKS.md`.

**Needs human judgment:**

- None for the approved prototype theme.

---

## 2026-08-10 — Combined workflow static audit completed

**What changed:**

- Reviewed the approved flow as Catalog → Split configuration → Timeline progress → Research report.
- Confirmed that each surface covers its intended handoff and includes responsive and reduced-motion branches in the prototype CSS.
- Identified shared visual-token consolidation as a production integration task because the exploratory surfaces intentionally use different palettes.

**Why:**

- A single workflow should preserve the approved interaction models without feeling like four unrelated products.
- Static review can confirm the documented sequence and source-level coverage, while visual laptop/narrow and console verification still needs a connected browser.

**New issues:**

- Connected-browser laptop, narrow-width, keyboard, non-color, reduced-motion, and console verification remains open.
- Prototype-specific visual tokens need consolidation during production scaffolding.

Both issues remain tracked in `TASKS.md` under Slice 0 and the current implementation foundation work.

**Needs human judgment:**

- Approve the combined workflow after live verification.

---

## 2026-08-10 — Timeline durable progress approved

**What changed:**

- Promoted the Timeline durable-progress variant as the approved direction.
- Defined durable progress around a stage timeline showing completed, current, and upcoming work, percentage, elapsed time, checkpoint safety, and calm recovery controls.
- Retained the durable-progress exploration file under the project prototype-retention rule.

**Why:**

- A stage timeline makes long-running work legible without turning normal processing into an operations console.
- Explicit checkpoint language supports closing and returning later while keeping cancellation and resume discoverable.

**New issues:**

- Connected-browser verification remains open for responsive timeline stacking, cancellation/resume state changes, keyboard behavior, and reduced motion.

The new issue above remains covered by the combined-workflow verification tasks in `TASKS.md`.

**Needs human judgment:**

- None for the durable-progress direction. The next gate is combined-workflow review.

---

## 2026-08-10 — Prototype cleanup rule corrected

**What changed:**

- Added a project-specific rule to retain prototype explorations after selection until production integration is complete and cleanup is explicitly approved.
- Clarified that promotion during prototype-only work means recording the selected direction in design artifacts, not deleting the exploration file.

**Why:**

- The previous cleanup was applied inconsistently and removed a useful visual reference before production implementation existed.
- Keeping explorations available supports later review, regression comparison, and implementation handoff.

**New issues:**

- The previously deleted `analysis-configuration.html` exploration remains unavailable and may need recreation if the original picker is still desired.

This issue is recorded for user direction rather than added as an implementation task.

**Needs human judgment:**

- Decide later whether to recreate the retired analysis-configuration exploration.

---

## 2026-08-10 — Split analysis configuration approved

**What changed:**

- Promoted the Split analysis-configuration variant as the approved direction.
- Defined the configuration surface as side-by-side review-scope/provider controls and a live processing-disclosure panel.
- Retired the three-way analysis-configuration exploration after selection, per the prototype workflow.

**Why:**

- Keeping configuration and consequences visible together makes review volume, time, cost, and processing location easier to understand before creating a report.
- The split layout preserves the product's research-tool character without turning setup into a long wizard.

**New issues:**

- Connected-browser verification remains open for the promoted direction's responsive stacking, provider disclosure changes, keyboard behavior, and non-color communication.

The new issue above remains covered by the upcoming combined-workflow review tasks in `TASKS.md`.

**Needs human judgment:**

- The next human gate is durable progress, cancellation, retry, and resume direction selection.

---

## 2026-08-10 — Catalog direction explicitly approved

**What changed:**

- Recorded the user's final approval of the Catalog game-selection direction, including its prominent latest-report tile, report-history dialog, and `Create report` action.
- Closed the game-selection design choice and moved the prototype frontier to analysis configuration and processing disclosure.

**Why:**

- The Catalog hierarchy now reflects the primary returning-user task while preserving first-time report creation.
- Recording the approval prevents later prototype work from reopening a settled game-selection decision.

**New issues:**

- None beyond the existing connected-browser verification task.

**Needs human judgment:**

- The next human gate is analysis-configuration direction selection.

---

## 2026-08-10 — Latest report emphasis increased and creation CTA restored

**What changed:**

- Strengthened the latest-report tile with a deeper green gradient, subtle gold accent, larger type, and a larger click target.
- Restored `Create report` as the primary button while leaving `Show all reports` secondary.

**Why:**

- The latest report is the most important returning-user action and needed clearer visual priority.
- Creating a report remains a legitimate next step for both first-time and existing-game flows, so demoting it too far made the action harder to discover.

**New issues:**

- Connected-browser visual verification remains open for the stronger contrast, responsive tile size, and reduced-motion behavior.

The new issue above remains covered by the existing game-selection verification task in `TASKS.md`.

**Needs human judgment:**

- None for this visual-priority adjustment.

---

## 2026-08-10 — Latest report prioritized and report creation terminology settled

**What changed:**

- Made the entire latest-report card the prominent Catalog action, using a restrained green-tinted surface that fits the existing neutral palette.
- Replaced the prominent analysis CTA with a quiet `Create report` action.
- Added a lightweight report-history dialog scoped to the selected game, with whole-row report selection and Escape/outside-click dismissal.
- Standardized `Create report` as the operation that generates a first or later immutable Report Version.

**Why:**

- Opening an existing report is the primary returning-user task; creating another report should remain available without competing visually.
- A focused history dialog supports multiple Quick versions without turning the Catalog preview into a second library.
- “Update report” implies mutation, while “Compare reports” would promise a feature that is not yet implemented.

**New issues:**

- Connected-browser visual verification remains open for the new card, dialog focus behavior, responsive layout, and reduced-motion state.

The new issue above remains covered by the existing game-selection verification task in `TASKS.md`.

**Needs human judgment:**

- None for this terminology and Catalog interaction revision.

---

## 2026-08-10 — Catalog selected with integrated report access

**What changed:**

- Selected Catalog as the game-selection foundation and integrated Library-style recent-report access into its right preview panel.
- Replaced Catalog's empty initial prompt with three compact recent reports.
- Kept AppID, release, status, and review availability visible after game selection.
- Added a lightweight existing-report summary beneath those identity facts with actions to open the latest report or start a new analysis.
- Added a direct way to return from game confirmation to recent reports while keeping the panel footprint stable.

**Why:**

- Catalog provides the preferred dense game-discovery workflow, while Library made previous reports substantially easier to find.
- Existing reports are a continuation path, but they should not replace the identity information needed to prevent selection mistakes.
- Reusing the preview panel keeps both paths available without adding another navigation surface.

**New issues:**

- Live connected-browser verification remains unavailable and must still cover state changes, responsive behavior, keyboard access, console output, and stable layout.

The new issue above remains covered by the existing game-selection verification task in `TASKS.md`.

**Needs human judgment:**

- None for the game-selection direction. The remaining prototype surfaces and combined-workflow approval retain their existing gates.

---

## 2026-08-10 — Project documentation lifecycle revised

**What changed:**

- Added `AGENTS.md` as the repository's persistent workflow authority.
- Changed project initialization to create only an interview-based `README.md` project brief.
- Assigned `CONTEXT.md`, `DESIGN.md`, `PLAN.md`, and `TASKS.md` to their dedicated workflows.
- Made `DECISION_LOG.md` and `LEARNINGS.md` lazy post-baseline records rather than initial scaffolding.
- Preserved explicit approval gates between design, planning, task generation, and implementation.

**Why:**

- Empty placeholder documents made it look as though downstream stages had occurred and duplicated information already captured during initial planning.
- Decision and learning history should describe changes and discoveries relative to an established baseline, not repeat that baseline.
- One owning workflow per artifact keeps responsibilities and stage transitions clear.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-10 — Game-selection prototype directions created

**What changed:**

- Added an isolated game-selection picker with three deliberately different directions: Catalog, Guided, and Library.
- Made each direction support realistic name or AppID discovery, game identity fields, explicit confirmation, and operation without an official Steam catalog key.
- Gave Catalog a dense search-and-preview workspace, Guided a progressive find-then-confirm flow, and Library an existing-report-first home with focused new-game discovery.
- Captured the user's settled Research report preferences and decision-recording request in `LEARNINGS.md`.

**Why:**

- Game selection must prevent AppID mistakes without assuming that every user has configured a Steam Web API key.
- The three directions test genuinely different answers to first-time discovery, confirmation emphasis, and returning-user report access.
- Keeping this surface separate prevents analysis setup and provider choices from biasing the discovery decision.

**New issues:**

- Connected-browser interaction, console, responsive, and reduced-motion verification remains open for all three game-selection directions.

The new issue above was added to `TASKS.md` under Slice 0.

**Needs human judgment:**

- Select, combine, or request another riff on the game-selection direction.

---

## 2026-08-10 — Theme details made lightweight and inline

**What changed:**

- Replaced the dark Canvas-style Theme drawer with a light neutral detail region that expands directly beneath the selected Research Theme.
- Made the entire Theme row the expansion control and added a down-arrow indicator with synchronized expanded state.
- Limited the overview to one open Theme at a time and allowed the open Theme to collapse when selected again.
- Kept summary, support metrics, category, two representative excerpts, and complete-evidence access inside the expanded region.

**Why:**

- The drawer's dark color, scale, and overlay behavior gave routine Theme inspection too much visual weight.
- Inline disclosure keeps the evidence attached to the Theme that owns it and removes an unnecessary navigation layer.
- A single-open accordion preserves the report's compact research-tool character while keeping detailed evidence available on demand.

**New issues:**

- Inline expansion changes column height and nearby scroll position; responsive and live interaction verification must confirm that this remains comfortable with longer Theme lists.

The new issue above is covered by the existing report-exploration responsive and interaction verification tasks in `TASKS.md`.

**Needs human judgment:**

- None for the inline disclosure behavior. The remaining prototype surfaces and combined workflow retain their existing approval gates.

---

## 2026-08-10 — Research overview combined with Canvas-style Theme details

**What changed:**

- Selected the Research Desk's dense side-by-side positive and negative Theme overview as the report foundation.
- Replaced its compact always-visible Theme inspector with a wide Canvas-style evidence drawer opened by selecting any Theme.
- Made the drawer full-screen on narrow viewports and required it to show polarity, summary, support metrics, category, representative excerpts, and the complete-evidence action.
- Updated all eight prototype Themes so selection changes the drawer's metrics and evidence rather than leaving unrelated placeholder content visible.

**Why:**

- The Research overview supports fast comparison across positive and negative findings.
- Theme evidence needs more space and focus than the original compact inspector provided.
- A drawer preserves the overview as context on wider screens while a full-screen presentation keeps details usable on narrow screens.

**New issues:**

- None beyond the existing connected-browser interaction, console, responsive, and reduced-motion verification tasks.

**Needs human judgment:**

- None for the report-exploration direction. The remaining prototype surfaces and combined workflow still require their existing approval gates.

---

## 2026-08-09 — Slice 0 report-exploration prototypes started

**What changed:**

- Added an isolated standalone report-exploration prototype with three deliberately different directions: Research Desk, Editorial Brief, and Evidence Canvas.
- Included realistic synthetic Themes, Technical Themes, mixed reception, filters, evidence drill-down, report history, responsive layouts, keyboard picker controls, and reduced-motion handling.
- Split the broad Slice 0 prototype checklist into separate single-surface explorations for report reading, game selection, analysis configuration, and durable progress.
- Kept the prototype outside production application code and left every design-selection gate open.

**Why:**

- Report exploration is the highest-leverage surface because it establishes how users compare findings, inspect evidence, understand metrics, filter a report, and revisit history.
- Exploring one high-leverage surface at a time produces more meaningful variation than attempting three complete applications in one comparison.
- Production scaffolding remains blocked until the separate surfaces form one approved workflow.

**New issues:**

- The in-app browser was unavailable, so visual rendering, live interaction, console, laptop-width, and narrow-width verification remain open.
- Game selection, analysis configuration, and durable progress still require their own prototype rounds.

All new issues above were added to `TASKS.md` under Slice 0.

**Needs human judgment:**

- Select, combine, or request another riff on the report-exploration direction after visual review.

---

## 2026-08-09 — Approved plan expanded into executable tasks

**What changed:**

- Expanded every approved implementation slice from Slice 0 through Slice 14 into concrete, dependency-ordered actions in `TASKS.md`.
- Added test-first behavior, contract, integration, accessibility, security, clean-install, and release verification at the slice where each capability enters the product.
- Preserved completed requirements decisions and mapped every existing open task into its owning slice without changing plan order or product scope.
- Added explicit human gates for prototype selection, analysis thresholds, first-provider selection, copyright ownership, source release, uninstall data retention, and packaged release.
- Kept deferred features as blocked one-line tasks that require later design and implementation planning before execution.

**Why:**

- `PLAN.md` defines strategic outcomes and dependencies but was not granular enough to execute one focused, verifiable change at a time.
- Locating tests and verification beside the behavior they introduce supports green atomic changes and makes blockers visible before implementation starts.
- A single ordered task tracker prevents quality, privacy, security, packaging, and human approval work from becoming detached from feature delivery.

**New issues:**

- The expected retention or removal of application data during Windows uninstall needs human judgment before packaged-release validation.

The new issue above was added to `TASKS.md` under Slice 14.

**Needs human judgment:**

- Select the prototype direction at Slice 0.
- Approve the labeled evaluation baseline and provisional thresholds at Slice 4.
- Approve the first automated cloud provider at Slice 8.
- Confirm the MIT copyright holder and approve the source release at Slice 13.
- Confirm uninstall data retention and approve the packaged release at Slice 14.

---

## 2026-08-09 — Historical evidence, filtering, export, and trust contracts clarified

**What changed:**

- Made Steam review history append-only through immutable Review Revisions and bound every Report Version to exact revisions.
- Defined Theme polarity, support denominators, exact source excerpts, and Technical Themes outside the design taxonomy and headline rankings.
- Defined Evidence Filter reranking, threshold markers, zero-support hiding, and filtered evidence behavior without new discovery.
- Classified manual Codex as external/manual cloud processing with an explicit disclosure.
- Limited default JSON re-import to installations containing the matching Game Dataset and Review Revisions; deferred a self-contained Portable Report Archive.
- Corrected the credential boundary to acknowledge the dedicated local submission request while prohibiting persistence, logging, and backend disclosure.
- Added untrusted-content, prompt-injection, sanitization, safe-link, and pipeline-wide cost-estimation requirements.
- Defined eligible Quick/Full reviews as English reviews matching the configured review scope without recommendation balancing.

**Why:**

- A report cannot be immutable if a refresh can overwrite the source review text it cites.
- Deterministic metrics and exact excerpts require explicit denominators, polarity, and evidence references.
- Privacy and credential claims must describe the actual local-browser data path rather than promise an impossible absence from all frontend requests.
- A default privacy-minimized JSON export cannot also be a self-contained backup without carrying the omitted source evidence.
- User-controlled filtering should remain predictable and visibly distinct from new theme discovery.

**New issues:**

- Review Revision persistence and exact report membership require implementation and fixture coverage.
- Portable cross-installation restore requires a separate privacy-warned archive format.
- Untrusted content and embedded prompt instructions require explicit security tests.
- Pipeline-wide cost estimates require provider-specific validation.

All new issues above were added to `TASKS.md`.

**Needs human judgment:**

- None. The user approved the recommended behavior.

---

## 2026-08-09 — Implementation plan reorganized into vertical slices

**What changed:**

- Replaced layer-oriented phases with 15 dependency-ordered vertical slices.
- Set prototype approval as the current execution frontier.
- Kept strategic outcomes, blockers, stable subsystem scope, acceptance evidence, tradeoffs, and status in `PLAN.md`.
- Deferred concrete test-first action expansion to `create-implementation-tasks` and `TASKS.md`.

**Why:**

- Vertical slices deliver independently observable behavior and carry verification with the behavior they introduce.
- Separating strategic planning from operational tasks keeps `PLAN.md` durable while allowing `TASKS.md` to evolve during implementation.
- The prototype gate prevents production UI contracts from being built around an unvalidated visual direction.

**New issues:**

- None beyond the existing quality, Steam-policy, prototype, and copyright blockers already tracked in `TASKS.md`.

**Needs human judgment:**

- Approve the prototype direction before production scaffolding.
- Approve the eventual concrete task expansion before implementation.

---

## 2026-08-09 — Requirements interview consolidated into the authoritative design

**What changed:**

- Replaced the earlier provisional design with the resolved single-game, local-web MVP.
- Made AI analysis provider-neutral across Ollama, OpenAI API, Anthropic Claude API, Google Gemini API, and manual Codex packages.
- Removed mandatory embeddings, automatic model downloads, manual Theme editing, and MVP comparison work.
- Added secure credential boundaries, explicit local/cloud disclosure, approximate paid-provider cost estimates, durable jobs, immutable Report Versions, incremental refresh, and privacy-safe exports.
- Defined comprehensive best-effort Steam metadata snapshots, grouped feature states, regional pricing, and opt-in Steam-hosted media behavior.
- Confirmed MIT licensing and Windows as the first packaged-release target.
- Deferred detailed interface choices to a visual prototype guided by the approved product hierarchy.

**Why:**

- The earlier documents were written incrementally and retained assumptions that the completed interview later rejected.
- A single coherent specification keeps evidence rules, provider behavior, security, lifecycle, and Steam limitations consistent before prototyping or implementation.
- Keeping embeddings optional and models user-managed supports local distribution without imposing downloads or a central AI budget.

**New issues:**

- No-embedding paraphrase grouping must be evaluated across the initial providers.
- The Steam storefront adapters need explicit reliability and retention validation.
- The copyright holder must be confirmed before adding the MIT license text.

All new issues above were added to `TASKS.md`.

**Needs human judgment:**

- Review and approve a visual prototype direction.
- Confirm the copyright holder for the MIT license file.

---

Newest entries at the top. Record meaningful decisions—not every small change, only choices with non-obvious reasoning.

---

## 2026-08-09 — Temporary evidence filters and saved cohort analyses

**What changed:**

- Kept evidence-filter changes as resettable, temporary view state.
- Required intentionally run cohort analyses to be saved as separate results with visible scope.
- Sharpened the `Cohort Analysis` glossary definition accordingly.

**Why:**

- Automatically saving every filter adjustment would clutter analysis history.
- Saving cohort analyses preserves deliberately generated discoveries for later inspection and comparison.

**New issues:**

- None.

**Needs human judgment:**

- None.

## 2026-08-09 — Steam recommendation filter separated from opinion sentiment

**What changed:**

- Added a filter for all, `Recommended`, or `Not Recommended` Steam reviews.
- Defined `Steam Recommendation` and `Opinion Sentiment` as separate canonical terms in the domain glossary.

**Why:**

- Steam's recommendation is a whole-review verdict, while one review may express several positive and negative opinions.
- Explicit labels prevent users from interpreting the filter as an AI sentiment classification.

**New issues:**

- None.

**Needs human judgment:**

- None.

## 2026-08-09 — Review-date filters confirmed

**What changed:**

- Added review-date presets for the last 30 days, 90 days, and one year.
- Added a custom review-date range.

**Why:**

- Date cohorts make changes in player feedback easier to inspect, including periods around known updates.

**New issues:**

- Steam review dates do not reliably identify the exact game version a reviewer played.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None.

## 2026-08-09 — Acquisition and Early Access filters confirmed

**What changed:**

- Added evidence filters for Steam purchase, received-for-free status, and reviews written during Early Access.
- Kept all reviews selected by default.

**Why:**

- These cohorts may reveal different feedback patterns.
- Default inclusion keeps the primary report comprehensive and avoids implying that one acquisition path is inherently more credible.

**New issues:**

- None beyond the existing minimum cohort-size calibration task.

**Needs human judgment:**

- None.

## 2026-08-09 — Evidence filters separated from cohort analysis

**What changed:**

- Defined evidence filters as instant recalculation of metrics for already discovered themes.
- Added optional cohort analysis to discover themes within a selected review subset.
- Added the resolved terminology to `Docs/DOMAIN_GLOSSARY.md`.

**Why:**

- Recalculating known themes supports fast exploration.
- Cohort-specific discovery can expose themes that are uncommon in the overall dataset but important within a playtime group.
- Separate terms prevent users and contributors from mistaking a filtered view for a new analysis.

**New issues:**

- Cohort analyses need clear scope labels and minimum sample requirements.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None until minimum cohort-size evidence is available.

## 2026-08-09 — Playtime filter fields confirmed

**What changed:**

- Selected playtime at review as the default playtime-filter field.
- Kept current total playtime available as an alternative.

**Why:**

- Playtime at review reflects the experience accumulated when the opinion was written.
- Current total playtime adds context about subsequent engagement.

**New issues:**

- None beyond the unresolved playtime-filter analysis behavior.

**Needs human judgment:**

- Decide whether filters recalculate known themes or trigger cohort-specific discovery.

## 2026-08-09 — All reviews included with playtime filtering

**What changed:**

- Included reviews from all Steam purchase sources by default.
- Required playtime filtering to inspect differences between lower- and higher-playtime feedback.

**Why:**

- Default inclusion avoids silently excluding part of the available player evidence.
- Playtime cohorts may discuss different design strengths and weaknesses even though every review retains equal weight within its selected scope.

**New issues:**

- It remains undecided whether playtime filtering recalculates known themes or performs cohort-specific theme discovery.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Choose the playtime field and filtering-analysis behavior.

## 2026-08-09 — Reviews receive equal weight

**What changed:**

- Gave every distinct review equal weight in theme-support calculations.
- Required playtime and helpfulness to remain visible as evidence context.
- Prohibited both fields from acting as hidden ranking or frequency multipliers.

**Why:**

- Frequency should represent how many players expressed an opinion, not how many helpful votes or hours a subset accumulated.
- The metadata can still help users interpret individual excerpts and reviews.

**New issues:**

- None.

**Needs human judgment:**

- None.

## 2026-08-09 — Neutral mentions excluded from opinion metrics

**What changed:**

- Excluded neutral and purely factual mentions from theme support, sentiment splits, and prevalence.

**Why:**

- Naming a mechanic does not demonstrate approval, criticism, or mixed reception.
- Counting neutral mentions would overstate the amount of actionable player opinion.

**New issues:**

- Neutral-versus-opinion classification must be included in the labeled analysis evaluation.

The existing human-labeled evaluation task in `TASKS.md` covers this issue.

**Needs human judgment:**

- None.

## 2026-08-09 — Mixed reception shown with sentiment and prevalence

**What changed:**

- Linked opposing positive and negative themes about the same mechanic.
- Added positive, negative, and mixed percentages among distinct reviews mentioning the mechanic.
- Added the mechanic's percentage and count among all analyzed distinct reviews.
- Kept the counts visible inline using the agreed compact presentation.

**Why:**

- Sentiment split shows whether players who discuss a mechanic tend to like it.
- Overall prevalence prevents a strong split from appearing broadly important when few reviews mention it.

**New issues:**

- Opposing-theme linkage and review-level mixed classification need evaluation.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None.

## 2026-08-09 — Theme caps apply across the report

**What changed:**

- Confirmed up to 10 positive and 10 negative themes across all categories in a report.
- Rejected separate top-10 quotas for every category.

**Why:**

- Per-category quotas would produce long reports and encourage unreliable filler themes.
- Categories are intended for organization, filtering, and comparison rather than guaranteeing equal representation.

**New issues:**

- None.

**Needs human judgment:**

- None.

## 2026-08-09 — Theme category overlap defined

**What changed:**

- Required exactly one primary category per theme.
- Allowed optional related-category labels for genuine overlap.
- Prohibited category overlap from duplicating the theme or its support count.

**Why:**

- A single primary category keeps report organization and comparisons unambiguous.
- Related labels preserve nuances such as onboarding feedback that also affects perceived difficulty.

**New issues:**

- None.

**Needs human judgment:**

- None.

## 2026-08-09 — Initial shared theme taxonomy confirmed

**What changed:**

- Confirmed the initial shared categories: gameplay and mechanics; progression and rewards; difficulty and balance; content, variety, and replayability; controls, interface, and onboarding; narrative, characters, and world; multiplayer and social experience; visuals and audio; accessibility; and monetization and value.
- Retained `Game-specific` for unmatched design themes and the separate secondary technical category.

**Why:**

- The categories cover common areas of player experience while remaining broad enough for cross-game comparison.

**New issues:**

- How later taxonomy changes affect historical reports and comparisons remains undecided.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None.

## 2026-08-09 — Hybrid category taxonomy confirmed

**What changed:**

- Required a shared set of game-design categories for consistent report organization and cross-game comparison.
- Added a `Game-specific` category for recurring themes that do not accurately fit the shared taxonomy.
- Kept theme discovery evidence-driven before category assignment.

**Why:**

- A shared taxonomy makes differences between game reports easier to understand.
- Game-specific mechanics and experiences should not be distorted merely to fit generic categories.

**New issues:**

- Category-assignment quality and overuse of the `Game-specific` fallback need evaluation.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Select the initial shared category set.

## 2026-08-09 — Frequent technical feedback retained as secondary evidence

**What changed:**

- Reserved the headline positive and negative rankings for game-design themes.
- Kept genuinely frequent technical themes visible in a secondary report category.

**Why:**

- Technical feedback should not displace the transferable design evidence the user primarily wants.
- Completely suppressing a dominant technical complaint would make the report an incomplete account of player feedback.

**New issues:**

- The display threshold for the secondary technical category needs calibration.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None until threshold evidence is available.

## 2026-08-09 — Reports focused on transferable game-design evidence

**What changed:**

- Prioritized recurring themes that can inform game-design understanding.
- Rejected a separate low-frequency technical-risk section for crashes, save corruption, performance problems, and similar defects.

**Why:**

- The report's purpose is to expose evidence the user can learn from when making game-design decisions.
- Basic stability expectations are already understood, and rare technical reports would distract from that purpose.

**New issues:**

- Theme classification needs a transparent, evaluated taxonomy so useful design evidence is not silently discarded.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None until taxonomy options are proposed and evaluated.

## 2026-08-09 — Standard theme count confirmed

**What changed:**

- Set the standard report to show up to 10 positive and 10 negative themes.
- Ranked themes by distinct-review support and allowed fewer than 10 when reliability thresholds are not met.

**Why:**

- Ten themes provide useful breadth while remaining scannable.
- Padding the report with weak clusters would make the output look more certain than the evidence supports.

**New issues:**

- The minimum support and cluster-coherence thresholds must be calibrated during the analysis spike.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- None until evaluation results are available.

---

## 2026-08-09 — Point-level sentiment confirmed

**What changed:**

- Required praise and criticism to be classified from individual opinion points rather than the review's overall Steam recommendation.
- Required separate positive and negative evidence when the same aspect receives both.

**Why:**

- Recommended reviews often contain criticism, and not-recommended reviews can still contain praise.
- Collapsing mixed reception into one verdict would discard useful disagreement in the source reviews.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-09 — Theme evidence requirements confirmed

**What changed:**

- Required every theme to include a specific title, short descriptive summary, distinct-review count and percentage, three to five representative excerpts, and analysis scope.
- Required drill-down to every matched opinion point and its complete original review.
- Limited each source review to one count per theme regardless of repeated wording.

**Why:**

- Users need both a fast overview and enough provenance to verify a generated theme.
- Distinct-review counting prevents repetitive writing from inflating apparent frequency.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-09 — Evidence-only reports confirmed

**What changed:**

- Limited reports to descriptive findings and supporting evidence.
- Excluded design recommendations, opportunity scores, and prescriptive advice from report output.

**Why:**

- The tool should faithfully organize what players said while leaving game-design judgment to the user.
- Separating evidence from advice reduces unsupported inference and keeps reports auditable.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-09 — English-only MVP confirmed

**What changed:**

- Confirmed that the first usable version analyzes English reviews only.
- Tracked automated translation and multilingual analysis as later-phase work.
- Required future translations to preserve original text, source language, and translation provenance.

**Why:**

- English-only scope lets the first version validate point extraction, clustering, and summary quality without mixing translation errors into the results.
- Preserving originals and provenance will keep later translated analysis auditable.

**New issues:**

- None.

**Needs human judgment:**

- None.

---

## 2026-08-09 — Unapproved interface draft removed

**What changed:**

- Removed `UI_DESIGN.md` and every reference, task, and plan item derived from it.
- Returned the interface to an undefined state so requirements can be established collaboratively.

**Why:**

- The draft contained workflow and presentation assumptions that had not been agreed with the user.
- No interface design should be treated as a project decision until its requirements are discussed and approved.

**New issues:**

- None.

**Needs human judgment:**

- Define the interface requirements collaboratively.

---

## 2026-08-09 — Repository, name, and stack confirmed

**What changed:**

- Selected **Game Review Analyzer** as the project name.
- Connected the local project to `https://github.com/pozbliz/game_review_analyzer.git`.
- Confirmed React/TypeScript/Vite for the frontend and FastAPI/Python for the backend and analysis pipeline.
- Deferred additional statistical dashboards and application-usage telemetry from the MVP.
- Kept Steam as the only confirmed MVP review source despite the broader project name.

**Why:**

- The selected name makes the tool's purpose immediately understandable and leaves room for future review sources.
- The hybrid stack balances a rich interactive interface with mature Python analysis tooling.
- The core risk is trustworthy theme extraction and summarization, so unrelated analytics would dilute the MVP.

**New issues:**

- The broader name may imply support for review platforms that are currently out of scope.

The new issue above was added to `TASKS.md`.

**Needs human judgment:**

- Decide later whether the product should actually expand beyond Steam.

---

## 2026-08-09 — Self-hosted public distribution confirmed

**What changed:**

- Confirmed that the project will be published in a public GitHub repository for users to run on their own machines.
- Revised the recommended interface from Jinja/HTMX to React/TypeScript while retaining FastAPI/Python for ingestion and analysis.
- Added a staged distribution plan: source installation, optional Docker Compose, then prebuilt releases.

**Why:**

- Local execution lets each user supply their own compute and avoids a central inference bill.
- React is well suited to progress views, filtering, cluster exploration, evidence drill-down, and future comparison screens.
- Python preserves access to mature NLP, clustering, evaluation, and data-processing tooling.
- Building React in CI lets release users run static assets through FastAPI without installing Node.js.

**New issues:**

- The initial supported operating systems and open-source license need human decisions.
- Docker GPU integration must be tested per operating system.
- Prebuilt releases need a packaging design that hides the Python and Node.js development toolchains.

All new issues above were added to `TASKS.md`.

**Needs human judgment:**

- Approve the recommended hybrid stack or choose a single-language alternative.
- Choose initial operating systems and an open-source license.

---

## 2026-08-09 — Initial analysis architecture proposed

**What changed:**

- Proposed a Python/FastAPI local web application with server-rendered Jinja/HTMX views and SQLite.
- Separated embeddings and summary generation behind provider interfaces.
- Defined opinion points, rather than whole reviews, as the unit of sentiment and semantic clustering.
- Proposed quick, full, and refresh import modes with explicit coverage labels.
- Made distinct-review support the primary theme-frequency metric.

**Why:**

- Python matches the user's existing experience and has strong local NLP tooling.
- A provider boundary supports local Ollama now, manual Codex analysis when useful, and hosted inference later.
- Whole-review embeddings mix multiple topics and recommendation-level sentiment misses praise/criticism inside mixed reviews.
- Always downloading and analyzing every review is unnecessarily slow for exploration and can be infeasible for very popular games.
- Counting source reviews once per theme prevents repetitive reviews from inflating frequency.

**New issues:**

- Exact laptop hardware is unknown because the automated Windows hardware query was denied access.
- The proposed 5,000-review quick cap needs a topic-stability experiment.
- Steam retention, attribution, and request-rate expectations need review before public deployment.
- The project needs a human-labeled evaluation set before model quality can be claimed.
- Codex exports need an explicit redaction and retention design.

All new issues above were added to `TASKS.md`.

**Needs human judgment:**

- Approve or revise the proposed application stack.
- Confirm the target hardware and MVP language.
- Define whether eventual hosting is a private demo or public multi-user service.

---

## 2026-08-09 — Project initialized

**What changed:**

- Created `README.md`, `DESIGN.md`, `PLAN.md`, `TASKS.md`, `DECISION_LOG.md`, and `LEARNINGS.md`.

**Why:**

- Establish the required documentation and decision workflow before implementation.

**New issues:**

- None beyond those recorded in the newer entry above.

**Needs human judgment:**

- None beyond those recorded in the newer entry above.
