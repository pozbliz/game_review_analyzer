# Agent Instructions

## Behavior

- Ask, don't assume. If something is unclear, ask before writing. When running unattended, choose the most reasonable interpretation, proceed, and record the assumption rather than blocking.
- Be direct and push back when a request conflicts with established practice; recommend a better alternative.
- State the intended approach and what it makes harder downstream before changing code.
- End every task by stating what was not done.
- Keep diffs scoped. Do not reformat or refactor unrelated work.
- When unrelated design or code issues are discovered after the project baseline exists, record them under **New issues** in `DECISION_LOG.md` and add them to `TASKS.md` when that file exists.
- Keep output concise unless the user asks for more detail.
- Investigate root causes before retrying failures.

## Project workflow

Project documents are created only when their owning workflow has substantive content. File existence should indicate that the corresponding stage has occurred.

### Ordered stages

1. `$init-project` conducts a short interview and creates the initial `README.md` project brief.
2. The user develops the requirements through conversation and, when useful, `$grill-with-docs`.
3. After the discussion is complete, the user explicitly invokes `$create-system-design` to create or revise `DESIGN.md`.
4. The user reviews and explicitly approves `DESIGN.md`.
5. The user explicitly invokes `$create-implementation-plan` to create `PLAN.md`.
6. The user reviews and explicitly approves `PLAN.md`.
7. The user explicitly invokes `$create-implementation-tasks` to create `TASKS.md`.
8. Implementation begins only through a separate explicit request and follows the repository's test-driven workflow.

Do not invoke the three creation skills automatically or skip their approval gates.

### File ownership and lifecycle

- **README.md** — Created by `$init-project`. Describes the current purpose, users, scope, status, and factual usage information. Update it whenever project purpose, scope, status, or operation changes.
- **CONTEXT.md** — Created lazily by `$domain-modeling` when the first project-specific canonical term is resolved. Contains only implementation-free domain language.
- **DESIGN.md** — Created or revised only by an explicit `$create-system-design` invocation after the relevant discussion is complete. Captures approved behavior, domain rules, architecture, interfaces, failure behavior, and testing boundaries.
- **PLAN.md** — Created or revised only by an explicit `$create-implementation-plan` invocation after `DESIGN.md` approval. Contains strategic vertical slices, ordering, dependencies, and verification gates—not concrete task checklists.
- **TASKS.md** — Created or revised only by an explicit `$create-implementation-tasks` invocation after `PLAN.md` approval. Contains the concrete ordered implementation checklist and becomes the source of truth for open implementation work once it exists.
- **DECISION_LOG.md** — Created lazily after the initial project baseline exists, when an approved design, plan, or implementation direction changes or an unplanned non-trivial decision is made. Do not repeat decisions already captured as part of the initial `README.md`, `DESIGN.md`, or `PLAN.md`.
- **LEARNINGS.md** — Created lazily when a confirmed constraint, system gotcha, user preference, or non-obvious behavior is discovered after work begins. Confirm with the user before recording a new learning.

The initial project baseline consists of the approved project brief, design, and implementation plan. Baseline creation is not itself decision-log history.

### Prototype surfaces

Retain visual exploration files after a direction is selected until that direction has been integrated into production and the user explicitly approves cleanup. In prototype-only stages, promotion means recording the selected direction in the authoritative design and decision log; it does not mean deleting the exploration file.

### Repository structure

- Keep the Python and TypeScript toolchains in separate top-level `backend/` and `frontend/` directories.
- Organize backend production code under `backend/src/game_review_analyzer/` by ownership: `domain/`, `application/`, `interfaces/`, `infrastructure/`, and `shared/`.
- Keep backend tests under `backend/tests/`, separating unit and integration coverage as those suites grow.
- Organize frontend production code under `frontend/src/` into `app/`, `features/`, `components/`, `api/`, and `styles/` as each area gains real content.
- Keep frontend cross-feature integration tests under `frontend/tests/`; colocated focused component tests remain acceptable when ownership is clearer there.
- Store maintained specifications under lowercase `docs/`, operational tooling under `scripts/`, and visual explorations under `prototypes/`.
- Do not create empty placeholder directories; add each approved directory when it gains owned content.

## Starting a new project

When the user says “new project,” “init project,” “set up project docs,” “create a project README,” or invokes `/init-project`, use `$init-project` before other project workflows.

`$init-project` creates only `README.md`. It must not initialize Git, scaffold code, install dependencies, classify the project, or create downstream workflow documents.

## Ongoing rules

- Read `README.md` and every existing artifact relevant to the current stage before working.
- Before implementation, read `TASKS.md` when it exists; it is the source of truth for open implementation work.
- Read `LEARNINGS.md` before working in an area with prior recorded constraints or gotchas.
- Do not create `TASKS.md` merely to track work discovered during design or planning. Keep unresolved design questions in `DESIGN.md` and planning blockers in `PLAN.md`.
- After the baseline exists, record every non-trivial behavioral change, routing or flow change, design revision, non-obvious implementation choice, multi-file refactor, or root-cause bug fix in `DECISION_LOG.md`.
- Create `DECISION_LOG.md` on the first qualifying post-baseline change. Keep entries newest-first and record **What changed**, **Why**, **New issues**, and **Needs human judgment**.
- Skip decision-log entries for trivial typo, comment, behavior-neutral variable rename, or version-string changes.
- Add every new implementation issue recorded in `DECISION_LOG.md` to `TASKS.md` when `TASKS.md` exists.
- Group tasks under the current date in `YYYY-MM-DD` format. Preserve completed tasks in place and do not move them into a separate “Done” section.
- Mark decisions or work requiring human input with `[HUMAN]`.
- Create `LEARNINGS.md` only after the user confirms the first learning. Record each learning with its capture date, keep the file append-only, and never delete entries.
- Keep `README.md` aligned with the current project rather than the original proposal.

## General

- More specific local instructions override broader instructions.
- Load specialized files from `./custom_rules/` only when relevant.
- For coding tasks, follow `C:\Users\Dante\.codex\custom_rules\coding_style.md`.
- Every rules file must end with a `## Changelog` section.
- Every changelog entry must include a date in `YYYY-MM-DD` format and a clear summary.

## Changelog

- 2026-08-11: Added the approved two-root Python/TypeScript repository structure with ownership-based internal boundaries.
- 2026-08-10: Replaced eager seven-file scaffolding with staged document ownership, lazy history files, and explicit design, plan, and task approval gates.
- 2026-08-10: Retain prototype explorations until production integration and explicit cleanup approval; do not delete selected prototypes during prototype-only stages.
