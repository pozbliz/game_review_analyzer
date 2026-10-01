"""Durable checkpoints for validated Version 3 map batches."""

from pathlib import Path

from pydantic import ValidationError

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
        row: tuple[str, str, str, str, str, int | None, int | None, int | None] | None = (
            connection.execute(
                "SELECT input_digest, provider, model, contract_version, result_json, "
                "input_tokens, cached_input_tokens, output_tokens "
                "FROM analysis_theme_batches WHERE run_id = ? AND batch_number = ?",
                (run_id, batch_number),
            ).fetchone()
        )
        if row is None:
            return None
        if row[:4] != (input_digest, provider, model, contract_version):
            connection.execute(
                "DELETE FROM analysis_theme_batches "
                "WHERE run_id = ? AND batch_number = ?",
                (run_id, batch_number),
            )
            return None
        try:
            result = ThemeAnalysisResult.model_validate_json(row[4])
        except (ValidationError, ValueError):
            connection.execute(
                "DELETE FROM analysis_theme_batches "
                "WHERE run_id = ? AND batch_number = ?",
                (run_id, batch_number),
            )
            return None
    return ThemeProviderRun(
        result=result,
        usage=ProviderUsage(row[5], row[6], row[7]),
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
