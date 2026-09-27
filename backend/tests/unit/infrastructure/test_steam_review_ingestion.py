"""Fixture-driven tests for paginated Steam review ingestion."""

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewCursorRepeated,
    SteamReviewIngestionAdapter,
    SteamReviewsUnavailable,
)

FIXTURE_DIRECTORY = Path(__file__).parents[2] / "fixtures" / "steam_reviews"


def fixture_responses(*names: str) -> Iterator[BytesIO]:
    for name in names:
        yield BytesIO((FIXTURE_DIRECTORY / name).read_bytes())


def test_adapter_encodes_cursor_filters_eligibility_and_stops_at_exhaustion() -> None:
    responses = fixture_responses("page_1.json", "page_empty.json")
    requests: list[Request] = []
    sleeps: list[float] = []

    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        assert timeout == 15.0
        requests.append(request)
        return next(responses)

    adapter = SteamReviewIngestionAdapter(open_url=open_fixture, sleep=sleeps.append)

    pages = list(adapter.iter_pages(1145350))

    assert [review.review_id for review in pages[0].reviews] == ["1001", "1002"]
    assert pages[1].reviews == ()
    assert parse_qs(urlparse(requests[1].full_url).query)["cursor"] == ["next+cursor=="]
    assert sleeps == [2.0]


def test_adapter_excludes_non_english_reviews() -> None:
    responses = fixture_responses("mixed_eligibility.json", "page_empty.json")
    adapter = SteamReviewIngestionAdapter(
        open_url=lambda *_, **__: next(responses),
        sleep=lambda _: None,
    )

    pages = list(adapter.iter_pages(1145350))

    assert [review.review_id for review in pages[0].reviews] == ["2001"]


def test_adapter_skips_recommendation_only_entries_without_review_text() -> None:
    payload = (FIXTURE_DIRECTORY / "mixed_eligibility.json").read_bytes().replace(
        b'"Eligible English review."',
        b'"   "',
    )
    adapter = SteamReviewIngestionAdapter(
        open_url=lambda *_, **__: BytesIO(payload),
        sleep=lambda _: None,
    )

    page = next(adapter.iter_pages(1145350))

    assert page.reviews == ()


def test_adapter_retries_transient_failures_with_bounded_backoff() -> None:
    attempts = 0
    sleeps: list[float] = []

    def eventually_open(*_: object, **__: object) -> BytesIO:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise URLError("temporary")
        return BytesIO((FIXTURE_DIRECTORY / "page_empty.json").read_bytes())

    adapter = SteamReviewIngestionAdapter(open_url=eventually_open, sleep=sleeps.append)

    assert list(adapter.iter_pages(1145350))[0].reviews == ()
    assert attempts == 3
    assert sleeps == [1.0, 2.0]


def test_adapter_honors_rate_limit_delay_with_safe_fallback() -> None:
    attempts: int = 0
    sleeps: list[float] = []

    def eventually_open(*_: object, **__: object) -> BytesIO:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HTTPError("", 429, "rate limited", {"Retry-After": "7"}, None)
        if attempts == 2:
            raise HTTPError("", 429, "rate limited", {}, None)
        return BytesIO((FIXTURE_DIRECTORY / "page_empty.json").read_bytes())

    adapter = SteamReviewIngestionAdapter(open_url=eventually_open, sleep=sleeps.append)

    assert list(adapter.iter_pages(1145350))[0].reviews == ()
    assert attempts == 3
    assert sleeps == [7.0, 60.0]


def test_adapter_stops_after_three_failed_attempts() -> None:
    attempts = 0

    def never_open(*_: object, **__: object) -> BytesIO:
        nonlocal attempts
        attempts += 1
        raise URLError("offline")

    adapter = SteamReviewIngestionAdapter(open_url=never_open, sleep=lambda _: None)

    with pytest.raises(SteamReviewsUnavailable):
        list(adapter.iter_pages(1145350))
    assert attempts == 3


def test_adapter_rejects_repeated_cursors() -> None:
    adapter = SteamReviewIngestionAdapter(
        open_url=lambda *_, **__: BytesIO(
            (FIXTURE_DIRECTORY / "cursor_repeat.json").read_bytes()
        ),
        sleep=lambda _: None,
    )

    with pytest.raises(ReviewCursorRepeated):
        list(adapter.iter_pages(1145350))
