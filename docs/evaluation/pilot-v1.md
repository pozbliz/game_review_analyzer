# Analysis Evaluation Pilot V1

## Scope

The first human round covered 18 recent reviews from Hades II, Stardew Valley, and Cyberpunk 2077: three Recommended and three Not Recommended reviews per game. Codex proposed 38 clause-level Opinion Points, and the user adjudicated every proposal in the local browser labeler.

This is a workflow and candidate-quality pilot. It is not a production accuracy baseline and provides no evidence for headline or Technical Theme thresholds.

## Results

| Check | Result |
| --- | ---: |
| Candidate Opinion Points accepted | 38/38 (100%) |
| Exact excerpts resolving to their source review | 38/38 (100%) |
| Sentiment unchanged after human review | 37/38 (97.4%) |
| Proposed positive labels confirmed | 12/12 (100%) |
| Proposed negative labels confirmed | 23/24 (95.8%) |
| Proposed neutral labels confirmed | 2/2 (100%) |
| Human-neutral points found by the proposal | 2/3 (66.7%) |
| Category unchanged | 38/38 (100%) |
| Technical Theme flag unchanged | 38/38 (100%) |
| Subject unchanged | 38/38 (100%) |
| Candidate Theme title unchanged | 38/38 (100%) |

The sole correction changed a difficulty description from negative to neutral. The positive statement about the same difficulty remained positive. This confirms that difficulty intensity alone must not be treated as criticism.

## Honest limits

- Candidate acceptance measures precision only. The interface did not ask the reviewer to add missing Opinion Points, so extraction recall is unknown.
- Category, subject, and Theme-title confirmation was anchored by visible candidate values rather than collected blind.
- Matching Theme titles do not prove pairwise paraphrase grouping.
- No Theme summaries or opposing-Theme links were reviewed.
- Eighteen deliberately short, recommendation-balanced reviews do not represent natural prevalence or a 5,000-review run.
- Exact-excerpt and prompt-injection validation require pipeline tests, not reviewer agreement alone.

## Next evaluation round

The prepared `quality_round_pilot_v1.json` contains 35 button-only judgments: 18 completeness checks, 8 Theme-grouping comparisons, 5 summary-faithfulness checks, 2 opposing-link checks, and 2 review-level classifications. Complete and export that round before calculating the remaining pilot metrics. Expand only after the reviewer confirms that workflow.
