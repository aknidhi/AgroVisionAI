"""Live dashboard page for AgroVision AI.

This page reads from the existing project services. It does not create sample
market, weather, research, farm simulation or crop diagnosis records.
"""
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from core.ui import render_page_header, render_section_header
from services.mandi_service import fetch_mandi_prices
from services.weather_service import (
    get_coordinates,
    get_weather,
    get_weather_description,
)
from services.research_service import (
    search_agricultural_research,
    ResearchAPIError,
)


@st.cache_data(ttl=900, show_spinner=False)
def _load_market_data():
    return fetch_mandi_prices(limit=1000, state=None)


@st.cache_data(ttl=900, show_spinner=False)
def _load_weather(city: str):
    location = get_coordinates(city)
    weather = get_weather(location["latitude"], location["longitude"])
    return location, weather


@st.cache_data(ttl=3600, show_spinner=False)
def _load_research_count():
    # A one-record live query is sufficient to retrieve OpenAlex's total count.
    return search_agricultural_research(
        query="agriculture",
        per_page=1,
        sort_by="relevance",
    )


def _money(value: Any) -> str:
    try:
        return f"₹{float(str(value).replace(',', '').strip()):,.0f}"
    except (TypeError, ValueError):
        return "Not available"


def _first_value(record: dict, *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _status_label(result: dict | None) -> str:
    if not result:
        return "Unavailable"
    status = result.get("status", "fresh")
    if status == "fresh":
        return "Live"
    if status == "cached":
        return "Cached"
    if status == "stale" or result.get("is_stale"):
        return "Stale cache"
    return str(status).replace("_", " ").title()


def dashboard():
    render_page_header(
        "Agricultural Overview",
        "A live snapshot of agricultural markets, local weather and research activity.",
        "COMMAND CENTER",
        "📊",
    )

    st.caption(
        "Dashboard indicators are retrieved from the platform's connected data services. "
        "Values are not generated or simulated."
    )

    # -------------------- LIVE MARKET DATA --------------------
    market_result = None
    market_error = None
    with st.spinner("Loading agricultural market data..."):
        try:
            market_result = _load_market_data()
            if not market_result.get("success"):
                market_error = market_result.get("warning") or "Market data unavailable."
        except Exception as exc:
            market_error = str(exc)

    market_records = (
        market_result.get("records", [])
        if market_result and market_result.get("success")
        else []
    )
    market_df = pd.DataFrame(market_records) if market_records else pd.DataFrame()

    commodity_count = (
        market_df["commodity"].dropna().nunique()
        if "commodity" in market_df.columns else 0
    )
    mandi_count = (
        market_df["market"].dropna().nunique()
        if "market" in market_df.columns else 0
    )
    market_status = _status_label(market_result)

    # -------------------- LIVE WEATHER --------------------
    weather_location = None
    weather_data = None
    weather_error = None
    weather_city = st.session_state.get("dashboard_weather_city", "Panipat")

    weather_col, weather_action = st.columns([4, 1])
    with weather_col:
        selected_city = st.text_input(
            "Weather location",
            value=weather_city,
            placeholder="Enter an Indian city or district",
            key="dashboard_weather_input",
        )
    with weather_action:
        st.write("")
        st.write("")
        refresh_weather = st.button("Update", use_container_width=True)

    if refresh_weather and selected_city.strip():
        st.session_state["dashboard_weather_city"] = selected_city.strip()
        weather_city = selected_city.strip()
        _load_weather.clear()

    try:
        with st.spinner(f"Loading live weather for {weather_city}..."):
            weather_location, weather_data = _load_weather(weather_city)
    except Exception as exc:
        weather_error = str(exc)

    # -------------------- LIVE RESEARCH METADATA --------------------
    research_result = None
    research_error = None
    try:
        with st.spinner("Checking scholarly research index..."):
            research_result = _load_research_count()
    except (ResearchAPIError, ValueError, Exception) as exc:
        research_error = str(exc)

    # -------------------- KPI ROW --------------------
    render_section_header(
        "Live Agricultural Indicators",
        "Latest available figures from the connected services.",
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mandi records loaded", f"{len(market_records):,}" if market_records else "—")
    k2.metric("Commodities represented", f"{commodity_count:,}" if commodity_count else "—")
    k3.metric("Markets represented", f"{mandi_count:,}" if mandi_count else "—")
    if research_result:
        research_total = research_result.get("total_count")
        k4.metric(
            "Agriculture research works",
            f"{research_total:,}" if research_total is not None else "—",
        )
    else:
        k4.metric("Agriculture research works", "—")

    # -------------------- WEATHER PANEL --------------------
    render_section_header(
        "Local Weather",
        "Current conditions and a short forecast from Open-Meteo.",
    )
    if weather_data and weather_location:
        current = weather_data.get("current", {})
        code = current.get("weather_code")
        description = get_weather_description(code) if code is not None else "Condition unavailable"
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Location", weather_location.get("name", weather_city))
        temp = current.get("temperature_2m")
        w2.metric("Temperature", f"{temp} °C" if temp is not None else "—")
        humidity = current.get("relative_humidity_2m")
        w3.metric("Humidity", f"{humidity}%" if humidity is not None else "—")
        wind = current.get("wind_speed_10m")
        w4.metric("Wind speed", f"{wind} km/h" if wind is not None else "—")
        st.write(f"**Current condition:** {description}")
        daily = weather_data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_probability_max", [])
        if dates:
            forecast_rows = []
            for i, day in enumerate(dates[:5]):
                forecast_rows.append({
                    "Date": day,
                    "Max °C": highs[i] if i < len(highs) else None,
                    "Min °C": lows[i] if i < len(lows) else None,
                    "Rain chance %": rain[i] if i < len(rain) else None,
                })
            st.dataframe(
                pd.DataFrame(forecast_rows),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.warning(f"Weather data unavailable for {weather_city}: {weather_error}")

    # -------------------- MARKET SNAPSHOT --------------------
    render_section_header(
        "Market Snapshot",
        "A sample of the latest records returned by the mandi data service.",
    )
    if market_records:
        display_rows = []
        for record in market_records[:8]:
            display_rows.append({
                "State": _first_value(record, "state"),
                "District": _first_value(record, "district"),
                "Market": _first_value(record, "market", "market_name"),
                "Commodity": _first_value(record, "commodity"),
                "Variety": _first_value(record, "variety"),
                "Modal price": _money(_first_value(
                    record, "modal_price", "modal price", "modal"
                )),
                "Arrival date": _first_value(
                    record, "arrival_date", "arrival date", "date"
                ),
            })
        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning(market_error or "No market records are currently available.")

    # -------------------- PLATFORM ACTIVITY & SOURCE STATUS --------------------
    render_section_header(
        "Platform Status",
        "Connection and activity visibility. No activity is shown unless it is actually recorded.",
    )
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.markdown("**Connected data services**")
        st.write(f"{'🟢' if market_records else '🔴'} AGMARKNET mandi data — {market_status}")
        st.write(
            f"{'🟢' if weather_data else '🔴'} Open-Meteo weather — "
            f"{'Live' if weather_data else 'Unavailable'}"
        )
        st.write(
            f"{'🟢' if research_result else '🔴'} OpenAlex research — "
            f"{'Live' if research_result else 'Unavailable'}"
        )
        st.caption("Crop Health Lab API keys are configured on its own page; this dashboard does not spend identification credits.")
    with status_col2:
        st.markdown("**Personal activity**")
        st.info(
            "No persistent crop-diagnosis or farm-simulation history is currently stored "
            "by the application. Those totals are therefore not displayed here."
        )
        st.caption(
            "Farm Simulator calculations are user-input estimates. They are not presented "
            "as observed farm outcomes."
        )

    # -------------------- FOOTNOTES / DATA FRESHNESS --------------------
    st.divider()
    fetched_at = market_result.get("fetched_at") if market_result else None
    if fetched_at:
        st.caption(
            f"Mandi data retrieved: {fetched_at} · Source: "
            f"{market_result.get('source', 'Not reported')} · Status: {market_status}"
        )
        if market_result.get("warning"):
            st.warning(market_result["warning"])
    if weather_data:
        st.caption(
            f"Weather provider: Open-Meteo · Forecast timezone: "
            f"{weather_data.get('timezone', 'provider default')}"
        )
    if research_result:
        st.caption("Research provider: OpenAlex · Count is the provider's current matching works total.")

    if st.button("Refresh dashboard data", type="primary"):
        _load_market_data.clear()
        _load_weather.clear()
        _load_research_count.clear()
        st.rerun()
