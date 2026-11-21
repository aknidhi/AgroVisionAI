def market_intelligence():
    import pandas as pd
    import plotly.express as px
    from services.mandi_service import fetch_mandi_prices

    render_page_header(
        "Market Intelligence",
        "Explore real agricultural commodity prices, mandi trends and market comparisons.",
        "LIVE MARKET ANALYTICS", "📈"
    )

    @st.cache_data(ttl=900, show_spinner=False)
    def load_india_data():
        return fetch_mandi_prices(limit=1000, state=None)

    st.markdown("### Explore Agricultural Markets")
    with st.spinner("Retrieving agricultural market records across India..."):
        try:
            result = load_india_data()
        except Exception as error:
            st.error(f"Market data retrieval failed: {error}")
            return

    if not result.get("success"):
        st.error("No live or cached mandi data is currently available.")
        st.warning(result.get("warning", "No market records found."))
        with st.expander("Provider diagnostics"):
            for item in result.get("errors", []):
                st.write(f"**{item.get('source', 'Provider')}:** {item.get('error', 'Unknown error')}")
        return

    df = pd.DataFrame(result.get("records", []))
    required = ["date", "state", "district", "market", "commodity",
                "min_price", "max_price", "modal_price"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        st.error(f"Mandi response is missing fields: {missing}")
        return
    if df.empty:
        st.warning("No agricultural market records were returned.")
        return

    for column in ["state", "district", "market", "commodity"]:
        df[column] = df[column].fillna("").astype(str).str.strip()
    for column in ["min_price", "max_price", "modal_price"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df[
        (df["market"] != "") & (df["district"] != "") &
        (df["state"] != "") & (df["commodity"] != "")
    ].copy()
    df = df.dropna(subset=["modal_price"])
    if df.empty:
        st.warning("No valid agricultural market records were returned.")
        return

    df["reporting_district"] = df["district"]

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
    c1.markdown("**Data Status**")
    c1.write(labels.get(status, status))
    c2.markdown("**Data Provider**")
    c2.write(source)
    c3.markdown("**Last Retrieved**")
    c3.write(str(fetched)[:19].replace("T", " ") if fetched else "Not available")

    if result.get("warning"):
        st.warning(result["warning"])
    if result.get("errors"):
        with st.expander("Data provider diagnostics"):
            for item in result["errors"]:
                st.write(f"**{item.get('source', 'Provider')}:** {item.get('error', 'Unknown error')}")

    st.divider()
    st.markdown("### Select Mandi / Market")
    market_search = st.text_input(
        "Search market",
        placeholder="Search by mandi, city, district or state...",
        key="market_search_input"
    )

    all_market_data = (
        df[["market", "district", "state"]]
        .drop_duplicates()
        .sort_values(
            ["market", "district", "state"],
            key=lambda column: column.astype(str).str.casefold()
        )
        .reset_index(drop=True)
    )
    searchable_market_data = all_market_data.copy()
    if market_search.strip():
        search_term = market_search.strip().casefold()
        searchable_market_data = searchable_market_data[
            searchable_market_data.apply(
                lambda row: search_term in " ".join(str(value) for value in row).casefold(),
                axis=1
            )
        ]

    market_options = [
        f"{row['market']} — {row['district']}, {row['state']}"
        for _, row in searchable_market_data.iterrows()
    ]
    market_options = ["All Markets"] + market_options
    selected_market = st.selectbox(
        "Choose a market",
        market_options,
        key="market_location_filter"
    )

    st.markdown("### Select Commodity")
    commodity_search = st.text_input(
        "Search commodity",
        placeholder="Search wheat, rice, mustard, tomato...",
        key="commodity_search_input"
    )
    all_commodities = sorted(df["commodity"].dropna().unique().tolist(), key=str.casefold)
    commodities = all_commodities
    if commodity_search.strip():
        search_term = commodity_search.strip().casefold()
        commodities = [item for item in all_commodities if search_term in item.casefold()]

    commodity_options = ["All Commodities"] + commodities
    selected_commodity = st.selectbox(
        "Choose a commodity",
        commodity_options,
        key="market_commodity_filter"
    )

    filtered = df.copy()
    if selected_market != "All Markets":
        selected_row = searchable_market_data[
            (
                searchable_market_data["market"] + " — " +
                searchable_market_data["district"] + ", " +
                searchable_market_data["state"]
            ) == selected_market
        ]
        if selected_row.empty:
            st.warning("Selected market is not available in the current data.")
            return
        market_row = selected_row.iloc[0]
        filtered = filtered[
            (filtered["market"] == market_row["market"]) &
            (filtered["district"] == market_row["district"]) &
            (filtered["state"] == market_row["state"])
        ].copy()

    if selected_commodity != "All Commodities":
        filtered = filtered[filtered["commodity"] == selected_commodity].copy()
    if filtered.empty:
        st.warning("No records match the selected market and commodity.")
        return

    st.divider()
    st.markdown("### Market Overview")
    a, b, c, d = st.columns(4)
    a.metric("Market Records", f"{len(filtered):,}")
    b.metric("Commodities", f"{filtered['commodity'].nunique():,}")
    c.metric("Markets", f"{filtered['market'].nunique():,}")
    d.metric("Average Modal Price", f"₹{filtered['modal_price'].mean():,.0f}/q")
    st.caption(
        f"Showing {filtered['market'].nunique():,} markets across "
        f"{filtered['state'].nunique():,} states in the filtered results."
    )
    if len(df) >= 1000:
        st.info(
            "The current request is limited to 1,000 records. "
            "Additional markets may be available beyond this result limit."
        )

    st.divider()
    st.markdown("### Commodity Price Analytics")
    left, right = st.columns(2)
    with left:
        summary = (
            filtered.groupby("commodity", as_index=False)
            .agg(Average_Modal_Price=("modal_price", "mean"))
            .sort_values("Average_Modal_Price", ascending=False)
            .head(10)
        )
        fig = px.bar(
            summary, x="commodity", y="Average_Modal_Price",
            title="Top Commodities by Average Modal Price",
            color_discrete_sequence=["#276749"]
        )
        fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        summary = (
            filtered.groupby("market", as_index=False)
            .agg(Average_Modal_Price=("modal_price", "mean"))
            .sort_values("Average_Modal_Price", ascending=False)
            .head(10)
        )
        fig = px.bar(
            summary, x="market", y="Average_Modal_Price",
            title="Market-wise Average Modal Prices",
            color_discrete_sequence=["#39734D"]
        )
        fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Price Range Analysis")
    prices = (
        filtered.dropna(subset=["min_price", "max_price", "modal_price"])
        .groupby("commodity", as_index=False)
        .agg(
            Minimum_Price=("min_price", "mean"),
            Modal_Price=("modal_price", "mean"),
            Maximum_Price=("max_price", "mean")
        )
        .sort_values("Modal_Price", ascending=False)
        .head(10)
    )
    if not prices.empty:
        fig = px.bar(
            prices,
            x="commodity",
            y=["Minimum_Price", "Modal_Price", "Maximum_Price"],
            barmode="group",
            title="Minimum, Modal and Maximum Prices",
            color_discrete_sequence=["#A7C957", "#276749", "#1B4332"]
        )
        fig.update_layout(template="plotly_white", height=430, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Mandi Market Records")
    columns = [
        "date", "state", "reporting_district", "market", "commodity",
        "variety", "grade", "min_price", "max_price", "modal_price"
    ]
    table = filtered[[column for column in columns if column in filtered.columns]].copy()
    if "date" in table:
        table["date"] = table["date"].dt.strftime("%d %b %Y")
    table = table.rename(columns={
        "date": "Date", "state": "State", "reporting_district": "District",
        "market": "Market", "commodity": "Commodity", "variety": "Variety",
        "grade": "Grade", "min_price": "Min Price (₹/q)",
        "max_price": "Max Price (₹/q)", "modal_price": "Modal Price (₹/q)"
    })
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        f"Displaying {len(table):,} actual market records. Prices are ₹ per quintal. "
        "Market locations retain their actual reporting district and state."
    )
    st.success("Market Intelligence is connected to the hybrid agricultural data system.")
