"""Benchmark installed Ollama models against the local human-reviewed pilot."""

import argparse
import json
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.application.provider_benchmark import score_extraction
from game_review_analyzer.domain.analysis import AnalysisSourceReview
from game_review_analyzer.infrastructure.ollama import OllamaProvider
from game_review_analyzer.infrastructure.ollama import OllamaError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+", help="Exact installed Ollama model tags")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("evaluation-data/real_adjudicated_pilot_v1.json"),
    )
    parser.add_argument(
        "--additions",
        type=Path,
        default=Path("evaluation-data/extraction_gold_additions_pilot_v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation-data/ollama_pilot_benchmark_v1.json"),
    )
    arguments = parser.parse_args()
    corpus: dict[str, Any] = json.loads(arguments.corpus.read_text(encoding="utf-8"))
    additions: dict[str, Any] = json.loads(
        arguments.additions.read_text(encoding="utf-8")
    )
    runs: list[dict[str, Any]] = []
    for model in arguments.models:
        print(f"Benchmarking {model}", flush=True)
        model_games: list[dict[str, Any]] = []
        for game in corpus["games"]:
            print(f"  {game['title']} ({len(game['reviews'])} reviews)", flush=True)
            request = build_analysis_request(
                request_id=f"ollama-pilot-{uuid4()}",
                app_id=game["app_id"],
                game_title=game["title"],
                reviews=(
                    AnalysisSourceReview(
                        review_revision_id=review["review_revision_id"],
                        text=review["text"],
                    )
                    for review in game["reviews"]
                ),
            )
            started_at: float = monotonic()
            try:
                provider_run = OllamaProvider(model=model).analyze(request)
            except OllamaError as error:
                duration_seconds = monotonic() - started_at
                cause_code: str | None = getattr(error.__cause__, "code", None)
                model_games.append({
                    "case_id": game["case_id"],
                    "duration_seconds": round(duration_seconds, 3),
                    "error_code": error.code,
                    "validation_code": cause_code,
                })
                print(
                    f"    FAILED {error.code}"
                    f"{f' ({cause_code})' if cause_code else ''}; "
                    f"{duration_seconds:.1f}s",
                    flush=True,
                )
                continue
            duration_seconds: float = monotonic() - started_at
            gold = [
                (
                    point["review_revision_id"],
                    point["excerpt"],
                    point["sentiment"],
                )
                for point in game["opinion_points"]
            ]
            gold.extend(
                (item["review_revision_id"], item["excerpt"], "unlabeled")
                for item in additions["items"]
                if any(
                    review["review_revision_id"] == item["review_revision_id"]
                    for review in game["reviews"]
                )
            )
            predicted = tuple(
                (point.review_revision_id, point.excerpt, point.sentiment.value)
                for point in provider_run.result.opinion_points
            )
            score = score_extraction(gold=tuple(gold), predicted=predicted)
            model_games.append({
                "case_id": game["case_id"],
                "duration_seconds": round(duration_seconds, 3),
                "input_tokens": provider_run.usage.input_tokens,
                "output_tokens": provider_run.usage.output_tokens,
                "theme_count": len(provider_run.result.themes),
                "opinion_point_count": len(predicted),
                "score": score.__dict__,
            })
            print(
                f"    F1 {score.f1:.1%}; {duration_seconds:.1f}s; "
                f"{len(predicted)} points",
                flush=True,
            )
        runs.append({"model": model, "games": model_games})
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "corpus": arguments.corpus.name,
        "scoring": "exact review_revision_id and excerpt; sentiment on exact matches",
        "runs": runs,
    }
    arguments.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {arguments.output}", flush=True)


if __name__ == "__main__":
    main()
