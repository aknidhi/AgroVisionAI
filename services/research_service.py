"""
Live agricultural research search powered by the OpenAlex scholarly works API.

OpenAlex is a public scholarly metadata API. Search results are live records,
not locally generated sample papers.
"""
from __future__ import annotations

from typing import Any

import requests

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
REQUEST_TIMEOUT = 25

SELECT_FIELDS = ",".join([
    "id",
    "doi",
    "title",
    "publication_year",
    "publication_date",
    "type",
    "authorships",
    "primary_location",
    "open_access",
    "cited_by_count",
    "abstract_inverted_index",
])


class ResearchAPIError(RuntimeError):
    """Raised when the scholarly research provider cannot be reached."""


def _decode_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Convert OpenAlex's inverted abstract index into readable text."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""

    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                words[position] = word

    return " ".join(words[index] for index in sorted(words))


def _author_names(authorships: list[dict[str, Any]] | None) -> list[str]:
    names = []
    for authorship in authorships or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(str(name))
    return names


def _normalise_work(work: dict[str, Any]) -> dict[str, Any]:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    open_access = work.get("open_access") or {}

    doi = work.get("doi") or ""
    landing_page = location.get("landing_page_url") or ""
    url = doi or landing_page or work.get("id") or ""

    return {
        "id": work.get("id", ""),
        "title": work.get("title") or "Untitled research work",
        "year": work.get("publication_year"),
        "date": work.get("publication_date") or "",
        "authors": _author_names(work.get("authorships")),
        "journal": source.get("display_name") or "Publication source not listed",
        "doi": doi,
        "url": url,
        "is_open_access": bool(open_access.get("is_oa")),
        "oa_status": open_access.get("oa_status") or "unknown",
        "citations": int(work.get("cited_by_count") or 0),
        "abstract": _decode_abstract(work.get("abstract_inverted_index")),
        "type": work.get("type") or "work",
    }


def search_agricultural_research(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    sort_by: str = "relevance",
    per_page: int = 20,
) -> dict[str, Any]:
    """
    Search live scholarly works. Returns normalized records and result metadata.
    """
    query = (query or "").strip()
    if len(query) < 2:
        raise ValueError("Enter at least 2 characters to search.")

    per_page = max(1, min(int(per_page), 50))
    filters = ["type:article"]

    if year_from is not None:
        filters.append(f"from_publication_date:{int(year_from)}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{int(year_to)}-12-31")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("The starting year cannot be later than the ending year.")
    if open_access_only:
        filters.append("open_access.is_oa:true")

    params: dict[str, Any] = {
        "search": query,
        "filter": ",".join(filters),
        "per_page": per_page,
        "page": 1,
        "select": SELECT_FIELDS,
    }
    if sort_by == "Most cited":
        params["sort"] = "cited_by_count:desc"
    elif sort_by == "Newest":
        params["sort"] = "publication_date:desc"

    try:
        response = requests.get(
            OPENALEX_WORKS_URL,
            params=params,
            headers={"User-Agent": "AgroVisionAI/1.0 (agricultural research discovery)"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ResearchAPIError(
            "The live research provider could not be reached. "
            "Please check your internet connection and try again."
        ) from exc
    except ValueError as exc:
        raise ResearchAPIError(
            "The research provider returned an unreadable response."
        ) from exc

    results = payload.get("results")
    if not isinstance(results, list):
        raise ResearchAPIError("The research provider returned an unexpected response.")

    return {
        "total_count": int((payload.get("meta") or {}).get("count") or 0),
        "results": [_normalise_work(item) for item in results],
        "provider": "OpenAlex",
        "query": query,
    }
