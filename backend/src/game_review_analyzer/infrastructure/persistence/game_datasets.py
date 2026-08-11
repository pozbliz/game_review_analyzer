"""SQLite persistence for the current Game Dataset metadata preview."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.steam_metadata import SteamMetadata


def save_game_dataset(database_path: Path, metadata: SteamMetadata) -> None:
    """Insert or replace the current normalized preview for one AppID."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO game_datasets(app_id, metadata_json) VALUES (?, ?) "
            "ON CONFLICT(app_id) DO UPDATE SET "
            "metadata_json = excluded.metadata_json, updated_at = CURRENT_TIMESTAMP",
            (metadata.app_id, metadata.model_dump_json()),
        )


def load_game_dataset(database_path: Path, app_id: int) -> SteamMetadata | None:
    """Return the stored metadata preview for an AppID when it exists."""

    with sqlite3.connect(database_path) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT metadata_json FROM game_datasets WHERE app_id = ?",
            (app_id,),
        ).fetchone()
    return SteamMetadata.model_validate_json(row[0]) if row else None
