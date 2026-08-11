"""Validate one structured stability output against its exact run input."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.stability_evaluation import (
    StabilityResult,
    validate_stability_result,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    run_input: dict[str, Any] = json.loads(arguments.input.read_text(encoding="utf-8"))
    result: StabilityResult = validate_stability_result(
        run_input,
        arguments.output.read_text(encoding="utf-8"),
    )
    print(f"Validated {result.run_id}: {len(result.themes)} Themes")


if __name__ == "__main__":
    main()
