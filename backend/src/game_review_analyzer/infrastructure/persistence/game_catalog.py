"""SQLite persistence for the synchronized Steam game catalog."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.game_catalog import CatalogGame, GameSearchResult


def save_catalog_games(database_path: Path, games: tuple[CatalogGame, ...]) -> None:
    """Upsert one normalized catalog page without deleting unaffected entries."""

    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO steam_catalog_games(app_id, name, last_modified, price_change_number) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(app_id) DO UPDATE SET "
            "name = excluded.name, last_modified = excluded.last_modified, "
            "price_change_number = excluded.price_change_number",
            ((game.app_id, game.name, game.last_modified, game.price_change_number) for game in games),
        )


def search_catalog(
    database_path: Path, query: str, limit: int = 20
) -> tuple[GameSearchResult, ...]:
    """Search locally retained catalog names case-insensitively."""

    escaped_query: str = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with sqlite3.connect(database_path) as connection:
        rows: list[tuple[int, str]] = connection.execute(
            "SELECT app_id, name FROM steam_catalog_games "
            "WHERE name LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "ORDER BY CASE WHEN name LIKE ? ESCAPE '\\' COLLATE NOCASE THEN 0 ELSE 1 END, "
            "name COLLATE NOCASE, app_id LIMIT ?",
            (f"%{escaped_query}%", f"{escaped_query}%", limit),
        ).fetchall()
    return tuple(
        GameSearchResult(app_id=app_id, title=name, source="catalog")
        for app_id, name in rows
    )


def catalog_sync_timestamp(database_path: Path) -> int:
    """Return the last fully completed catalog synchronization timestamp."""

    with sqlite3.connect(database_path) as connection:
        row: tuple[int] | None = connection.execute(
            "SELECT synced_at FROM steam_catalog_state WHERE id = 1"
        ).fetchone()
    return row[0] if row else 0


def save_catalog_sync_timestamp(database_path: Path, synced_at: int) -> None:
    """Record the next safe incremental synchronization boundary."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO steam_catalog_state(id, synced_at) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET synced_at = excluded.synced_at",
            (synced_at,),
        )
