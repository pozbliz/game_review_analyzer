"""Prepare privacy-minimized deterministic inputs for headline stability runs."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.evaluation_corpus import (
    PartitionStrategy,
    partition_reviews_for_evaluation,
)
from game_review_analyzer.application.stability_evaluation import (
    stability_result_json_schema,
)
from game_review_analyzer.domain.reviews import SteamReview


STRATEGIES: tuple[PartitionStrategy, ...] = (
    "contiguous",
    "interleaved",
    "hashed",
)


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
        default=Path("evaluation-data/stability-v1-runs"),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    arguments = parser.parse_args()
    corpus: dict[str, Any] = json.loads(arguments.corpus.read_text(encoding="utf-8"))
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    result_schema: dict[str, Any] = stability_result_json_schema()

    written: int = 0
    for game in corpus["games"]:
        reviews: tuple[SteamReview, ...] = tuple(
            SteamReview.model_validate(review) for review in game["reviews"]
        )
        for strategy in STRATEGIES:
            run_id: str = f"{game['case_id']}-{strategy}"
            run_directory: Path = arguments.output_directory / run_id
            run_directory.mkdir(parents=True, exist_ok=True)
            (run_directory / "result-schema.json").write_text(
                json.dumps(result_schema, indent=2), encoding="utf-8"
            )
            batches: tuple[tuple[SteamReview, ...], ...] = (
                partition_reviews_for_evaluation(
                    reviews,
                    strategy,
                    batch_size=arguments.batch_size,
                )
            )
            run_input: dict[str, Any] = {
                "schema_version": "1.0",
                "run_id": run_id,
                "game_case_id": game["case_id"],
                "app_id": game["app_id"],
                "game_title": game["title"],
                "model": "gpt-5.6-luna",
                "reasoning_effort": "medium",
                "partition_strategy": strategy,
                "review_count": len(reviews),
                "batches": [
                    {
                        "batch_id": f"batch-{index:03d}",
                        "reviews": [
                            {
                                "review_revision_id": review.review_id,
                                "text": review.text,
                            }
                            for review in batch
                        ],
                    }
                    for index, batch in enumerate(batches, start=1)
                ],
            }
            output_path: Path = run_directory / "input.json"
            output_path.write_text(
                json.dumps(run_input, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            written += 1
    print(f"Wrote {written} isolated run directories to {arguments.output_directory}")


if __name__ == "__main__":
    main()
