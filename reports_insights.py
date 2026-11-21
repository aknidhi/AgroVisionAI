"""AgroVision AI Reports & Insights page module.

Drop this file in the project root. It uses the existing services package.
"""

import streamlit as st

from core.ui import render_page_header

def reports():

    import pandas as pd
    import plotly.express as px
    from datetime import datetime
    from services.mandi_service import fetch_mandi_prices
    from services.weather_service import get_coordinates, get_weather
    from services.report_service import build_agrovision_pdf

    render_page_header(
        "Reports & Insights",
        "Build downloadable agricultural reports from live market and weather data, alongside your saved farm estimates.",
        "AGRICULTURAL REPORTING CENTRE",
        "📑"
    )

    st.caption(
        "Reports use the same AGMARKNET mandi service and Open-Meteo weather service "
        "as the existing intelligence pages. Farm financial figures are included only "
        "when you have completed a simulation and are based on your entered assumptions."
    )

    st.markdown("### Configure your report")
    with st.form("agrovision_report_form"):
        col1, col2 = st.columns(2)
        with col1:
            report_state = st.text_input(
                "Market state / region", value="Haryana",
                help="State name used to retrieve mandi records."
            )
            report_city = st.text_input(
                "Weather location", value="Panipat",
                help="City or district searched through Open-Meteo geocoding."
            )
        with col2:
            report_commodity = st.text_input(
                "Commodity filter (optional)", value="",
                placeholder="Example: Wheat"
            )
            include_farm = st.checkbox(
                "Include my latest Farm Decision Simulator results",
                value=True
            )
        generate_report = st.form_submit_button(
            "Generate Agricultural Report", use_container_width=True,
            type="primary"
        )

    if generate_report:
        report_payload = {
            "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "state": report_state.strip(),
            "city": report_city.strip(),
            "commodity_filter": report_commodity.strip(),
            "market": None,
            "weather": None,
            "farm": st.session_state.get("farm_simulation_result") if include_farm else None,
            "errors": []
        }

        if report_state.strip():
            try:
                with st.spinner("Retrieving mandi records..."):
                    market_result = fetch_mandi_prices(limit=1000, state=report_state.strip())
                if market_result.get("success") and market_result.get("records"):
                    market_df = pd.DataFrame(market_result["records"])
                    for field in ["min_price", "max_price", "modal_price"]:
                        if field in market_df.columns:
                            market_df[field] = pd.to_numeric(market_df[field], errors="coerce")
                    if report_commodity.strip() and "commodity" in market_df.columns:
                        mask = market_df["commodity"].astype(str).str.contains(
                            report_commodity.strip(), case=False, na=False
                        )
                        market_df = market_df[mask]
                    report_payload["market"] = {
                        "status": market_result.get("status", "unknown"),
                        "source": market_result.get("source", "Unknown provider"),
                        "fetched_at": market_result.get("fetched_at"),
                        "warning": market_result.get("warning"),
                        "records": market_df.replace({float("nan"): None}).to_dict("records")
                    }
                else:
                    report_payload["errors"].append(
                        "Mandi data: " + str(market_result.get("warning") or "No market records returned.")
                    )
            except Exception as error:
                report_payload["errors"].append(f"Mandi data: {error}")
        else:
            report_payload["errors"].append("Market state was not provided; mandi data was not requested.")

        if report_city.strip():
            try:
                with st.spinner("Retrieving weather observations and forecast..."):
                    coordinates = get_coordinates(report_city.strip())
                    weather_data = get_weather(
                        coordinates["latitude"], coordinates["longitude"]
                    )
                report_payload["weather"] = {
                    "location": coordinates,
                    "current": weather_data.get("current", {}),
                    "daily": weather_data.get("daily", {}),
                    "timezone": weather_data.get("timezone", coordinates.get("timezone", "local"))
                }
            except Exception as error:
                report_payload["errors"].append(f"Weather data: {error}")
        else:
            report_payload["errors"].append("Weather location was not provided; weather data was not requested.")

        st.session_state["agrovision_generated_report"] = report_payload

    payload = st.session_state.get("agrovision_generated_report")
    if not payload:
        st.info("Choose a region and location, then generate your first report. No sample or simulated live data is shown here.")
        return

    st.divider()
    st.markdown("### Report overview")
    st.caption(f"Generated: {payload.get('generated_at')} · Market region: {payload.get('state') or 'Not selected'} · Weather location: {payload.get('city') or 'Not selected'}")

    market = payload.get("market")
    weather = payload.get("weather")
    farm = payload.get("farm")
    market_records = market.get("records", []) if market else []
    market_df = pd.DataFrame(market_records)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Mandi records", f"{len(market_records):,}" if market else "Unavailable")
    metric_cols[1].metric("Commodities", f"{market_df['commodity'].nunique():,}" if market and not market_df.empty and "commodity" in market_df else "—")
    if weather:
        current = weather.get("current", {})
        metric_cols[2].metric("Current temperature", f"{current.get('temperature_2m', '—')} °C")
        daily_rain = weather.get("daily", {}).get("precipitation_sum", [])
        rain_total = sum(float(v) for v in daily_rain if v is not None)
        metric_cols[3].metric("7-day forecast rain", f"{rain_total:.1f} mm")
    else:
        metric_cols[2].metric("Current temperature", "Unavailable")
        metric_cols[3].metric("7-day forecast rain", "Unavailable")

    if market:
        st.markdown("#### Market intelligence")
        st.write(f"**Provider:** {market.get('source')} · **Data status:** {market.get('status')} · **Retrieved:** {market.get('fetched_at') or 'Not supplied'}")
        if market.get("warning"):
            st.warning(market["warning"])
        if not market_df.empty and "modal_price" in market_df:
            market_df["modal_price"] = pd.to_numeric(market_df["modal_price"], errors="coerce")
            valid_prices = market_df.dropna(subset=["modal_price"])
            if not valid_prices.empty:
                avg_price = valid_prices["modal_price"].mean()
                low_price = valid_prices["modal_price"].min()
                high_price = valid_prices["modal_price"].max()
                a, b, c = st.columns(3)
                a.metric("Average modal price", f"₹{avg_price:,.2f}/quintal")
                b.metric("Lowest modal price", f"₹{low_price:,.2f}/quintal")
                c.metric("Highest modal price", f"₹{high_price:,.2f}/quintal")
                if "commodity" in valid_prices and "market" in valid_prices:
                    chart_df = (valid_prices.groupby(["commodity", "market"], as_index=False)
                                .agg(Modal_Price=("modal_price", "mean"))
                                .sort_values("Modal_Price", ascending=False).head(15))
                    fig = px.bar(chart_df, x="market", y="Modal_Price", color="commodity",
                                 title="Reported modal prices by mandi", barmode="group",
                                 labels={"market": "Mandi", "Modal_Price": "Modal price (₹/quintal)"})
                    fig.update_layout(height=420, xaxis_tickangle=-30)
                    st.plotly_chart(fig, use_container_width=True)
                display_cols = [c for c in ["date", "state", "district", "market", "commodity", "variety", "min_price", "max_price", "modal_price"] if c in market_df.columns]
                st.dataframe(market_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.warning("Mandi records were returned, but no usable modal-price values were present.")
        else:
            st.warning("No mandi records matched this region and commodity filter.")
    else:
        st.warning("Market data could not be retrieved. This report will not invent market figures.")

    st.divider()
    st.markdown("#### Weather intelligence")
    if weather:
        loc = weather.get("location", {})
        current = weather.get("current", {})
        daily = weather.get("daily", {})
        st.write(f"**Location:** {loc.get('name')}, {loc.get('state')}, {loc.get('country')} · **Coordinates:** {loc.get('latitude')}, {loc.get('longitude')}")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Temperature", f"{current.get('temperature_2m', '—')} °C")
        w2.metric("Humidity", f"{current.get('relative_humidity_2m', '—')}%")
        w3.metric("Precipitation now", f"{current.get('precipitation', '—')} mm")
        w4.metric("Wind speed", f"{current.get('wind_speed_10m', '—')} km/h")
        if daily.get("time"):
            weather_df = pd.DataFrame({
                "Date": daily.get("time", []),
                "Maximum temperature (°C)": daily.get("temperature_2m_max", []),
                "Minimum temperature (°C)": daily.get("temperature_2m_min", []),
                "Forecast rainfall (mm)": daily.get("precipitation_sum", []),
                "Rain probability (%)": daily.get("precipitation_probability_max", []),
                "Maximum wind speed (km/h)": daily.get("wind_speed_10m_max", [])
            })
            st.dataframe(weather_df, use_container_width=True, hide_index=True)
            weather_chart = px.line(weather_df, x="Date", y=["Maximum temperature (°C)", "Minimum temperature (°C)"],
                                    title="7-day temperature forecast", markers=True)
            weather_chart.update_layout(height=350)
            st.plotly_chart(weather_chart, use_container_width=True)
    else:
        st.warning("Weather data could not be retrieved. This report will not invent weather figures.")

    st.divider()
    st.markdown("#### Farm financial performance")
    if farm:
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Crop", farm.get("crop", "—"))
        f2.metric("Estimated production", f"{farm.get('total_production_quintals', 0):,.2f} quintals")
        f3.metric("Estimated investment", f"₹{farm.get('total_cultivation_cost', 0):,.2f}")
        f4.metric("Estimated profit / loss", f"₹{farm.get('net_profit', 0):,.2f}")
        st.caption("These figures are calculated from the inputs entered in Farm Decision Simulator; they are estimates, not observed farm outcomes.")
        cost_breakdown = farm.get("cost_breakdown", {})
        if cost_breakdown:
            cost_df = pd.DataFrame([{"Expense": key.replace("_", " ").title(), "Cost (₹)": value} for key, value in cost_breakdown.items()])
            cost_fig = px.pie(cost_df, names="Expense", values="Cost (₹)", hole=0.5, title="Farm cost distribution (user-entered assumptions)")
            st.plotly_chart(cost_fig, use_container_width=True)
    else:
        st.info("No saved farm simulation was included. Open Farm Decision Simulator, calculate a scenario, then generate the report again.")

    if payload.get("errors"):
        with st.expander("Data retrieval notes"):
            for message in payload["errors"]:
                st.write(f"- {message}")

    st.divider()
    st.markdown("### Export report")
    try:
        pdf_bytes = build_agrovision_pdf(payload)
        st.download_button(
            "Download Agricultural Report (PDF)",
            data=pdf_bytes,
            file_name=f"agrovision_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    except Exception as error:
        st.error(f"PDF report could not be prepared: {error}")
        st.caption("Install the project requirements, including reportlab, and try again.")

    st.caption("AgroVision AI · Market prices are source-reported mandi records; weather is a model forecast; farm financial results are user-input estimates.")

