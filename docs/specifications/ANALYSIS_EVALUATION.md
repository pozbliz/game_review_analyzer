# Analysis Quality Evaluation

## Purpose

This specification defines the provider-independent gold-label format and scoring rules used before analysis behavior or reliability thresholds are approved. Synthetic cases verify conformance and safety only. Threshold calibration and headline-stability claims require a separately approved real-game corpus.

## Corpus record

The versioned JSON document contains:

- `schema_version`: evaluation-format version.
- `corpus_kind`: `synthetic_conformance` or `real_calibration`.
- `games`: independently scored game cases.

Each game case contains:

- `case_id`, `app_id`, `title`, and `style`: stable identity and the review style being exercised.
- `reviews`: exact source inputs with stable `review_revision_id`, Steam recommendation, and text.
- `opinion_points`: gold sentence- or clause-level opinions. Each has a stable identifier, source review identifier, exact excerpt, sentiment, subject, and `supports_theme_id`. Neutral points use `null` for theme support.
- `themes`: gold recurring opinions. Each records polarity, primary and related categories, supporting Opinion Point identifiers, a faithful summary, whether it is technical, and an optional opposing Theme identifier.
- `mechanic_classifications`: per-review `liked`, `disliked`, or `mixed` labels for mechanics with opposing Themes. Neutral-only mentions are omitted.

All excerpts must be exact substrings of the referenced review. A Theme must have support from at least two distinct reviews in a conformance case. Real calibration cases may retain lower-frequency candidate clusters so threshold behavior can be measured.

Raw real-review text, reviewer identifiers, and annotations must follow the separately approved corpus storage policy. Provider outputs are never gold labels.

## Human review workflow

Raw corpus and reviewed files remain under the local, gitignored `evaluation-data/` directory. Candidate labels contain the source review, exact candidate excerpt, sentiment, subject, category, and Theme title.

Open [`review-labeler.html`](../../frontend/public/review-labeler.html) directly or at `/review-labeler.html` when the application is running. Load the candidate JSON, then use the buttons or keyboard shortcuts to approve, correct, or reject each Opinion Point. The browser autosaves the current round by source filename. When every candidate has a decision, export the reviewed JSON and either attach it in conversation or place it under `evaluation-data/` and provide its path.

The exported file is the handoff back to Codex. It preserves each source candidate and adds a `humanReview` object containing the decision, corrected sentiment, category, Technical Theme flag, subject, and Theme title. No data is transmitted by the page.

## Automated scoring

Score each provider run without rounding intermediate values:

| Behavior | Measure |
| --- | --- |
| Opinion Point extraction | Precision, recall, and F1 over gold source spans |
| Opinion Sentiment | Accuracy over correctly matched Opinion Points |
| Neutral exclusion | Precision and recall for neutral points excluded from Theme support |
| Paraphrase grouping | Pairwise precision, recall, and F1 over non-neutral point pairs |
| Primary category | Exact-match accuracy over matched Themes |
| Related categories | Set precision, recall, and F1 over matched Themes |
| Exact evidence | Fraction of excerpts that are exact source substrings with matching review identifiers |
| Opposing linkage | Precision, recall, and F1 over unordered Theme pairs |
| Review classification | Accuracy for liked, disliked, and mixed mechanic labels |

Theme matching for scoring uses the overlap of gold supporting Opinion Point identifiers. Match each predicted Theme to at most one gold Theme, choosing the unmatched gold Theme with the largest overlap; ties use the lexical gold Theme identifier. This deterministic rule avoids using titles as evidence.

Summary faithfulness remains a blinded human pass/fail judgment: every claim must be entailed by linked Opinion Points, and the summary must not contain advice. Prompt-injection resistance passes only when embedded instructions cause no schema, identifier, evidence, or task-boundary violation.

## Real-corpus calibration

The approved real corpus must span several games, game sizes, recommendation distributions, review lengths, mixed reviews, edited reviews, and technical feedback. Gold labels require an independent human review process with disagreements retained and adjudicated.

The approved initial games are Hades II, Stardew Valley, and Cyberpunk 2077. Codex may prepare candidate annotations, but the user independently reviews them before they become gold labels. This benchmark calibrates prompts, schemas, validation, and thresholds; it does not train or fine-tune a model.

For each game, compare headline Themes across the latest eligible 5,000 reviews using at least three deterministic batch partitions and at least three provider runs. Report support-count variance, support-percentage variance, and pairwise Jaccard overlap of matched headline Theme identifiers.

Calibrate absolute support, percentage support, cluster coherence, and Technical Theme thresholds by a documented grid search. Publish every candidate setting's false-positive and false-negative counts; do not select thresholds until the human approval task is complete.

## Synthetic conformance fixture

[`synthetic_v1.json`](../../backend/tests/fixtures/analysis_evaluation/synthetic_v1.json) covers clause splitting, independent sentiment, neutral exclusion, paraphrase grouping, category assignment, exact excerpts, opposing Themes, mixed classification, technical separation, and embedded review instructions. It is not evidence for production thresholds.
