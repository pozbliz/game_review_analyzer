"""Application configuration with safe, environment-driven defaults."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the application shell."""

    environment: str = "development"
    database_path: Path = Path("data/game-review-analyzer.sqlite3")
    frontend_dist_path: Path = Path("../frontend/dist")

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
        )
