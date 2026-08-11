"""Regional and secret runtime configuration tests."""

import pytest

from game_review_analyzer.shared.config import Settings


def test_steam_region_is_normalized_and_key_is_hidden_from_repr() -> None:
    settings = Settings(steam_country_code="jp", steam_web_api_key="secret-key")

    assert settings.steam_country_code == "JP"
    assert "secret-key" not in repr(settings)


def test_invalid_steam_region_is_rejected() -> None:
    with pytest.raises(ValueError, match="country code"):
        Settings(steam_country_code="Japan")
