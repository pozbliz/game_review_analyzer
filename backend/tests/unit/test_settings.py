"""Regional and secret runtime configuration tests."""

from pathlib import Path

import pytest

from game_review_analyzer.shared.config import Settings


def test_steam_region_is_normalized_and_key_is_hidden_from_repr() -> None:
    settings = Settings(steam_country_code="jp", steam_web_api_key="secret-key")

    assert settings.steam_country_code == "JP"
    assert "secret-key" not in repr(settings)


def test_invalid_steam_region_is_rejected() -> None:
    with pytest.raises(ValueError, match="country code"):
        Settings(steam_country_code="Japan")


def test_environment_example_lists_supported_settings_without_a_secret() -> None:
    example_path: Path = Path(__file__).parents[3] / ".env.example"
    values: dict[str, str] = dict(
        line.split("=", maxsplit=1)
        for line in example_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )

    assert set(values) == {
        "GAME_REVIEW_ANALYZER_ENV",
        "GAME_REVIEW_ANALYZER_DATABASE",
        "GAME_REVIEW_ANALYZER_FRONTEND_DIST",
        "GAME_REVIEW_ANALYZER_STEAM_COUNTRY",
        "GAME_REVIEW_ANALYZER_STEAM_WEB_API_KEY",
    }
    assert values["GAME_REVIEW_ANALYZER_STEAM_WEB_API_KEY"] == ""
