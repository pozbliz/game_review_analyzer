"""Paginated Steam review ingestion with bounded source handling."""

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from time import sleep
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import ValidationError

from game_review_analyzer.domain.reviews import SteamReview


class SteamReviewsUnavailable(Exception):
    """Signal that a caller may retry review acquisition after a source failure."""


class SteamReviewsMalformed(Exception):
    """Signal that Steam returned a review page that cannot be normalized safely."""


class ReviewCursorRepeated(Exception):
    """Stop callers from looping forever when Steam repeats a pagination cursor."""


@dataclass(frozen=True)
class ReviewPage:
    """Carry one normalized page and the exact cursor needed for its checkpoint."""

    reviews: tuple[SteamReview, ...]
    next_cursor: str


@dataclass(frozen=True)
class ReviewLanguageCount:
    """Expose Steam's current review total for one language."""

    language: str
    review_count: int


class ReviewLanguageSource(Protocol):
    """Load Steam review totals grouped by supported API language."""

    def fetch(self, app_id: int) -> tuple[ReviewLanguageCount, ...]:
        """Return non-empty language totals for one game."""


STEAM_REVIEW_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("arabic", "Arabic"),
    ("bulgarian", "Bulgarian"),
    ("schinese", "Chinese (Simplified)"),
    ("tchinese", "Chinese (Traditional)"),
    ("czech", "Czech"),
    ("danish", "Danish"),
    ("dutch", "Dutch"),
    ("english", "English"),
    ("finnish", "Finnish"),
    ("french", "French"),
    ("german", "German"),
    ("greek", "Greek"),
    ("hungarian", "Hungarian"),
    ("indonesian", "Indonesian"),
    ("italian", "Italian"),
    ("japanese", "Japanese"),
    ("koreana", "Korean"),
    ("malay", "Malay"),
    ("norwegian", "Norwegian"),
    ("polish", "Polish"),
    ("portuguese", "Portuguese"),
    ("brazilian", "Portuguese-Brazil"),
    ("romanian", "Romanian"),
    ("russian", "Russian"),
    ("spanish", "Spanish-Spain"),
    ("latam", "Spanish-Latin America"),
    ("swedish", "Swedish"),
    ("thai", "Thai"),
    ("turkish", "Turkish"),
    ("ukrainian", "Ukrainian"),
    ("vietnamese", "Vietnamese"),
)


