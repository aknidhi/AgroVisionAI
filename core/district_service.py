
import json
import re
from pathlib import Path
from functools import lru_cache
from difflib import get_close_matches
from math import radians, sin, cos, asin, sqrt


# ==========================================
# CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DISTRICT_DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "india_districts.json"
)

MAX_NEARBY_DISTANCE_KM = 300


# ==========================================
# NAME NORMALIZATION
# ==========================================

STATE_ALIASES = {
    "orissa": "odisha",
    "uttaranchal": "uttarakhand",
    "pondicherry": "puducherry",
    "nct of delhi": "delhi",
    "national capital territory of delhi": "delhi",
    "andaman nicobar islands": "andaman and nicobar islands",
}


def _normalize_name(value):
    """Normalize state and district names for comparison."""

    if value is None:
        return ""

    value = str(value).strip().casefold()

    value = re.sub(r"[^a-z0-9]+", " ", value)

    value = re.sub(r"\s+", " ", value).strip()

    return value


def canonical_state_name(value):
    """Return a normalized canonical state name."""

    name = _normalize_name(value)

    return STATE_ALIASES.get(name, name)


def canonical_district_name(value):
    """Return a normalized canonical district name."""

    name = _normalize_name(value)

    # Remove common suffixes.
    name = re.sub(r"\s+district$", "", name)

    return name.strip()


# ==========================================
# LOAD DISTRICT DATABASE
# ==========================================

@lru_cache(maxsize=1)
def load_district_database():
    """
    Load the official district reference JSON.

    The database contains:
        source
        retrieved_at
        district_count
        state_count
        districts
    """

    if not DISTRICT_DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"District database not found: "
            f"{DISTRICT_DATABASE_PATH}"
        )

    try:
        with open(
            DISTRICT_DATABASE_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid district JSON file: {error}"
        )

    if not isinstance(data, dict):
        raise ValueError(
            "District database must contain a JSON object."
        )

    districts = data.get("districts")

    if not isinstance(districts, list) or not districts:
        raise ValueError(
            "District database contains no valid districts."
        )

    valid_districts = []

    for item in districts:

        if not isinstance(item, dict):
            continue

        state = item.get("state")
        district = item.get("district")

        if not state or not district:
            continue

        try:
            latitude = float(item["latitude"])
            longitude = float(item["longitude"])

        except (ValueError, TypeError, KeyError):
            continue

        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            continue

        valid_districts.append({
            "state": str(state).strip(),
            "district": str(district).strip(),
            "latitude": latitude,
            "longitude": longitude
        })

    if not valid_districts:
        raise ValueError(
            "No valid district coordinates found."
        )

    result = dict(data)

    result["districts"] = valid_districts

    result["district_count"] = len(valid_districts)

    result["state_count"] = len({
        canonical_state_name(x["state"])
        for x in valid_districts
    })

    return result


# ==========================================
# GET ALL STATES
# ==========================================

def get_states(master=None):
    """Return all available states and UTs."""

    if master is None:
        master = load_district_database()

    states = {
        item["state"]
        for item in master["districts"]
    }

    return sorted(states, key=str.casefold)


# ==========================================
# GET DISTRICTS OF A STATE
# ==========================================

def get_districts(state, master=None):
    """
    Return every district belonging to a state.

    Does not depend on mandi API records.
    """

    if master is None:
        master = load_district_database()

    target_state = canonical_state_name(state)

    districts = {
        item["district"]
        for item in master["districts"]
        if canonical_state_name(item["state"]) == target_state
    }

    return sorted(districts, key=str.casefold)


# ==========================================
# MATCH API DISTRICT NAMES
# ==========================================

def match_record_district(record_name, state_districts):
    """
    Match a mandi API district name against
    the master district reference database.

    Returns:
        Actual master district name if matched.
        None if no reliable match exists.
    """

    if not record_name:
        return None

    record_key = canonical_district_name(record_name)

    if not record_key:
        return None

    lookup = {
        canonical_district_name(district): district
        for district in state_districts
    }

    # Exact normalized match.
    if record_key in lookup:
        return lookup[record_key]

    # Conservative fuzzy matching.
    matches = get_close_matches(
        record_key,
        list(lookup.keys()),
        n=1,
        cutoff=0.90
    )

    if matches:
        return lookup[matches[0]]

    return None


# ==========================================
# HAVERSINE DISTANCE
# ==========================================

def calculate_distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate approximate geographical distance
    between two coordinates using Haversine formula.
    """

    earth_radius_km = 6371.0

    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    a = min(1.0, max(0.0, a))

    c = 2 * asin(sqrt(a))

    return earth_radius_km * c


# ==========================================
# FIND NEAREST REPORTING DISTRICT
# ==========================================

def find_nearest_reporting_district(
    state,
    district,
    available,
    rows=None,
    max_distance_km=MAX_NEARBY_DISTANCE_KM
):
    """
    Find the nearest district with actual mandi records.

    Rules:
        1. Search only within the same state.
        2. Use district coordinates from master JSON.
        3. Never invent or generate prices.
        4. Only consider districts in available records.
        5. Respect the maximum distance limit.

    Returns:
        {
            "district": "Panipat",
            "distance_km": 45.2
        }

        Returns None if no suitable district exists.
    """

    if rows is None:
        rows = load_district_database()

    if not available:
        return None

    target_state = canonical_state_name(state)

    target_district = canonical_district_name(district)

    available_keys = {
        canonical_district_name(name)
        for name in available
        if name
    }

    # Locate selected district coordinates.
    target = None

    for item in rows["districts"]:

        if (
            canonical_state_name(item["state"]) == target_state
            and canonical_district_name(item["district"])
            == target_district
        ):
            target = item
            break

    if target is None:
        return None

    nearest = None
    minimum_distance = float("inf")

    # Find nearest available reporting district.
    for item in rows["districts"]:

        if canonical_state_name(item["state"]) != target_state:
            continue

        candidate_key = canonical_district_name(
            item["district"]
        )

        if candidate_key == target_district:
            continue

        if candidate_key not in available_keys:
            continue

        distance = calculate_distance_km(
            target["latitude"],
            target["longitude"],
            item["latitude"],
            item["longitude"]
        )

        if distance < minimum_distance:

            minimum_distance = distance

            nearest = {
                "district": item["district"],
                "distance_km": round(distance, 2)
            }

    if nearest is None:
        return None

    if minimum_distance > max_distance_km:
        return None

    return nearest


# ==========================================
# DATABASE INFORMATION
# ==========================================

def get_database_statistics(master=None):
    """Return district database statistics."""

    if master is None:
        master = load_district_database()

    return {
        "total_states": master["state_count"],
        "total_districts": master["district_count"],
        "source": master.get("source"),
        "retrieved_at": master.get("retrieved_at")
    }
