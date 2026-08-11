"""Synchronize and query local-first Steam game discovery."""

from collections.abc import Iterator
from pathlib import Path
import time
from typing import Protocol

from game_review_analyzer.domain.game_catalog import (
    CatalogPage,
    CatalogSyncResult,
    GameSearchResult,
)
from game_review_analyzer.infrastructure.persistence.game_catalog import (
    catalog_sync_timestamp,
    save_catalog_games,
    save_catalog_sync_timestamp,
    search_catalog,
)


class CatalogSource(Protocol):
    """Provide incremental pages from a keyed game catalog source."""

    def iter_pages(
        self, api_key: str, if_modified_since: int
    ) -> Iterator[CatalogPage]:
        """Yield every page required for one incremental synchronization."""


class FallbackSearchSource(Protocol):
    """Provide replaceable unkeyed search when the local catalog has no match."""

    def search(self, query: str, country_code: str) -> tuple[GameSearchResult, ...]:
        """Return bounded normalized matches for one query and region."""


def synchronize_catalog(
    database_path: Path,
    source: CatalogSource,
    api_key: str,
    synced_at: int | None = None,
) -> CatalogSyncResult:
    """Persist one complete incremental catalog synchronization."""

    previous_sync: int = catalog_sync_timestamp(database_path)
    next_sync: int = int(time.time()) if synced_at is None else synced_at
    updated_count: int = 0
    for page in source.iter_pages(api_key, previous_sync):
        save_catalog_games(database_path, page.games)
        updated_count += len(page.games)
    save_catalog_sync_timestamp(database_path, next_sync)
    return CatalogSyncResult(updated_game_count=updated_count, synced_at=next_sync)


def search_games(
    database_path: Path,
    fallback: FallbackSearchSource,
    query: str,
    country_code: str,
) -> tuple[GameSearchResult, ...]:
    """Prefer durable catalog matches, using remote fallback only when empty."""

    normalized_query: str = query.strip()
    if len(normalized_query) < 2:
        raise ValueError("Search query must contain at least two characters")
    local_results: tuple[GameSearchResult, ...] = search_catalog(
        database_path, normalized_query
    )
    return local_results or fallback.search(normalized_query, country_code)
