"""Download a small local-only review subset for human gold-label evaluation."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.evaluation_corpus import select_balanced_reviews
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.steam_reviews import SteamReviewIngestionAdapter

GAMES: tuple[tuple[str, int, str], ...] = (
    ("hades-ii", 1145350, "Hades II"),
    ("stardew-valley", 413150, "Stardew Valley"),
    ("cyberpunk-2077", 1091500, "Cyberpunk 2077"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-recommendation", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation-data/real_raw_v1.json"),
    )
    arguments = parser.parse_args()
    source = SteamReviewIngestionAdapter()
    games: list[dict[str, Any]] = []

    for case_id, app_id, title in GAMES:
        collected: list[SteamReview] = []
        selected: tuple[SteamReview, ...] = ()
        for page_number, page in enumerate(source.iter_pages(app_id), start=1):
            collected.extend(page.reviews)
            selected = select_balanced_reviews(collected, arguments.per_recommendation)
            if recommendation_counts(selected) == {
                True: arguments.per_recommendation,
                False: arguments.per_recommendation,
            }:
                break
            if page_number >= arguments.max_pages:
                raise RuntimeError(f"{title} did not satisfy both review quotas")
        games.append(
            {
                "case_id": case_id,
                "app_id": app_id,
                "title": title,
                "style": "real recent balanced recommendation subset",
                "reviews": [review.model_dump(mode="json") for review in selected],
                "opinion_points": [],
                "themes": [],
                "mechanic_classifications": [],
            }
        )

    corpus: dict[str, Any] = {
        "schema_version": "1.0",
        "corpus_kind": "real_candidate",
        "selection": {
            "per_recommendation": arguments.per_recommendation,
            "maximum_pages_per_game": arguments.max_pages,
            "ordering": "Steam recent source order",
        },
        "games": games,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(f"Wrote {sum(len(game['reviews']) for game in games)} reviews to {arguments.output}")


def recommendation_counts(reviews: tuple[SteamReview, ...]) -> dict[bool, int]:
    return {
        True: sum(review.recommended for review in reviews),
        False: sum(not review.recommended for review in reviews),
    }


if __name__ == "__main__":
    main()
