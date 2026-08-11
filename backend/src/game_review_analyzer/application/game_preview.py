"""Application rules for direct-AppID metadata preview."""

from typing import Protocol

from game_review_analyzer.domain.steam_metadata import SteamMetadata


class SteamMetadataSource(Protocol):
    """Allow the preview service to use any adapter that returns normalized metadata."""

    def fetch(self, app_id: int) -> SteamMetadata:
        """Return normalized metadata for one positive AppID."""


class InvalidAppId(ValueError):
    """Tell HTTP callers to reject an AppID before accessing Steam."""


def parse_app_id(raw_app_id: str) -> int:
    """Return a validated positive AppID suitable for persistence and Steam lookup."""

    if (
        not raw_app_id.isascii()
        or not raw_app_id.isdecimal()
        or raw_app_id.startswith("0")
    ):
        raise InvalidAppId("AppID must contain only positive decimal digits")
    app_id: int = int(raw_app_id)
    if app_id > 2_147_483_647:
        raise InvalidAppId("AppID is outside the supported range")
    return app_id
