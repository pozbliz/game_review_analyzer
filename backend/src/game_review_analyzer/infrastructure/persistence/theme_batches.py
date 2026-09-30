"""Durable checkpoints for validated Version 3 map batches."""

from pathlib import Path

from game_review_analyzer.application.provider import ProviderUsage, ThemeProviderRun
from game_review_analyzer.domain.analysis import ThemeAnalysisResult
from game_review_analyzer.infrastructure.persistence.jobs import connect


def load_theme_batch(
    database_path: Path,
    *,
    run_id: str,
    batch_number: int,
    input_digest: str,
    provider: str,
    model: str,
    contract_version: str,
) -> ThemeProviderRun | None:
    """Load one checkpoint only when its exact input and provenance match."""

    with connect(database_path) as connection:
        row: tuple[str, int | None, int | None, int | None] | None = (
            connection.execute(
                "SELECT result_json, input_tokens, cached_input_tokens, output_tokens "
                "FROM analysis_theme_batches WHERE run_id = ? AND batch_number = ? "
                "AND input_digest = ? AND provider = ? AND model = ? "
                "AND contract_version = ?",
                (
                    run_id,
                    batch_number,
                    input_digest,
                    provider,
                    model,
                    contract_version,
                ),
            ).fetchone()
        )
    if row is None:
        return None
    return ThemeProviderRun(
        result=ThemeAnalysisResult.model_validate_json(row[0]),
        usage=ProviderUsage(row[1], row[2], row[3]),
    )


def save_theme_batch(
    database_path: Path,
    *,
    run_id: str,
    batch_number: int,
    input_digest: str,
    provider: str,
    model: str,
    contract_version: str,
    provider_run: ThemeProviderRun,
) -> None:
    """Persist one validated map result and measured usage atomically."""

    with connect(database_path) as connection:
        connection.execute(
            "INSERT INTO analysis_theme_batches("
            "run_id, batch_number, input_digest, provider, model, contract_version, "
            "result_json, input_tokens, cached_input_tokens, output_tokens) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                batch_number,
                input_digest,
                provider,
                model,
                contract_version,
                provider_run.result.model_dump_json(),
                provider_run.usage.input_tokens,
                provider_run.usage.cached_input_tokens,
                provider_run.usage.output_tokens,
            ),
        )