class SteamReviewLanguageAdapter:
    """Load per-language review totals from Steam only when requested."""

    def __init__(
        self,
        open_url: Callable[..., Any] = urlopen,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._open_url = open_url
        self._timeout_seconds = timeout_seconds

    def fetch(self, app_id: int) -> tuple[ReviewLanguageCount, ...]:
        """Return nonzero language totals, largest first."""

        if app_id <= 0:
            raise ValueError("AppID must be a positive integer")
        with ThreadPoolExecutor(max_workers=4) as executor:
            counts: tuple[ReviewLanguageCount, ...] = tuple(
                executor.map(
                    lambda item: self._fetch_language(app_id, *item),
                    STEAM_REVIEW_LANGUAGES,
                )
            )
        return tuple(
            sorted(
                (item for item in counts if item.review_count > 0),
                key=lambda item: (-item.review_count, item.language),
            )
        )

    def _fetch_language(
        self,
        app_id: int,
        language_code: str,
        language_name: str,
    ) -> ReviewLanguageCount:
        query: str = urlencode({
            "json": 1,
            "filter": "recent",
            "language": language_code,
            "purchase_type": "all",
            "num_per_page": 1,
            "filter_offtopic_activity": 1,
        })
        request = Request(
            f"https://store.steampowered.com/appreviews/{app_id}?{query}",
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        try:
            with self._open_url(request, timeout=self._timeout_seconds) as response:
                payload: Any = json.loads(response.read())
        except (OSError, URLError) as error:
            raise SteamReviewsUnavailable("Steam review summary request failed") from error
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            raise SteamReviewsMalformed("Steam returned invalid review summary JSON") from error
        summary: Any = payload.get("query_summary") if isinstance(payload, dict) else None
        total: Any = summary.get("total_reviews") if isinstance(summary, dict) else None
        if (
            not isinstance(payload, dict)
            or payload.get("success") != 1
            or not isinstance(total, int)
            or total < 0
        ):
            raise SteamReviewsMalformed("Steam review summary omitted its total")
        return ReviewLanguageCount(language=language_name, review_count=total)


class SteamReviewIngestionAdapter:
    """Yield eligible English Steam review pages with pacing and bounded retries."""

    def __init__(
        self,
        open_url: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = sleep,
        timeout_seconds: float = 15.0,
        pace_seconds: float = 2.0,
        max_attempts: int = 3,
    ) -> None:
        self._open_url = open_url
        self._sleep = sleep
        self._timeout_seconds = timeout_seconds
        self._pace_seconds = pace_seconds
        self._max_attempts = max_attempts

    def iter_pages(self, app_id: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        """Yield pages until Steam is exhausted or repeats a cursor."""

        if app_id <= 0:
            raise ValueError("AppID must be a positive integer")
        cursor: str = start_cursor
        seen_cursors: set[str] = set()
        while True:
            if cursor in seen_cursors:
                raise ReviewCursorRepeated(f"Steam repeated cursor {cursor!r}")
            seen_cursors.add(cursor)
            page: ReviewPage = self._fetch_page(app_id, cursor)
            yield page
            if not page.reviews:
                return
            self._sleep(self._pace_seconds)
            cursor = page.next_cursor

    def _fetch_page(self, app_id: int, cursor: str) -> ReviewPage:
        query = urlencode(
            {
                "json": 1,
                "filter": "recent",
                "language": "english",
                "purchase_type": "all",
                "num_per_page": 100,
                "filter_offtopic_activity": 1,
                "cursor": cursor,
            }
        )
        request = Request(
            f"https://store.steampowered.com/appreviews/{app_id}?{query}",
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        for attempt in range(self._max_attempts):
            try:
                with self._open_url(request, timeout=self._timeout_seconds) as response:
                    payload: Any = json.loads(response.read())
                return self._normalize_page(payload)
            except (OSError, URLError) as error:
                if attempt + 1 == self._max_attempts:
                    raise SteamReviewsUnavailable("Steam review request failed") from error
                delay_seconds: float = float(2**attempt)
                if isinstance(error, HTTPError) and error.code == 429:
                    retry_after: str | None = (
                        error.headers.get("Retry-After") if error.headers else None
                    )
                    delay_seconds = (
                        float(retry_after)
                        if retry_after and retry_after.isdecimal()
                        else float(30 * (2**attempt))
                    )
                self._sleep(delay_seconds)
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
                raise SteamReviewsMalformed("Steam returned invalid review JSON") from error
        raise AssertionError("bounded retry loop exited unexpectedly")

    @staticmethod
    def _normalize_page(payload: Any) -> ReviewPage:
        if not isinstance(payload, dict) or payload.get("success") != 1:
            raise SteamReviewsMalformed("Steam review response was unsuccessful")
        raw_reviews: Any = payload.get("reviews")
        next_cursor: Any = payload.get("cursor")
        if not isinstance(raw_reviews, list) or not isinstance(next_cursor, str):
            raise SteamReviewsMalformed("Steam review page omitted pagination data")

        reviews: list[SteamReview] = []
        for raw_review in raw_reviews:
            if not isinstance(raw_review, dict):
                raise SteamReviewsMalformed("Steam review entry must be an object")
            if raw_review.get("language") != "english":
                continue
            try:
                review_text: Any = raw_review["review"]
                if isinstance(review_text, str) and not review_text.strip():
                    continue
                author: Any = raw_review["author"]
                if not isinstance(author, dict):
                    raise TypeError("author must be an object")
                playtime_at_review: Any = author.get("playtime_at_review")
                reviews.append(
                    SteamReview(
                        review_id=str(raw_review["recommendationid"]),
                        language="english",
                        text=review_text,
                        source_created_at=raw_review["timestamp_created"],
                        source_updated_at=raw_review["timestamp_updated"],
                        recommended=raw_review["voted_up"],
                        votes_helpful=raw_review["votes_up"],
                        votes_funny=raw_review["votes_funny"],
                        weighted_vote_score=float(raw_review["weighted_vote_score"]),
                        steam_purchase=raw_review["steam_purchase"],
                        received_for_free=raw_review["received_for_free"],
                        written_during_early_access=raw_review[
                            "written_during_early_access"
                        ],
                        playtime_forever_minutes=author["playtime_forever"],
                        playtime_at_review_minutes=playtime_at_review,
                    )
                )
            except (KeyError, TypeError, ValueError, ValidationError) as error:
                raise SteamReviewsMalformed("Steam review entry could not be normalized") from error
        return ReviewPage(reviews=tuple(reviews), next_cursor=next_cursor)
