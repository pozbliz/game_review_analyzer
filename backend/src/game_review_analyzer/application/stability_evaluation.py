"""Structured result contract and validation for headline-Theme stability runs."""

from typing import Any, Literal

from pydantic import Field, ValidationError

from game_review_analyzer.domain.analysis import (
    ContractModel,
    NonEmptyString,
    ThemeCategory,
    ThemePolarity,
)


class StabilityEvidence(ContractModel):
    """Reference one exact excerpt supporting a stability-run Theme."""

    review_revision_id: NonEmptyString
    excerpt: NonEmptyString


class StabilityTheme(ContractModel):
    """Carry one recurring Theme and its complete distinct-review membership."""

    theme_key: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    primary_category: ThemeCategory | Literal["Technical"]
    technical: bool
    coherence_score: float = Field(ge=0, le=1)
    supporting_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=2)
    representative_excerpts: tuple[StabilityEvidence, ...] = Field(
        min_length=1, max_length=5
    )


class StabilityResult(ContractModel):
    """Represent one structured provider run over an exact 5,000-review scope."""

    schema_version: Literal["1.0"]
    run_id: NonEmptyString
    game_case_id: NonEmptyString
    app_id: int = Field(gt=0)
    model: Literal["gpt-5.6-luna"]
    reasoning_effort: Literal["medium"]
    partition_strategy: Literal["contiguous", "interleaved", "hashed"]
    review_count: int = Field(gt=0)
    themes: tuple[StabilityTheme, ...] = Field(max_length=60)


class StabilityValidationError(ValueError):
    """Report a stable rejection code for one imported stability result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code: str = code


def stability_result_json_schema() -> dict[str, Any]:
    """Return the strict JSON Schema passed to the non-interactive Codex run."""

    return StabilityResult.model_json_schema()


def validate_stability_result(
    run_input: dict[str, Any],
    result_json: str,
) -> StabilityResult:
    """Validate one structured run against its exact local review input."""

    try:
        result: StabilityResult = StabilityResult.model_validate_json(result_json)
    except ValidationError as error:
        raise StabilityValidationError(
            "malformed_result", "Result does not match the stability schema."
        ) from error
    scope_fields: tuple[str, ...] = (
        "run_id",
        "game_case_id",
        "app_id",
        "model",
        "reasoning_effort",
        "partition_strategy",
        "review_count",
    )
    if any(getattr(result, field) != run_input.get(field) for field in scope_fields):
        raise StabilityValidationError(
            "scope_mismatch", "Result metadata does not match the stability input."
        )
    review_text_by_id: dict[str, str] = {}
    for batch in run_input.get("batches", []):
        for review in batch.get("reviews", []):
            review_text_by_id[str(review["review_revision_id"])] = str(review["text"])
    theme_keys: set[str] = {theme.theme_key for theme in result.themes}
    if len(theme_keys) != len(result.themes):
        raise StabilityValidationError(
            "duplicate_identifier", "Theme keys must be unique within a run."
        )
    for theme in result.themes:
        supporting_ids: set[str] = set(theme.supporting_review_revision_ids)
        if len(supporting_ids) != len(theme.supporting_review_revision_ids):
            raise StabilityValidationError(
                "duplicate_identifier", f"Theme {theme.theme_key} repeats support IDs."
            )
        if any(review_id not in review_text_by_id for review_id in supporting_ids):
            raise StabilityValidationError(
                "unknown_review_revision",
                f"Theme {theme.theme_key} references an unknown Review Revision.",
            )
        for evidence in theme.representative_excerpts:
            if evidence.review_revision_id not in supporting_ids:
                raise StabilityValidationError(
                    "inconsistent_theme_membership",
                    f"Theme {theme.theme_key} excerpt is outside its support set.",
                )
            if evidence.excerpt not in review_text_by_id[evidence.review_revision_id]:
                raise StabilityValidationError(
                    "non_matching_excerpt",
                    f"Theme {theme.theme_key} includes a non-exact excerpt.",
                )
    return result
