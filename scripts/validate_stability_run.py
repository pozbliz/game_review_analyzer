"""Validate one structured stability output against its exact run input."""

import argparse
import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.stability_evaluation import (
    StabilityResult,
    apply_stability_evidence_repair,
    validate_stability_result,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repair", type=Path)
    parser.add_argument("--rejected-theme", action="append", default=[])
    parser.add_argument("--merged-output", type=Path)
    arguments = parser.parse_args()
    run_input: dict[str, Any] = json.loads(arguments.input.read_text(encoding="utf-8"))
    result_json: str = arguments.output.read_text(encoding="utf-8")
    if arguments.repair:
        if not arguments.rejected_theme or not arguments.merged_output:
            parser.error("--repair requires --rejected-theme and --merged-output")
        result: StabilityResult = apply_stability_evidence_repair(
            run_input,
            result_json,
            arguments.repair.read_text(encoding="utf-8"),
            set(arguments.rejected_theme),
        )
        arguments.merged_output.write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
    else:
        result = validate_stability_result(run_input, result_json)
    print(f"Validated {result.run_id}: {len(result.themes)} Themes")


if __name__ == "__main__":
    main()
