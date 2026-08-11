"""SQLite integration tests for initial Game Dataset persistence."""

from pathlib import Path

from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    schema_version,
)
from game_review_analyzer.infrastructure.persistence.game_datasets import (
    load_game_dataset,
    save_game_dataset,
)


def test_metadata_preview_round_trips_as_initial_game_dataset(tmp_path: Path) -> None:
    database_path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    metadata = SteamMetadata(
        app_id=1145350,
        title="Hades II",
        developers=("Supergiant Games",),
        capsule_image_url=None,
        release_date=None,
        release_status="unknown",
        review_count=None,
        source_status="partial",
        missing_fields=frozenset(
            {"capsule_image_url", "release_date", "release_status", "review_count"}
        ),
    )

    save_game_dataset(database_path, metadata)

    assert CURRENT_SCHEMA_VERSION == 2
    assert schema_version(database_path) == 2
    assert load_game_dataset(database_path, 1145350) == metadata
    assert load_game_dataset(database_path, 999999999) is None
