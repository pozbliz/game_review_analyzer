"""Tests for exact human-gold provider benchmark scoring."""

from game_review_analyzer.application.provider_benchmark import score_extraction


def test_score_extraction_uses_exact_review_excerpt_pairs_and_sentiment() -> None:
    score = score_extraction(
        gold=(
            ("r1", "Great combat", "positive"),
            ("r2", "Slow start", "negative"),
        ),
        predicted=(
            ("r1", "Great combat", "positive"),
            ("r2", "Slow start", "neutral"),
            ("r2", "Extra claim", "negative"),
        ),
    )

    assert score.true_positives == 2
    assert score.false_positives == 1
    assert score.false_negatives == 0
    assert score.precision == 2 / 3
    assert score.recall == 1
    assert score.f1 == 0.8
    assert score.sentiment_accuracy == 0.5
