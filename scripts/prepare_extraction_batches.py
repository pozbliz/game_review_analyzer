"""Prepare isolated Manual Codex packages for bounded Opinion Point extraction."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.evaluation_corpus import (
    partition_reviews_for_evaluation,
)
from game_review_analyzer.application.manual_codex import (
    export_manual_codex_extraction_package,
)
from game_review_analyzer.domain.analysis import AnalysisSourceReview
from game_review_analyzer.domain.reviews import SteamReview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("evaluation-data/stability_raw_v1.json"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("evaluation-data/extraction-v1"),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    arguments = parser.parse_args()
    corpus: dict[str, Any] = json.loads(arguments.corpus.read_text(encoding="utf-8"))
    written: int = 0
    for game in corpus["games"]:
        reviews: tuple[SteamReview, ...] = tuple(
            SteamReview.model_validate(review) for review in game["reviews"]
        )
        batches: tuple[tuple[SteamReview, ...], ...] = (
            partition_reviews_for_evaluation(
                reviews, "contiguous", batch_size=arguments.batch_size
            )
        )
        for index, batch in enumerate(batches, start=1):
            request_id: str = f"{game['case_id']}-extract-{index:03d}"
            package: dict[str, Any] = json.loads(
                export_manual_codex_extraction_package(
                    request_id=request_id,
                    app_id=game["app_id"],
                    game_title=game["title"],
                    reviews=(
                        AnalysisSourceReview(
                            review_revision_id=review.review_id,
                            text=review.text,
                        )
                        for review in batch
                    ),
                )
            )
            batch_directory: Path = arguments.output_directory / request_id
            batch_directory.mkdir(parents=True, exist_ok=True)
            (batch_directory / "package.json").write_text(
                json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (batch_directory / "result-schema.json").write_text(
                json.dumps(package["result_json_schema"], indent=2), encoding="utf-8"
            )
            written += 1
    print(f"Wrote {written} extraction batches to {arguments.output_directory}")


if __name__ == "__main__":
    main()
