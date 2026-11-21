"""Data Sources transparency page for AgroVision AI.

Shows the providers and local reference data actually used by this project.
Live connection checks run only when the user requests them.
"""
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.ui import render_page_header, render_section_header
from services.mandi_service import fetch_mandi_prices
from services.weather_service import get_coordinates, get_weather
from services.research_service import search_agricultural_research, ResearchAPIError
from services.kindwise_service import get_provider_status
from services.crop_service import load_crop_requirements


def _status_icon(ok: bool) -> str:
    return "🟢" if ok else "🔴"


def _show_source_card(title, provider, role, data, endpoint, note):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(f"Provider: {provider} · Role: {role}")
        st.write(data)
        st.markdown(f"[Provider endpoint / documentation]({endpoint})")
        st.caption(note)


def data_sources_page():
    render_page_header(
        "Data Sources & Transparency",
        "Explore the real providers, reference datasets and fallback paths behind AgroVision AI.",
        "DATA TRANSPARENCY",
        "🌐",
    )

    st.info(
        "This page distinguishes live API checks from API-key configuration. "
        "A configured key does not by itself prove that the provider is reachable."
    )

    render_section_header(
        "Agricultural market data",
        "Market prices use a primary government source, a secondary provider and a local cache fallback.",
    )
    col1, col2 = st.columns(2)
    with col1:
        _show_source_card(
            "AGMARKNET · Government of India",
            "data.gov.in",
            "Primary",
            "Market-wise commodity prices, arrivals, mandi, district and state records.",
            "https://api.data.gov.in/",
            "Requires DATA_GOV_API_KEY. The service records provider name, retrieval time and freshness status.",
        )
    with col2:
        _show_source_card(
            "AGMARKNET mirror",
            "India API",
            "Secondary fallback",
            "Secondary access path used if the official data.gov.in request fails.",
            "https://api.dharun.dev/v1/mandi",
            "The existing mandi service uses this provider before falling back to its local JSON cache.",
        )

    render_section_header(
        "Weather data",
        "Location lookup and forecast information are retrieved from Open-Meteo.",
    )
    _show_source_card(
        "Open-Meteo",
        "Open-Meteo Geocoding API + Forecast API",
        "Live weather",
        "City geocoding, current weather, hourly weather variables and a 7-day forecast.",
        "https://open-meteo.com/",
        "No API key is required by the current weather service. Weather checks use the selected city.",
    )

    render_section_header(
        "Research discovery",
        "Scholarly records are retrieved live from OpenAlex.",
    )
    _show_source_card(
        "OpenAlex Works API",
        "OpenAlex",
        "Live research metadata",
        "Research titles, authors, publication dates, journals, open-access status, citation counts and abstracts when available.",
        "https://docs.openalex.org/",
        "Search results and result counts come from the live scholarly works API.",
    )

    render_section_header(
        "Plant, crop and insect analysis",
        "Image analysis providers are configured in Crop Health Lab. This page checks key presence only and does not spend identification credits.",
    )
    key_status = get_provider_status()
    providers = [
        ("Kindwise Plant.id", "Primary plant identification", "https://plant.id/"),
        ("Kindwise Insect.id", "Insect identification", "https://insect.id/"),
        ("Kindwise Crop.health", "Crop disease and health analysis", "https://crop.health/"),
        ("Pl@ntNet", "Plant identification fallback; disease feature only where supported", "https://my.plantnet.org/"),
    ]
    provider_cols = st.columns(2)
    for index, (name, role, url) in enumerate(providers):
        with provider_cols[index % 2]:
            with st.container(border=True):
                configured = bool(key_status.get(name))
                st.markdown(f"**{_status_icon(configured)} {name}**")
                st.caption(role)
                st.write("API key configured" if configured else "API key missing")
                st.markdown(f"[Provider website]({url})")
    st.caption(
        "Kindwise is called as the primary provider. Pl@ntNet is used only as a fallback "
        "for supported plant identification and limited disease coverage. Insect identification "
        "currently has no automatic backup in this application."
    )

    render_section_header(
        "Local crop reference data",
        "Crop soil pH guidance is loaded from a local CSV reference file.",
    )
    try:
        crop_df = load_crop_requirements()
        st.success(
            f"Local crop reference file loaded: {len(crop_df)} valid crop records."
        )
        st.dataframe(
            crop_df[["crop", "min_ph", "max_ph", "source"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "This is a local reference dataset, not a live sensor feed or a crop-yield prediction."
        )
    except Exception as exc:
        st.error(f"Local crop reference data could not be loaded: {exc}")

    render_section_header(
        "Live connection check",
        "Run checks on demand. This does not submit images to paid identification APIs.",
    )
    check_city = st.text_input(
        "City for weather check",
        value=st.session_state.get("data_sources_check_city", "Panipat"),
        key="data_sources_city_input",
    )

    if st.button("Run live connection checks", type="primary", use_container_width=True):
        checks = {}
        checked_at = datetime.now().astimezone().strftime("%d %b %Y, %I:%M:%S %p %Z")

        progress = st.status("Starting live connection checks...", expanded=True)
        progress.write("1/3 — Checking mandi market data...")

        # Market: existing primary -> secondary -> cache pipeline.
        try:
            with st.spinner("Contacting the mandi data service..."):
                market = fetch_mandi_prices(limit=20, state=None)
            if market.get("success"):
                checks["Market data"] = {
                    "ok": True,
                    "detail": (
                        f"{market.get('source', 'Provider not reported')} · "
                        f"{len(market.get('records', []))} records · "
                        f"status: {market.get('status', 'unknown')} · "
                        f"retrieved: {market.get('fetched_at') or 'cache timestamp unavailable'}"
                    ),
                    "warning": market.get("warning"),
                    "errors": market.get("errors", []),
                }
            else:
                checks["Market data"] = {
                    "ok": False,
                    "detail": market.get("warning", "No market data returned."),
                    "warning": None,
                    "errors": market.get("errors", []),
                }
        except Exception as exc:
            checks["Market data"] = {"ok": False, "detail": str(exc)}
        progress.write(
            ("🟢" if checks["Market data"]["ok"] else "🔴")
            + " Market check finished."
        )

        progress.write("2/3 — Checking weather service...")
        try:
            with st.spinner(f"Checking Open-Meteo for {check_city.strip() or 'Panipat'}..."):
                location = get_coordinates(check_city.strip() or "Panipat")
                weather = get_weather(location["latitude"], location["longitude"])
            current = weather.get("current", {})
            checks["Weather data"] = {
                "ok": bool(current),
                "detail": (
                    f"{location.get('name')}, {location.get('state')} · "
                    f"{current.get('temperature_2m', '—')} °C · "
                    f"{len(weather.get('daily', {}).get('time', []))}-day forecast returned."
                ),
            }
        except Exception as exc:
            checks["Weather data"] = {"ok": False, "detail": str(exc)}
        progress.write(
            ("🟢" if checks["Weather data"]["ok"] else "🔴")
            + " Weather check finished."
        )

        progress.write("3/3 — Checking OpenAlex research service...")
        try:
            with st.spinner("Sending a small research metadata query to OpenAlex..."):
                research = search_agricultural_research(
                    query="agriculture",
                    per_page=1,
                    sort_by="relevance",
                )
            checks["Research data"] = {
                "ok": True,
                "detail": (
                    f"OpenAlex responded · {research.get('total_count', 0):,} "
                    "matching works for the query 'agriculture'."
                ),
            }
        except Exception as exc:
            checks["Research data"] = {"ok": False, "detail": str(exc)}
        progress.write(
            ("🟢" if checks["Research data"]["ok"] else "🔴")
            + " Research check finished."
        )

        st.session_state["data_sources_last_check"] = {
            "checked_at": checked_at,
            "checks": checks,
        }
        st.session_state["data_sources_check_city"] = check_city.strip() or "Panipat"
        progress.update(label="Connection checks completed.", state="complete", expanded=False)
        st.success("Live connection checks completed. Results are shown below.")

    previous = st.session_state.get("data_sources_last_check")
    if not previous:
        st.caption("No live connection check has been run in this session yet. Click the button above to start.")
    if previous:
        st.caption(f"Last check: {previous['checked_at']}")
        for name, result in previous["checks"].items():
            with st.container(border=True):
                st.markdown(
                    f"**{_status_icon(result.get('ok', False))} {name}**"
                )
                st.write(result.get("detail", "No details returned."))
                if result.get("warning"):
                    st.warning(result["warning"])
                for error in result.get("errors", []) or []:
                    if isinstance(error, dict):
                        st.caption(
                            f"{error.get('source', 'Provider')}: {error.get('error', '')}"
                        )
                    else:
                        st.caption(str(error))

    st.divider()
    st.caption(
        "Connection checks are point-in-time tests. A successful check does not guarantee "
        "continuous availability. Market data may be served from the local cache if both "
        "live providers fail."
    )
