"""Exact human-gold extraction scoring for provider evaluation."""

from dataclasses import dataclass


LabeledExcerpt = tuple[str, str, str]


@dataclass(frozen=True)
class ExtractionScore:
    """Report exact extraction and matched-sentiment quality."""

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    sentiment_accuracy: float | None


def score_extraction(
    *, gold: tuple[LabeledExcerpt, ...], predicted: tuple[LabeledExcerpt, ...]
) -> ExtractionScore:
    """Compare exact review/excerpt pairs and sentiment on matched pairs."""

    gold_by_evidence: dict[tuple[str, str], str] = {
        (review_id, excerpt): sentiment for review_id, excerpt, sentiment in gold
    }
    predicted_by_evidence: dict[tuple[str, str], str] = {
        (review_id, excerpt): sentiment
        for review_id, excerpt, sentiment in predicted
    }
    matched: set[tuple[str, str]] = set(gold_by_evidence) & set(
        predicted_by_evidence
    )
    true_positives: int = len(matched)
    false_positives: int = len(set(predicted_by_evidence) - set(gold_by_evidence))
    false_negatives: int = len(set(gold_by_evidence) - set(predicted_by_evidence))
    precision: float = _ratio(true_positives, true_positives + false_positives)
    recall: float = _ratio(true_positives, true_positives + false_negatives)
    f1: float = _ratio(2 * precision * recall, precision + recall)
    sentiment_accuracy: float | None = (
        sum(
            gold_by_evidence[evidence] == predicted_by_evidence[evidence]
            for evidence in matched
        )
        / len(matched)
        if matched
        else None
    )
    return ExtractionScore(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        sentiment_accuracy=sentiment_accuracy,
    )


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0
