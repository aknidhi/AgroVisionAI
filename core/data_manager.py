
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Central cache directory
CACHE_DIR = PROJECT_ROOT / "data" / "cache"


def get_timestamp():
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def save_cache(data, cache_path):
    """Save successfully retrieved data to local cache."""

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = cache_path.with_suffix(
        cache_path.suffix + ".tmp"
    )

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temporary_path.replace(cache_path)


def load_cache(cache_path):
    """Load previously stored data."""

    cache_path = Path(cache_path)

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        return None


def is_cache_stale(fetched_at, max_age_hours):
    """Check whether cached data has exceeded its allowed age."""

    try:
        fetched_time = datetime.fromisoformat(
            fetched_at.replace("Z", "+00:00")
        )

        if fetched_time.tzinfo is None:
            fetched_time = fetched_time.replace(
                tzinfo=timezone.utc
            )

        age = datetime.now(timezone.utc) - fetched_time

        return age > timedelta(hours=max_age_hours)

    except (ValueError, TypeError, AttributeError):
        return True


def validate_response(response):
    """Validate the common service response structure."""

    if not isinstance(response, dict):
        raise ValueError("Invalid service response.")

    records = response.get("records")

    if not isinstance(records, list) or not records:
        raise ValueError("No valid records received.")

    return response


def fetch_with_fallback(
    primary_fetcher: Callable,
    secondary_fetcher: Optional[Callable] = None,
    cache_name="default",
    primary_name="Primary API",
    secondary_name="Secondary API",
    max_age_hours=24
):
    """
    Universal three-layer data retrieval system.

    Layer 1: Primary API
    Layer 2: Secondary API
    Layer 3: Local cache

    All providers must return a dictionary containing
    a non-empty 'records' list.
    """

    cache_path = CACHE_DIR / f"{cache_name}_cache.json"

    errors = []

    providers = [
        (primary_fetcher, primary_name),
        (secondary_fetcher, secondary_name)
    ]

    # ------------------------------------------
    # LAYER 1 & 2: LIVE API PROVIDERS
    # ------------------------------------------

    for fetcher, source_name in providers:

        if fetcher is None:
            continue

        try:
            response = validate_response(fetcher())

            result = {
                **response,
                "success": True,
                "source": source_name,
                "fetched_at": get_timestamp(),
                "status": "fresh",
                "is_stale": False,
                "warning": None,
                "errors": errors.copy()
            }

            # Save only successfully validated data.
            save_cache(result, cache_path)

            return result

        except Exception as error:

            errors.append({
                "source": source_name,
                "error": str(error)
            })

    # ------------------------------------------
    # LAYER 3: LOCAL CACHE
    # ------------------------------------------

    cached_data = load_cache(cache_path)

    if cached_data:

        fetched_at = cached_data.get("fetched_at", "")

        stale = is_cache_stale(
            fetched_at,
            max_age_hours
        )

        cached_data.update({
            "success": True,
            "status": "stale" if stale else "cached",
            "is_stale": stale,
            "warning": (
                "Live APIs are unavailable. "
                "Showing previously retrieved data."
            ),
            "errors": errors
        })

        return cached_data

    # ------------------------------------------
    # ALL SOURCES FAILED
    # ------------------------------------------

    return {
        "success": False,
        "status": "unavailable",
        "source": None,
        "records": [],
        "count": 0,
        "fetched_at": None,
        "is_stale": True,
        "warning": (
            "All data sources are unavailable "
            "and no cached data exists."
        ),
        "errors": errors
    }
