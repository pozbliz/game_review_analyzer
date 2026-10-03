# Progressive workflow verification

## Scope and environment

Verification started on 2026-10-03 against commit `d0b1d9376822fa2b6a3e90d6c2451a4ef0f87e90` plus the existing working-tree changes.

Those earlier changes were committed and pushed as `4d4ffe5` during verification. Final frontend checks include the scoped UI corrections described below.

The game is Gothic 1 Classic (AppID `65540`). SQLite's backup API copied the current local database into `backend/data/workflow-verification-2026-10-03/verification.sqlite3`.

The verification backend uses `http://127.0.0.1:8001`. The original database is not the verification target.

The provider is authenticated Codex CLI `0.160.0`, using `gpt-5.6-luna` with low reasoning.

## Automated checks

- Backend: 114 tests passed.
- Frontend: 24 tests passed across four files after the UI corrections below.
- TypeScript checks and production build passed.
- PowerShell blocks `npm.ps1`; `npm.cmd` runs the existing npm commands without changing system policy.

## Live runs

| Operation | Run ID | Scope | Result | Measured time | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| Test | `9f7d0fe5-4530-47dd-8148-be2d7bf54666` | 50 | Completed | 21.000 seconds | 21,680 | 895 |
| Main replacement | `4a3b0b95-f257-4e7c-92a9-48688f33644e` | 1,000 | Completed after restart | About 7 minutes 6 seconds | 462,389 | 13,778 |
| Main extension | `962c499c-d016-4aaa-869b-af23c723bb28` | 1,000 additional reviews, 2,000 cumulative | Completed | About 7 minutes 27 seconds | 467,705 | 15,605 |

The Test Report contains 25 oldest and 25 newest reviews without overlap. Its creation leaves the original Main Report snapshot hash unchanged.

Test timing comes from the `analysis.completed` event. Main replacement wall time comes from database creation and completion timestamps, which have one-second precision.

Main replacement includes Steam refresh and forced interruption. Its completion event measures only the 276.453-second execution after restart.

The replacement recorded 101,376 cached input tokens, included in its input total. The extension recorded 189,696 cached input tokens, also included in its input total.

Token totals cover saved successful results, including reused checkpoints. Usage from the interrupted map call and rejected merge attempt is unavailable. Recorded totals are not complete subscription-quota measurements.

Extension execution took 447.187 seconds, including Steam refresh. Database timestamps give approximately 447 seconds from creation to completion; refresh took approximately 87 seconds.

The extension's second negative merge returned a new Theme without an assignment. Validation rejected it with `theme_merge_theme_unassigned`. The existing correction retry succeeded.

The completed replacement report has disjoint 500-review cohorts. All replacement metrics independently reproduce from stored memberships. Its API exposes four positive and six negative Themes.

Every visible replacement Theme's evidence count, revision IDs, text, recommendation, helpful votes, and helpful-first ordering match local storage.

## Restart and report isolation

The verification backend was terminated during Main replacement after map batches 1 and 2 were saved. Its owned provider subprocesses were also terminated.

Restart resumed the same run with identical ordered scope, cohorts, base report, refresh job, and metric policy. Both saved checkpoint hashes and timestamps remained unchanged.

Logs show maps 1 and 2 ran once. The interrupted map 3 ran again. The recovered run completed with 14 map checkpoints and six merge checkpoints.

The stop-to-relaunch interval was approximately 0.913 seconds. This interval excludes backend startup and the interrupted provider call.

The old Main Report remained readable during replacement. Successful replacement removed it and published a fresh 1,000-review report. The Test Report snapshot remained unchanged.

During extension, the prior Main and Test Report snapshots remained unchanged. The reserved extension contained exactly 1,000 reviews outside the Main Report's scope.

Successful extension published 2,000 distinct review identities with disjoint 1,000-review oldest and newest cohorts. Its scope is exactly the union of the base scope and reserved unseen scope.

All cumulative metrics and visible rankings independently reproduce from 3,241 unique Theme memberships. The API still exposes four positive and six negative Themes.

Every visible Theme's evidence matches local storage and helpful-first ordering. All ten previously visible Theme definitions remain unchanged.

The extension retained 15 map checkpoints and five merge checkpoints. The Test Report snapshot remained unchanged.

SQLite integrity and foreign-key checks passed. Original reports, runs, and checkpoints match the pre-verification baseline.

A concurrent Main update was rejected with `409 main_report_analysis_active`.

## Browser and human gates

The browser tool reports no connected browsers. Browser isolation, keyboard, narrow-screen, reduced-motion, and non-color acceptance remain open.

Source inspection found native disclosure controls, named Theme buttons, responsive breakpoints, reduced-motion rules, and text labels for polarity and failures. Source inspection does not replace browser acceptance.

The user must review live Theme usefulness before release work resumes. Human assistive-technology acceptance and release approval remain separate gates.

While the verification backend runs, the isolated [Test Report](http://127.0.0.1:8001/test-reports/65540) and [Main Report](http://127.0.0.1:8001/main-reports/65540) are available for review.

To reopen them later, set `GAME_REVIEW_ANALYZER_DATABASE` to the absolute verification database path and start the documented backend command with `--port 8001`.

## Corrected findings

- Import and Steam refresh progress bars now have accessible names.
- The completed-import screen displays the selected cohort support threshold and Theme cap.
- Empty Main and Test Reports refer to their report's support threshold without assuming 5%.

Focused component assertions failed before each correction and passed afterward. These findings are closed under Workflow verification follow-ups in `TASKS.md`.

Empty-report wording is generic because the public report response does not contain the stored threshold. The correction adds no API fields.
