"""Application configuration with safe, environment-driven defaults."""

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the application shell."""

    environment: str = "development"
    database_path: Path = Path("data/game-review-analyzer.sqlite3")
    frontend_dist_path: Path = Path("../frontend/dist")
    steam_web_api_key: str | None = field(default=None, repr=False)
    steam_country_code: str = "US"

    def __post_init__(self) -> None:
        """Normalize and validate the two-letter Steam store country code."""

        country_code: str = self.steam_country_code.upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError("Steam country code must contain two letters")
        object.__setattr__(self, "steam_country_code", country_code)

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from supported environment variables."""

        database_path = os.getenv("GAME_REVIEW_ANALYZER_DATABASE", str(cls.database_path))
        return cls(
            environment=os.getenv("GAME_REVIEW_ANALYZER_ENV", cls.environment),
            database_path=Path(database_path),
            frontend_dist_path=Path(
                os.getenv(
                    "GAME_REVIEW_ANALYZER_FRONTEND_DIST",
                    str(cls.frontend_dist_path),
                )
            ),
            steam_web_api_key=os.getenv("GAME_REVIEW_ANALYZER_STEAM_WEB_API_KEY"),
            steam_country_code=os.getenv(
                "GAME_REVIEW_ANALYZER_STEAM_COUNTRY", cls.steam_country_code
            ).upper(),
        )
