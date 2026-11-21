
import os
import re
import requests

from dotenv import load_dotenv
from core.data_manager import fetch_with_fallback

load_dotenv()


# =====================================================
# API CONFIGURATION
# =====================================================

OFFICIAL_API_URL = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)

SECONDARY_API_URL = "https://api.dharun.dev/v1/mandi"

DEFAULT_TIMEOUT = 30
SECONDARY_TIMEOUT = 20
MAX_RECORDS = 1000


# =====================================================
# COMMON HELPERS
# =====================================================

def _normalize_state(state):
    """Normalize state names for reliable comparison."""

    if not state:
        return None

    return " ".join(str(state).strip().casefold().split())


def _filter_records_by_state(records, state):
    """Keep only records belonging to the requested state."""

    if not state:
        return records

    expected = _normalize_state(state)

    return [
        record
        for record in records
        if _normalize_state(record.get("state")) == expected
    ]


def _cache_key(state):
    """Generate a separate cache key for each state."""

    if not state:
        return "mandi_prices_india"

    slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        str(state).casefold()
    ).strip("_")

    return f"mandi_prices_{slug}"


def _validate_limit(limit):
    """Validate and normalize API record limits."""

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError("Record limit must be an integer.")

    return min(max(limit, 1), MAX_RECORDS)


def _safe_total(value, fallback):
    """Safely convert API metadata into an integer."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


# =====================================================
# PRIMARY SOURCE: GOVERNMENT OF INDIA
# =====================================================

def fetch_official_mandi_prices(
    limit=1000,
    offset=0,
    state=None
):
    """
    Retrieve actual mandi prices from data.gov.in.

    Uses official Government of India AGMARKNET data.
    """

    api_key = os.getenv("DATA_GOV_API_KEY")

    if not api_key:
        raise ValueError(
            "DATA_GOV_API_KEY is missing in .env"
        )

    limit = _validate_limit(limit)

    try:
        offset = max(int(offset), 0)
    except (TypeError, ValueError):
        raise ValueError("Offset must be a non-negative integer.")

    params = {
        "api-key": api_key,
        "format": "json",
        "limit": limit,
        "offset": offset
    }

    # Request only the selected state.
    if state:
        params["filters[state]"] = state

    response = requests.get(
        OFFICIAL_API_URL,
        params=params,
        timeout=DEFAULT_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError(
            "Government API returned an invalid response."
        )

    records = data.get("records")

    if not isinstance(records, list) or not records:
        raise ValueError(
            "Government API returned no valid records."
        )

    # Apply local verification as an additional safeguard.
    records = _filter_records_by_state(records, state)

    if not records:
        raise ValueError(
            f"Government API returned no records for {state}."
        )

    return {
        "success": True,
        "total_records": _safe_total(
            data.get("total"),
            len(records)
        ),
        "count": len(records),
        "records": records
    }


# =====================================================
# SECONDARY SOURCE: INDIA API
# =====================================================

def fetch_secondary_mandi_prices(
    limit=1000,
    state=None
):
    """
    Retrieve real AGMARKNET records through the
    secondary India API.

    No API key is currently required.
    """

    limit = _validate_limit(limit)

    params = {
        "limit": limit
    }

    if state:
        params["state"] = state

    response = requests.get(
        SECONDARY_API_URL,
        params=params,
        timeout=SECONDARY_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError(
            "Secondary API returned an invalid response."
        )

    records = data.get("data")

    metadata = data.get("meta", {})

    if not isinstance(records, list) or not records:
        raise ValueError(
            "Secondary provider returned no valid records."
        )

    if not isinstance(metadata, dict):
        metadata = {}

    # Verify selected state locally.
    records = _filter_records_by_state(records, state)

    if not records:
        raise ValueError(
            f"Secondary API returned no records for {state}."
        )

    return {
        "success": True,
        "total_records": _safe_total(
            metadata.get("total"),
            len(records)
        ),
        "count": len(records),
        "records": records,
        "provider_metadata": metadata
    }


# =====================================================
# HYBRID DATA RELIABILITY SYSTEM
# =====================================================

def fetch_mandi_prices(
    limit=1000,
    offset=0,
    state=None
):
    """
    Three-layer mandi data retrieval system.

    Layer 1: Official Government of India API
    Layer 2: Secondary India AGMARKNET API
    Layer 3: State-specific local JSON cache

    Each state maintains an independent cache.
    """

    limit = _validate_limit(limit)

    cache_name = _cache_key(state)

    return fetch_with_fallback(

        # PRIMARY PROVIDER
        primary_fetcher=lambda: fetch_official_mandi_prices(
            limit=limit,
            offset=offset,
            state=state
        ),

        # SECONDARY PROVIDER
        secondary_fetcher=lambda: fetch_secondary_mandi_prices(
            limit=limit,
            state=state
        ),

        # STATE-SPECIFIC CACHE
        cache_name=cache_name,

        primary_name=(
            "AGMARKNET - Government of India"
        ),

        secondary_name=(
            "India API - AGMARKNET Mirror"
        ),

        max_age_hours=24
    )
