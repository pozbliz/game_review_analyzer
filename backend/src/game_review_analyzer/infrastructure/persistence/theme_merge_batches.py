"""Durable checkpoints for validated Version 3 merge batches."""

import sqlite3
from pathlib import Path

from pydantic import ValidationError

from game_review_analyzer.application.provider import (
    ProviderUsage,
    ThemeMergeProviderRun,
    validate_theme_merge_result,
)
from game_review_analyzer.domain.analysis import ThemeMergeRequest, ThemeMergeResult
from game_review_analyzer.infrastructure.persistence.jobs import connect


def load_theme_merge_batch(
    database_path: Path,
    *,
    run_id: str,
    polarity: str,
    batch_number: int,
    request: ThemeMergeRequest,
    provider: str,
    model: str,
    contract_version: str,
) -> ThemeMergeProviderRun | None:
    """Load one merge checkpoint only when its request and provenance match."""

    with connect(database_path) as connection:
        row: (
            tuple[str, str, str, str, str, int | None, int | None, int | None]
            | None
        ) = connection.execute(
            "SELECT input_digest, provider, model, contract_version, result_json, "
            "input_tokens, cached_input_tokens, output_tokens "
            "FROM analysis_theme_merge_batches "
            "WHERE run_id = ? AND polarity = ? AND batch_number = ?",
            (run_id, polarity, batch_number),
        ).fetchone()
        if row is None:
            return None
        if row[:4] != (request.scope_sha256, provider, model, contract_version):
            _delete_batch(connection, run_id, polarity, batch_number)
            return None
        try:
            result = ThemeMergeResult.model_validate_json(row[4])
            validate_theme_merge_result(
                request,
                result,
                expected_provider=provider,
                expected_model=model,
            )
        except (KeyError, ValidationError, ValueError):
            _delete_batch(connection, run_id, polarity, batch_number)
            return None
    return ThemeMergeProviderRun(
        result=result,
        usage=ProviderUsage(row[5], row[6], row[7]),
    )


def save_theme_merge_batch(
    database_path: Path,
    *,
    run_id: str,
    polarity: str,
    batch_number: int,
    request: ThemeMergeRequest,
    provider: str,
    model: str,
    contract_version: str,
    provider_run: ThemeMergeProviderRun,
) -> None:
    """Persist one validated merge result and measured usage atomically."""

    with connect(database_path) as connection:
        connection.execute(
            "INSERT INTO analysis_theme_merge_batches("
            "run_id, polarity, batch_number, input_digest, provider, model, "
            "contract_version, result_json, input_tokens, cached_input_tokens, "
            "output_tokens) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                polarity,
                batch_number,
                request.scope_sha256,
                provider,
                model,
                contract_version,
                provider_run.result.model_dump_json(),
                provider_run.usage.input_tokens,
                provider_run.usage.cached_input_tokens,
                provider_run.usage.output_tokens,
            ),
        )


def _delete_batch(
    connection: sqlite3.Connection,
    run_id: str,
    polarity: str,
    batch_number: int,
) -> None:
    connection.execute(
        "DELETE FROM analysis_theme_merge_batches "
        "WHERE run_id = ? AND polarity = ? AND batch_number = ?",
        (run_id, polarity, batch_number),
    )
