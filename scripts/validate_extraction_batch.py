"""Validate one Opinion Point extraction output against its package request."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.manual_codex import (
    validate_manual_codex_extraction_result,
)
from game_review_analyzer.domain.analysis import AnalysisRequest, OpinionExtractionResult


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    package: dict[str, Any] = json.loads(arguments.package.read_text(encoding="utf-8"))
    request: AnalysisRequest = AnalysisRequest.model_validate(package["request"])
    result: OpinionExtractionResult = validate_manual_codex_extraction_result(
        request, arguments.output.read_text(encoding="utf-8")
    )
    print(
        f"Validated {result.request_id}: {len(result.completed_review_revision_ids)} "
        f"reviews, {len(result.opinion_points)} Opinion Points"
    )


if __name__ == "__main__":
    main()
