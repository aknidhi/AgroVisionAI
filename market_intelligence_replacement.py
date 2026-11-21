def market_intelligence():
    import pandas as pd
    import plotly.express as px
    from services.mandi_service import fetch_mandi_prices
    from core.district_service import (
        load_district_database, get_states, get_districts,
        canonical_state_name, canonical_district_name,
        find_nearest_reporting_district, match_record_district
    )

    render_page_header(
        "Market Intelligence",
        "Explore real agricultural commodity prices, mandi trends and market comparisons.",
        "LIVE MARKET ANALYTICS", "📈"
    )

    try:
        master = load_district_database()
    except Exception as error:
        st.error(f"District reference data could not be loaded: {error}")
        st.info("Run `python -m scripts.download_district_database` from the project root.")
        return

    st.markdown("### Explore Agricultural Markets")
    states = ["Select a State"] + get_states(master)
    state = st.selectbox("1. Select State", states, key="market_state_filter")
    if state == "Select a State":
        st.info("Select a state to load its current mandi records.")
        return

    @st.cache_data(ttl=900, show_spinner=False)
    def load_state_data(state_name):
        return fetch_mandi_prices(limit=1000, state=state_name)

    with st.spinner(f"Retrieving mandi prices for {state}..."):
        try:
            result = load_state_data(state)
        except Exception as error:
            st.error(f"Market data retrieval failed: {error}")
            return

    if not result.get("success"):
        st.error(f"No live or cached mandi data is currently available for {state}.")
        st.warning(result.get("warning", "No market records found."))
        with st.expander("Provider diagnostics"):
            for item in result.get("errors", []):
                st.write(f"**{item.get('source', 'Provider')}:** {item.get('error', 'Unknown error')}")
        return

    df = pd.DataFrame(result.get("records", []))
    required = ["date", "state", "district", "market", "commodity", "min_price", "max_price", "modal_price"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Mandi response is missing fields: {missing}")
        return

    df = df[df["state"].astype(str).map(canonical_state_name) == canonical_state_name(state)].copy()
    if df.empty:
        st.warning(f"No mandi records were returned for {state}. District options remain complete, but nearby fallback needs actual reporting districts.")
        return

    for col in ["min_price", "max_price", "modal_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["commodity", "modal_price", "district"])
    if df.empty:
        st.warning("No valid commodity price records were returned.")
        return

    state_districts = get_districts(state, master)
    df["reporting_district"] = df["district"].astype(str).apply(
        lambda x: match_record_district(x, state_districts) or x.strip()
    )

    status = result.get("status", "unknown")
    source = result.get("source", "Unknown provider")
    fetched = result.get("fetched_at")
    labels = {
        "fresh": "🟢 Fresh API Data",
        "cached": "🟡 Cached Data",
        "stale": "🟠 Stale Cached Data",
        "unavailable": "🔴 Unavailable"
    }
    if status == "fresh" and "Mirror" in str(source):
        labels["fresh"] = "🟢 Fresh API Data (Fallback)"

    st.markdown("### Data Connection")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Data Status**"); c1.write(labels.get(status, status))
    c2.markdown("**Data Provider**"); c2.write(source)
    c3.markdown("**Last Retrieved**"); c3.write(str(fetched)[:19].replace("T", " ") if fetched else "Not available")
    if result.get("warning"):
        st.warning(result["warning"])
    if result.get("errors"):
        with st.expander("Data provider diagnostics"):
            for item in result["errors"]:
                st.write(f"**{item.get('source', 'Provider')}:** {item.get('error', 'Unknown error')}")

    st.divider()
    district_options = ["All Districts"] + state_districts
    district = st.selectbox("2. Select District", district_options, key="market_district_filter")
    chosen = df.copy()
    fallback = None

    if district != "All Districts":
        chosen = df[df["reporting_district"].astype(str).map(canonical_district_name) == canonical_district_name(district)].copy()
        if chosen.empty:
            available = chosen_names = df["reporting_district"].dropna().astype(str).unique().tolist()
            fallback = find_nearest_reporting_district(
                state, district, available, rows=master, max_distance_km=300
            )
            if not fallback:
                st.warning(
                    f"No direct records for {district}, and no reporting district with coordinates "
                    "was found within 300 km in this state. No substitute prices are shown."
                )
                return
            chosen = df[df["reporting_district"].astype(str).map(canonical_district_name) == canonical_district_name(fallback["district"])].copy()
            st.warning(
                f"No direct mandi records for **{district}**. Showing actual records from "
                f"**{fallback['district']}**, approximately **{fallback['distance_km']} km** away. "
                f"These are nearby-market prices, not prices reported by {district}."
            )
        else:
            st.success(f"Showing mandi records reported directly in {district}.")

    commodities = ["All Commodities"] + sorted(chosen["commodity"].dropna().astype(str).unique(), key=str.casefold)
    commodity = st.selectbox("3. Select Commodity", commodities, key="market_commodity_filter")
    filtered = chosen if commodity == "All Commodities" else chosen[chosen["commodity"].astype(str) == commodity]
    if filtered.empty:
        st.warning("No records match the selected commodity.")
        return

    st.divider()
    st.markdown("### Market Overview")
    a, b, c, d = st.columns(4)
    a.metric("Market Records", f"{len(filtered):,}")
    b.metric("Commodities", f"{filtered['commodity'].nunique():,}")
    c.metric("Reporting Districts", f"{filtered['reporting_district'].nunique():,}")
    d.metric("Average Modal Price", f"₹{filtered['modal_price'].mean():,.0f}/q")
    if fallback:
        st.caption(f"Selected district: {district} | Actual reporting district: {fallback['district']} | Approx. centroid distance: {fallback['distance_km']} km")

    st.divider()
    st.markdown("### Commodity Price Analytics")
    left, right = st.columns(2)
    with left:
        summary = filtered.groupby("commodity", as_index=False).agg(Average_Modal_Price=("modal_price", "mean")).sort_values("Average_Modal_Price", ascending=False).head(10)
        fig = px.bar(summary, x="commodity", y="Average_Modal_Price", title="Top Commodities by Average Modal Price", color_discrete_sequence=["#276749"])
        fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        summary = filtered.groupby("market", as_index=False).agg(Average_Modal_Price=("modal_price", "mean")).sort_values("Average_Modal_Price", ascending=False).head(10)
        fig = px.bar(summary, x="market", y="Average_Modal_Price", title="Market-wise Average Modal Prices", color_discrete_sequence=["#39734D"])
        fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Price Range Analysis")
    prices = filtered.dropna(subset=["min_price", "max_price", "modal_price"]).groupby("commodity", as_index=False).agg(
        Minimum_Price=("min_price", "mean"), Modal_Price=("modal_price", "mean"), Maximum_Price=("max_price", "mean")
    ).sort_values("Modal_Price", ascending=False).head(10)
    if not prices.empty:
        fig = px.bar(prices, x="commodity", y=["Minimum_Price", "Modal_Price", "Maximum_Price"], barmode="group", title="Minimum, Modal and Maximum Prices", color_discrete_sequence=["#A7C957", "#276749", "#1B4332"])
        fig.update_layout(template="plotly_white", height=430, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Mandi Market Records")
    columns = ["date", "state", "reporting_district", "market", "commodity", "variety", "grade", "min_price", "max_price", "modal_price"]
    table = filtered[[c for c in columns if c in filtered.columns]].copy()
    if "date" in table:
        table["date"] = table["date"].dt.strftime("%d %b %Y")
    table = table.rename(columns={
        "date": "Date", "state": "State", "reporting_district": "Actual Reporting District",
        "market": "Market", "commodity": "Commodity", "variety": "Variety", "grade": "Grade",
        "min_price": "Min Price (₹/q)", "max_price": "Max Price (₹/q)", "modal_price": "Modal Price (₹/q)"
    })
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(f"Displaying {len(table):,} actual market records. Prices are ₹ per quintal. Nearby fallback rows retain their actual reporting district.")
    st.success("Market Intelligence is connected to the hybrid agricultural data system.")
