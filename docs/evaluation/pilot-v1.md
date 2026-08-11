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
| Reviews with complete Opinion Point coverage | 17/18 (94.4%) |
| Theme-grouping judgments confirmed | 8/8 (100%) |
| Proposed Theme summaries judged faithful | 5/5 (100%) |
| Opposing/unrelated Theme links confirmed | 2/2 (100%) |
| Review-level classifications confirmed | 2/2 (100%) |

The sole correction changed a difficulty description from negative to neutral. The positive statement about the same difficulty remained positive. This confirms that difficulty intensity alone must not be treated as criticism.

## Honest limits

- Candidate acceptance measures precision only. The completeness round found one review with missing Opinion Points; exact missing spans still need adjudication before extraction recall can be calculated.
- Category, subject, and Theme-title confirmation was anchored by visible candidate values rather than collected blind.
- Eight selected Theme pairs were reviewed, but this small anchored sample does not establish general paraphrase-grouping quality.
- Five summaries and two opposing-link cases passed human review, but the small selected sample does not establish general accuracy.
- Eighteen deliberately short, recommendation-balanced reviews do not represent natural prevalence or a 5,000-review run.
- Exact-excerpt and prompt-injection validation require pipeline tests, not reviewer agreement alone.

## Quality follow-up

The reviewer completed all 35 button-only judgments. Seventeen of 18 reviews were complete; the missing case was review `232551790` from Hades II. All eight grouping judgments, five summary-faithfulness judgments, two opposing-link judgments, and two review-level classifications passed.

The prepared `missing_opinion_followup_pilot_v1.json` asks the reviewer to accept or reject four exact candidate spans from the incomplete review. Extraction recall remains unreported until that correction round is complete.
