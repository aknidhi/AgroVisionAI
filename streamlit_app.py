import streamlit as st
from crop_health_lab import crop_health_lab
from dashboard import dashboard as live_dashboard
from data_sources_page import data_sources_page
from datetime import date
from services.research_service import (
    search_agricultural_research,
    ResearchAPIError,
)
from core.ui import (
    load_global_styles,
    render_page_header,
    render_section_header
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="AgroVision AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Load the shared AgroVision design system on every page.
load_global_styles()

# --------------------------------------------------
# PAGE 1: HOME
# --------------------------------------------------

def home():

    render_page_header(
        "Agricultural Intelligence, Reimagined.",
        "From agricultural data to smarter farming decisions.",
        "AGRICULTURAL INTELLIGENCE · INDIA",
        "🌱"
    )

    st.write(
        "AgroVision AI is an integrated agricultural "
        "intelligence platform designed to help farmers, "
        "researchers and agricultural planners."
    )

    render_section_header(
        "Explore AgroVision",
        "Discover the intelligence tools available on our platform."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🌾 Crop Intelligence")
        st.write("Explore crop suitability and agricultural planning.")

    with col2:
        st.markdown("### 🌦️ Weather Intelligence")
        st.write("Understand weather conditions and agricultural risks.")

    with col3:
        st.markdown("### 📊 Market Intelligence")
        st.write("Explore commodity prices and market trends.")

    st.divider()

    st.subheader("Our Mission")

    st.info(
        "To make agricultural information more accessible "
        "and transform it into understandable, evidence-based "
        "farming insights."
    )

    st.caption(
        "AgroVision AI | Intelligent Agriculture for a Better Tomorrow"
    )


# --------------------------------------------------
# PAGE 2: DASHBOARD
# --------------------------------------------------

def dashboard():
    live_dashboard()

# --------------------------------------------------
# PAGE 3: CROP INTELLIGENCE
# --------------------------------------------------


def crop_intelligence():

    import pandas as pd
    import plotly.express as px
    import streamlit as st

    from core.district_service import (
        get_states,
        get_districts
    )

    from services.crop_service import (
        analyze_soil_ph,
        recommend_crops
    )

    from services.weather_service import (
        get_coordinates,
        get_weather,
        get_weather_description
    )

    # --------------------------------------------------
    # PAGE HEADER
    # --------------------------------------------------

    render_page_header(
        "Crop Intelligence",
        "Explore crop suitability using soil information "
        "and live weather conditions.",
        "CROP ANALYTICS",
        "🌾"
    )

    st.divider()

    # --------------------------------------------------
    # LOCATION SELECTION
    # --------------------------------------------------

    render_section_header(
        "Agricultural Location",
        "Select your state and district."
    )

    states = get_states()

    if not states:
        st.error("No states are available in the district database.")
        return

    default_state = (
        states.index("Haryana")
        if "Haryana" in states
        else 0
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_state = st.selectbox(
            "Select State / UT",
            states,
            index=default_state,
            key="crop_selected_state"
        )

    districts = get_districts(selected_state)

    with col2:

        if districts:
            selected_district = st.selectbox(
                "Select District",
                districts,
                key=f"crop_district_{selected_state}"
            )
        else:
            selected_district = None
            st.warning(
                "No districts are currently available "
                "for this state."
            )

    st.divider()

    # --------------------------------------------------
    # SOIL INPUTS
    # --------------------------------------------------

    render_section_header(
        "Soil Analysis",
        "Enter your soil pH to evaluate crop compatibility."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        soil_ph = st.slider(
            "Soil pH",
            min_value=0.0,
            max_value=14.0,
            value=6.5,
            step=0.1,
            help="Enter the pH measured from your soil test."
        )

    with col2:
        soil_info = analyze_soil_ph(soil_ph)

        st.metric(
            "Soil Classification",
            soil_info["category"]
        )

    st.info(soil_info["description"])

    st.caption(
        "For reliable agricultural decisions, use laboratory-tested "
        "soil pH values rather than estimates."
    )

    st.divider()

    # --------------------------------------------------
    # ANALYSIS BUTTON
    # --------------------------------------------------

    if st.button(
        "Analyze Crop Suitability",
        type="primary",
        use_container_width=True,
        disabled=not selected_district
    ):

        with st.spinner(
            "Analyzing soil conditions and retrieving live weather..."
        ):

            try:

                # Crop recommendation based on current
                # soil pH reference database.

                result = recommend_crops(
                    ph=soil_ph,
                    top_n=10
                )

                st.session_state["crop_analysis_result"] = result

                st.session_state["crop_analysis_location"] = {
                    "state": selected_state,
                    "district": selected_district
                }

                st.session_state["crop_analysis_ph"] = soil_ph

                # Retrieve live weather independently.

                try:

                    coordinates = get_coordinates(
                        f"{selected_district}, {selected_state}"
                    )

                    weather = get_weather(
                        coordinates["latitude"],
                        coordinates["longitude"]
                    )

                    st.session_state["crop_weather"] = weather
                    st.session_state["crop_coordinates"] = coordinates
                    st.session_state["crop_weather_error"] = None

                except Exception as weather_error:

                    st.session_state["crop_weather"] = None

                    st.session_state["crop_weather_error"] = str(
                        weather_error
                    )

            except Exception as error:

                st.error(
                    f"Crop analysis failed: {error}"
                )

    # --------------------------------------------------
    # DISPLAY ANALYSIS RESULTS
    # --------------------------------------------------

    if "crop_analysis_result" in st.session_state:

        result = st.session_state["crop_analysis_result"]

        location = st.session_state["crop_analysis_location"]

        st.divider()

        render_section_header(
            "Crop Recommendation Results",
            "Crops ranked according to their soil pH compatibility."
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Crops Evaluated",
                result["total_crops_evaluated"]
            )

        with col2:
            st.metric(
                "pH Range Matches",
                len(result["matching_crops"])
            )

        with col3:
            st.metric(
                "Soil pH",
                f"{st.session_state['crop_analysis_ph']:.1f}"
            )

        st.caption(
            f"Location: {location['district']}, "
            f"{location['state']}"
        )

        recommendations = result["recommendations"]

        if recommendations:

            st.subheader("Recommended Crops")

            recommendation_df = pd.DataFrame(
                recommendations
            )

            display_df = recommendation_df[
                [
                    "crop",
                    "min_ph",
                    "max_ph",
                    "ph_match_score",
                    "status"
                ]
            ].rename(
                columns={
                    "crop": "Crop",
                    "min_ph": "Minimum pH",
                    "max_ph": "Maximum pH",
                    "ph_match_score": "pH Match Score",
                    "status": "Compatibility"
                }
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # --------------------------------------------------
            # CROP COMPARISON CHART
            # --------------------------------------------------

            st.subheader("Crop Suitability Comparison")

            chart_df = recommendation_df.sort_values(
                "ph_match_score",
                ascending=True
            )

            fig = px.bar(
                chart_df,
                x="ph_match_score",
                y="crop",
                orientation="h",
                color="ph_match_score",
                color_continuous_scale="Greens",
                labels={
                    "ph_match_score": "pH Match Score",
                    "crop": "Crop"
                },
                title="Soil pH Compatibility"
            )

            fig.update_layout(
                height=450,
                xaxis_range=[0, 105],
                showlegend=False
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # --------------------------------------------------
            # RECOMMENDATION EXPLANATION
            # --------------------------------------------------

            st.subheader("Recommendation Explanation")

            for crop in recommendations:

                with st.expander(
                    crop["crop"]
                    + f" — {crop['ph_match_score']}% pH match"
                ):

                    st.write(
                        f"**Reference pH range:** "
                        f"{crop['min_ph']} – {crop['max_ph']}"
                    )

                    st.write(
                        f"**Your soil pH:** "
                        f"{crop['soil_ph']}"
                    )

                    st.write(
                        f"**Compatibility:** "
                        f"{crop['status']}"
                    )

                    st.caption(
                        f"Reference: {crop['source']}"
                    )

        # --------------------------------------------------
        # LIVE WEATHER CONTEXT
        # --------------------------------------------------

        st.divider()

        render_section_header(
            "Live Weather Context",
            "Current weather conditions for the selected district."
        )

        weather = st.session_state.get(
            "crop_weather"
        )

        if weather:

            coordinates = st.session_state[
                "crop_coordinates"
            ]

            current = weather["current"]

            st.caption(
                f"Weather location: {coordinates['name']}, "
                f"{coordinates['state']}"
            )

            weather_cols = st.columns(4)

            weather_cols[0].metric(
                "Temperature",
                f"{current['temperature_2m']} °C"
            )

            weather_cols[1].metric(
                "Humidity",
                f"{current['relative_humidity_2m']}%"
            )

            weather_cols[2].metric(
                "Wind Speed",
                f"{current['wind_speed_10m']} km/h"
            )

            weather_cols[3].metric(
                "Rainfall",
                f"{current['precipitation']} mm"
            )

            st.info(
                "Current Condition: "
                + get_weather_description(
                    current["weather_code"]
                )
            )

            # Seven-day forecast

            daily = weather["daily"]

            forecast_df = pd.DataFrame({
                "Date": pd.to_datetime(
                    daily["time"]
                ).strftime("%d %b"),

                "Condition": [
                    get_weather_description(code)
                    for code in daily["weather_code"]
                ],

                "Maximum Temperature (°C)": (
                    daily["temperature_2m_max"]
                ),

                "Minimum Temperature (°C)": (
                    daily["temperature_2m_min"]
                ),

                "Rainfall (mm)": (
                    daily["precipitation_sum"]
                ),

                "Rain Probability (%)": (
                    daily["precipitation_probability_max"]
                )
            })

            st.subheader("7-Day Weather Forecast")

            st.dataframe(
                forecast_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            weather_error = st.session_state.get(
                "crop_weather_error"
            )

            st.warning(
                "Weather information is currently unavailable. "
                "Crop pH analysis is still available."
            )

            if weather_error:
                st.caption(weather_error)

        # --------------------------------------------------
        # METHODOLOGY
        # --------------------------------------------------

        st.divider()

        st.caption(
            "Current recommendation methodology: "
            "soil pH reference-range matching. "
            "Weather is displayed as separate live context. "
            "NPK, soil texture, irrigation, season and yield "
            "prediction are not yet included in the scoring model. "
            "These results are preliminary decision-support "
            "information, not guaranteed crop recommendations."
        )


# --------------------------------------------------
# PAGE 4: WEATHER INTELLIGENCE
# --------------------------------------------------



def weather_intelligence():

    import pandas as pd
    import plotly.express as px
    import streamlit as st

    from datetime import datetime

    from services.weather_service import (
        get_coordinates,
        get_weather,
        get_weather_description
    )

    render_page_header(
        "Weather Intelligence",
        "Monitor real-time weather conditions, forecasts and agricultural risks.",
        "WEATHER ANALYTICS",
        "🌦️"
    )

    # ==========================================
    # LOCATION SEARCH
    # ==========================================

    st.markdown("### Explore Weather Conditions")

    col1, col2 = st.columns([3, 1])

    with col1:
        place = st.text_input(
            "Enter City / District",
            value="Panipat",
            placeholder="Example: Panipat, Karnal, Hisar"
        )

    with col2:
        st.write("")
        st.write("")
        search_weather = st.button(
            "Get Weather",
            use_container_width=True
        )

    if "weather_location" not in st.session_state:
        st.session_state.weather_location = "Panipat"

    if search_weather and place.strip():
        st.session_state.weather_location = place.strip()

    location_name = st.session_state.weather_location

    # ==========================================
    # FETCH WEATHER DATA
    # ==========================================

    @st.cache_data(ttl=900, show_spinner=False)
    def load_weather_data(city):

        coordinates = get_coordinates(city)

        weather = get_weather(
            coordinates["latitude"],
            coordinates["longitude"]
        )

        return coordinates, weather

    try:

        with st.spinner(
            f"Retrieving live weather information for {location_name}..."
        ):

            coordinates, weather = load_weather_data(
                location_name
            )

    except Exception as error:

        st.error(f"Weather data retrieval failed: {error}")

        st.info(
            "Check your internet connection or try another city name."
        )

        return

    current = weather.get("current", {})
    daily = weather.get("daily", {})
    hourly = weather.get("hourly", {})

    if not current or not daily:
        st.error("The weather provider returned incomplete data.")
        return

    # ==========================================
    # LOCATION INFORMATION
    # ==========================================

    st.divider()

    st.markdown("### Location Information")

    a, b, c = st.columns(3)

    a.metric(
        "Location",
        coordinates["name"]
    )

    b.metric(
        "State",
        coordinates["state"]
    )

    c.metric(
        "Country",
        coordinates["country"]
    )

    st.caption(
        f"Coordinates: {coordinates['latitude']}, "
        f"{coordinates['longitude']}"
    )

    # ==========================================
    # CURRENT WEATHER
    # ==========================================

    st.divider()

    st.markdown("### Current Weather Conditions")

    temperature = current.get("temperature_2m", 0)
    feels_like = current.get("apparent_temperature", 0)
    humidity = current.get("relative_humidity_2m", 0)
    rainfall = current.get("precipitation", 0)
    rain = current.get("rain", 0)
    wind = current.get("wind_speed_10m", 0)
    wind_direction = current.get("wind_direction_10m", 0)

    weather_code = current.get("weather_code", 0)

    description = get_weather_description(
        weather_code
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Temperature",
        f"{temperature} °C",
        help="Current air temperature"
    )

    m2.metric(
        "Feels Like",
        f"{feels_like} °C"
    )

    m3.metric(
        "Humidity",
        f"{humidity}%"
    )

    m4.metric(
        "Wind Speed",
        f"{wind} km/h"
    )

    m5, m6, m7, m8 = st.columns(4)

    m5.metric(
        "Weather Condition",
        description
    )

    m6.metric(
        "Precipitation",
        f"{rainfall} mm"
    )

    m7.metric(
        "Rainfall",
        f"{rain} mm"
    )

    m8.metric(
        "Wind Direction",
        f"{wind_direction}°"
    )

    # ==========================================
    # AGRICULTURAL WEATHER ADVISORY
    # ==========================================

    st.divider()

    st.markdown("### Agricultural Weather Advisory")

    advisory = []

    if temperature >= 40:
        advisory.append(
            ("High Temperature",
             "Extreme heat conditions. Consider irrigation "
             "and monitor crops for heat stress.")
        )

    elif temperature >= 35:
        advisory.append(
            ("Temperature Alert",
             "High temperature may increase crop water requirements.")
        )

    elif temperature <= 5:
        advisory.append(
            ("Cold Weather Alert",
             "Very low temperatures may increase frost-related risks.")
        )

    if humidity >= 85:
        advisory.append(
            ("High Humidity",
             "High humidity may increase the risk of fungal diseases.")
        )

    if rainfall >= 20:
        advisory.append(
            ("Heavy Rainfall",
             "Significant rainfall has been recorded. Monitor "
             "field drainage and waterlogging.")
        )

    if wind >= 40:
        advisory.append(
            ("Strong Winds",
             "Strong winds may affect standing crops and spraying operations.")
        )

    if not advisory:
        st.success(
            "No major weather risk detected from the current "
            "temperature, humidity, rainfall and wind indicators."
        )

    else:

        for title, message in advisory:

            st.warning(
                f"**{title}:** {message}"
            )

    st.caption(
        "These are rule-based weather advisories, not "
        "official agricultural forecasts or disease predictions."
    )

    # ==========================================
    # SEVEN-DAY FORECAST
    # ==========================================

    st.divider()

    st.markdown("### 7-Day Weather Forecast")

    forecast_df = pd.DataFrame({

        "Date": pd.to_datetime(
            daily["time"]
        ),

        "Weather Code": daily["weather_code"],

        "Maximum Temperature": daily["temperature_2m_max"],

        "Minimum Temperature": daily["temperature_2m_min"],

        "Rainfall": daily["precipitation_sum"],

        "Rain Probability": daily["precipitation_probability_max"],

        "Maximum Wind Speed": daily["wind_speed_10m_max"]

    })

    forecast_df["Condition"] = forecast_df[
        "Weather Code"
    ].apply(get_weather_description)

    forecast_df["Date"] = forecast_df[
        "Date"
    ].dt.strftime("%d %b")

    st.dataframe(
        forecast_df[
            [
                "Date",
                "Condition",
                "Maximum Temperature",
                "Minimum Temperature",
                "Rainfall",
                "Rain Probability",
                "Maximum Wind Speed"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ==========================================
    # WEATHER ANALYTICS
    # ==========================================

    st.divider()
    st.markdown("### Weather Analytics")

    # Keep chart inputs numeric and avoid misleading Plotly colour scales
    # when every forecast value is zero.
    numeric_columns = [
        "Maximum Temperature",
        "Minimum Temperature",
        "Rainfall",
        "Rain Probability",
        "Maximum Wind Speed",
    ]
    for column in numeric_columns:
        forecast_df[column] = pd.to_numeric(
            forecast_df[column], errors="coerce"
        )

    left, right = st.columns(2)

    with left:
        fig = px.line(
            forecast_df,
            x="Date",
            y=["Maximum Temperature", "Minimum Temperature"],
            markers=True,
            title="7-Day Temperature Forecast",
            color_discrete_sequence=["#E76F51", "#277DA1"],
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        fig.update_layout(
            template="plotly_white",
            height=380,
            xaxis_title="Date",
            yaxis_title="Temperature (°C)",
            legend_title_text="",
            margin=dict(l=15, r=15, t=55, b=15),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        rainfall_values = forecast_df["Rainfall"].fillna(0)
        if rainfall_values.max() <= 0:
            st.markdown("#### Expected Daily Rainfall")
            st.info(
                "No rainfall is currently forecast for these 7 days. "
                "The chart is hidden because every daily rainfall value is 0 mm."
            )
        else:
            rain_chart = forecast_df.copy()
            rain_chart["Rainfall"] = rain_chart["Rainfall"].fillna(0)
            fig = px.bar(
                rain_chart,
                x="Date",
                y="Rainfall",
                title="Expected Daily Rainfall",
                text="Rainfall",
                color_discrete_sequence=["#2D7A52"],
            )
            fig.update_traces(
                texttemplate="%{text:.1f} mm",
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                template="plotly_white",
                height=380,
                xaxis_title="Date",
                yaxis_title="Rainfall (mm)",
                yaxis=dict(rangemode="tozero"),
                showlegend=False,
                margin=dict(l=15, r=15, t=55, b=15),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # RAIN PROBABILITY
    # ==========================================

    st.divider()
    st.markdown("### Rain Probability Analysis")

    probability = forecast_df["Rain Probability"].dropna()
    if probability.empty:
        st.info("Rain probability data is not available from the weather provider.")
    elif probability.max() <= 0:
        st.info(
            "The forecast currently shows a 0% chance of precipitation "
            "for all 7 days."
        )
    else:
        probability_df = forecast_df.dropna(
            subset=["Rain Probability"]
        ).copy()
        fig = px.bar(
            probability_df,
            x="Date",
            y="Rain Probability",
            title="Daily Probability of Precipitation",
            text="Rain Probability",
            color_discrete_sequence=["#3979A8"],
        )
        fig.update_traces(
            texttemplate="%{text:.0f}%",
            textposition="outside",
            cliponaxis=False,
        )
        fig.update_layout(
            template="plotly_white",
            height=350,
            yaxis_title="Probability (%)",
            xaxis_title="Date",
            yaxis=dict(range=[0, 100], ticksuffix="%"),
            showlegend=False,
            margin=dict(l=15, r=15, t=55, b=15),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # HOURLY WEATHER
    # ==========================================

    st.divider()
    st.markdown("### Hourly Weather Forecast")

    hourly_df = pd.DataFrame({
        "Time": pd.to_datetime(hourly.get("time", []), errors="coerce"),
        "Temperature": pd.to_numeric(
            pd.Series(hourly.get("temperature_2m", [])), errors="coerce"
        ),
        "Humidity": pd.to_numeric(
            pd.Series(hourly.get("relative_humidity_2m", [])), errors="coerce"
        ),
        "Rain Probability": pd.to_numeric(
            pd.Series(hourly.get("precipitation_probability", [])), errors="coerce"
        ),
        "Precipitation": pd.to_numeric(
            pd.Series(hourly.get("precipitation", [])), errors="coerce"
        ),
        "Wind Speed": pd.to_numeric(
            pd.Series(hourly.get("wind_speed_10m", [])), errors="coerce"
        ),
    })

    # Select the next 24 hours relative to the provider's local timestamp.
    hourly_df = hourly_df.dropna(subset=["Time"]).head(24).copy()
    if hourly_df.empty:
        st.info("Hourly forecast data is not currently available.")
    else:
        hourly_df["Time Label"] = hourly_df["Time"].dt.strftime("%I %p")

        left, right = st.columns(2)

        with left:
            temperature_df = hourly_df.dropna(subset=["Temperature"])
            if temperature_df.empty:
                st.info("Hourly temperature data is unavailable.")
            else:
                fig = px.line(
                    temperature_df,
                    x="Time",
                    y="Temperature",
                    markers=True,
                    title="Hourly Temperature (Next 24 Hours)",
                    color_discrete_sequence=["#E76F51"],
                )
                fig.update_traces(line=dict(width=3), marker=dict(size=6))
                fig.update_layout(
                    template="plotly_white",
                    height=350,
                    xaxis_title="Local time",
                    yaxis_title="Temperature (°C)",
                    hovermode="x unified",
                    margin=dict(l=15, r=15, t=55, b=15),
                )
                st.plotly_chart(fig, use_container_width=True)

        with right:
            rain_probability = hourly_df["Rain Probability"].dropna()
            if rain_probability.empty:
                st.info("Hourly precipitation probability is unavailable.")
            elif rain_probability.max() <= 0:
                st.markdown("#### Hourly Rain Probability")
                st.info(
                    "The next 24-hour forecast currently shows a 0% "
                    "chance of precipitation."
                )
            else:
                rain_df = hourly_df.dropna(
                    subset=["Rain Probability"]
                ).copy()
                fig = px.area(
                    rain_df,
                    x="Time",
                    y="Rain Probability",
                    title="Hourly Rain Probability (Next 24 Hours)",
                    color_discrete_sequence=["#277DA1"],
                )
                fig.update_traces(line=dict(width=2))
                fig.update_layout(
                    template="plotly_white",
                    height=350,
                    xaxis_title="Local time",
                    yaxis_title="Probability (%)",
                    yaxis=dict(range=[0, 100], ticksuffix="%"),
                    hovermode="x unified",
                    margin=dict(l=15, r=15, t=55, b=15),
                )
                st.plotly_chart(fig, use_container_width=True)

        # Actual hourly rainfall is useful even when probability is zero.
        hourly_rain = hourly_df["Precipitation"].fillna(0)
        if hourly_rain.max() > 0:
            st.markdown("#### Hourly Expected Precipitation")
            fig = px.bar(
                hourly_df,
                x="Time",
                y="Precipitation",
                title="Expected Rainfall by Hour",
                color_discrete_sequence=["#2D7A52"],
            )
            fig.update_layout(
                template="plotly_white",
                height=300,
                xaxis_title="Local time",
                yaxis_title="Precipitation (mm)",
                yaxis=dict(rangemode="tozero"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("View detailed hourly forecast data"):
            st.dataframe(
                hourly_df[
                    [
                        "Time",
                        "Temperature",
                        "Humidity",
                        "Rain Probability",
                        "Precipitation",
                        "Wind Speed",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    # ==========================================
    # DATA SOURCE
    # ==========================================

    st.divider()

    st.markdown("### Data Source")

    st.success(
        "Weather Intelligence is connected successfully "
        "to the Open-Meteo live weather API."
    )

    st.caption(
        f"Provider: Open-Meteo | "
        f"Location: {coordinates['name']}, "
        f"{coordinates['state']} | "
        f"Timezone: {coordinates['timezone']}"
    )

    st.caption(
        "Weather information is refreshed every 15 minutes "
        "through the application cache."
    )


    # ------------------------------------------
    # LOCATION SEARCH
    # ------------------------------------------

    render_section_header(
        "Select Your Location",
        "Enter an Indian city or district to retrieve its latest weather information."
    )

    with st.form("weather_search_form"):

        city = st.text_input(
            "Enter an Indian city or district",
            value="Panipat",
            placeholder="Example: Karnal, Hisar, Jaipur, Pune"
        )

        submitted = st.form_submit_button(
            "Get Weather Information",
            use_container_width=True
        )

    if submitted:

        if not city.strip():

            st.warning("Please enter a location.")

        else:

            try:

                with st.spinner(
                    "Fetching real weather information..."
                ):

                    location = get_coordinates(city.strip())

                    weather = get_weather(
                        location["latitude"],
                        location["longitude"]
                    )

                    st.session_state["weather_location"] = location
                    st.session_state["weather_data"] = weather

            except Exception as error:

                st.error(
                    f"Unable to retrieve weather information: {error}"
                )

    # ------------------------------------------
    # DISPLAY WEATHER
    # ------------------------------------------

    if "weather_data" not in st.session_state:

        st.info(
            "Enter a city above to explore its real weather conditions."
        )

        return

    location = st.session_state["weather_location"]

    weather = st.session_state["weather_data"]

    current = weather["current"]

    daily = weather["daily"]

    # ------------------------------------------
    # LOCATION INFORMATION
    # ------------------------------------------

    st.divider()

    st.subheader(
        f"📍 {location['name']}, {location['state']}"
    )

    st.caption(
        f"Latitude: {location['latitude']} | "
        f"Longitude: {location['longitude']}"
    )

    st.caption(
        f"Timezone: {location['timezone']} | "
        f"Weather source: Open-Meteo"
    )

    condition = get_weather_description(
        current["weather_code"]
    )

    st.markdown(f"### Current Conditions: {condition}")

    # ------------------------------------------
    # WEATHER METRICS
    # ------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Temperature",
            f"{current['temperature_2m']} °C"
        )

    with col2:

        st.metric(
            "Feels Like",
            f"{current['apparent_temperature']} °C"
        )

    with col3:

        st.metric(
            "Humidity",
            f"{current['relative_humidity_2m']}%"
        )

    with col4:

        st.metric(
            "Wind Speed",
            f"{current['wind_speed_10m']} km/h"
        )

    col5, col6 = st.columns(2)

    with col5:

        st.metric(
            "Current Precipitation",
            f"{current['precipitation']} mm"
        )

    with col6:

        st.metric(
            "Wind Direction",
            f"{current['wind_direction_10m']}°"
        )

    # ------------------------------------------
    # SEVEN DAY FORECAST
    # ------------------------------------------

    st.divider()

    render_section_header(
        "Seven-Day Weather Forecast",
        "Daily temperature, rainfall probability and wind conditions."
    )

    forecast_df = pd.DataFrame({

        "Date": daily["time"],

        "Maximum Temperature": daily[
            "temperature_2m_max"
        ],

        "Minimum Temperature": daily[
            "temperature_2m_min"
        ],

        "Rainfall": daily[
            "precipitation_sum"
        ],

        "Rain Probability": daily[
            "precipitation_probability_max"
        ],

        "Maximum Wind Speed": daily[
            "wind_speed_10m_max"
        ]

    })

    st.dataframe(
        forecast_df,
        use_container_width=True,
        hide_index=True
    )

    # ------------------------------------------
    # TEMPERATURE CHART
    # ------------------------------------------

    st.divider()

    render_section_header("Temperature Trends")

    temperature_chart = px.line(
        forecast_df,
        x="Date",
        y=[
            "Maximum Temperature",
            "Minimum Temperature"
        ],
        markers=True,
        title="Seven-Day Temperature Forecast",
        labels={
            "value": "Temperature (°C)",
            "variable": "Temperature Type"
        }
    )

    temperature_chart.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    st.plotly_chart(
        temperature_chart,
        use_container_width=True
    )

    # ------------------------------------------
    # RAINFALL CHART
    # ------------------------------------------

    render_section_header("Rainfall Forecast")

    rainfall_chart = px.bar(
        forecast_df,
        x="Date",
        y="Rainfall",
        title="Expected Daily Rainfall",
        labels={
            "Rainfall": "Rainfall (mm)"
        }
    )

    rainfall_chart.update_layout(
        template="plotly_white"
    )

    st.plotly_chart(
        rainfall_chart,
        use_container_width=True
    )

    # ------------------------------------------
    # WEATHER SUMMARY
    # ------------------------------------------

    st.divider()

    render_section_header(
        "Agricultural Weather Overview",
        "A summary of forecast conditions that may support farm planning."
    )

    total_rainfall = forecast_df["Rainfall"].sum()

    average_max_temp = forecast_df[
        "Maximum Temperature"
    ].mean()

    average_min_temp = forecast_df[
        "Minimum Temperature"
    ].mean()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Forecast Rainfall",
        f"{total_rainfall:.1f} mm"
    )

    col2.metric(
        "Average Maximum Temperature",
        f"{average_max_temp:.1f} °C"
    )

    col3.metric(
        "Average Minimum Temperature",
        f"{average_min_temp:.1f} °C"
    )

    st.info(
        "These weather indicators can support agricultural "
        "planning. Crop-specific recommendations will be "
        "developed using crop requirements and validated "
        "agronomic information."
    )

    # ------------------------------------------
    # DATA TRANSPARENCY
    # ------------------------------------------

    st.divider()

    with st.expander("Data Source & Methodology"):

        st.write(
            "Weather information is retrieved from the "
            "Open-Meteo Forecast API."
        )

        st.write(
            "The forecast is based on weather models and "
            "does not necessarily represent measurements "
            "from a local physical weather station."
        )

        st.write(
            "Forecast values may change as weather models "
            "are updated."
        )

        st.markdown(
            "[Open-Meteo API Documentation]"
            "(https://open-meteo.com/en/docs)"
        )


# --------------------------------------------------
# PAGE 5: MARKET INTELLIGENCE
# --------------------------------------------------


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

    # Show every distinct mandi present in the records retrieved from the
    # connected provider. No extra text-search field is needed.
    all_market_data = (
        df[["market", "district", "state"]]
        .drop_duplicates()
        .sort_values(
            ["state", "district", "market"],
            key=lambda column: column.astype(str).str.casefold()
        )
        .reset_index(drop=True)
    )

    market_options = [
        f"{row['market']} — {row['district']}, {row['state']}"
        for _, row in all_market_data.iterrows()
    ]
    market_options = ["All Mandis (India)"] + market_options
    selected_market = st.selectbox(
        "Choose a mandi",
        market_options,
        key="market_location_filter"
    )

    st.markdown("### Select Commodity")
    all_commodities = sorted(
        df["commodity"].dropna().unique().tolist(),
        key=str.casefold
    )
    commodity_options = ["All Commodities"] + all_commodities
    selected_commodity = st.selectbox(
        "Choose a commodity",
        commodity_options,
        key="market_commodity_filter"
    )

    filtered = df.copy()
    if selected_market != "All Mandis (India)":
        selected_row = all_market_data[
            (
                all_market_data["market"] + " — " +
                all_market_data["district"] + ", " +
                all_market_data["state"]
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
            "The provider returned the maximum 1,000 records requested. "
            "The mandi selector includes every distinct mandi in these returned records; "
            "it may not represent every mandi in India. The complete nationwide list "
            "requires paginated retrieval from the official source."
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


# --------------------------------------------------
# PAGE 6: CROP HEALTH LAB
# --------------------------------------------------

def crop_health():
    crop_health_lab()


# --------------------------------------------------
# PAGE 7: FARM SIMULATOR
# --------------------------------------------------


def farm_simulator():

    import pandas as pd
    import plotly.express as px
    import streamlit as st

    from services.farm_simulator_service import (
        COST_CATEGORIES,
        simulate_farm,
        compare_farm_scenarios,
        get_financial_summary
    )

    render_page_header(
        "Farm Decision Simulator",
        "Plan cultivation costs, estimate farm profitability and compare crop scenarios.",
        "AGRICULTURAL FINANCIAL INTELLIGENCE",
        "🚜"
    )

    st.caption(
        "Make informed farming decisions using customizable "
        "farm inputs and financial calculations."
    )

    st.divider()

    # ==========================================
    # FARM INPUTS
    # ==========================================

    render_section_header(
        "Farm Configuration",
        "Enter your cultivation details and expected market price."
    )

    with st.form("farm_simulation_form"):

        col1, col2 = st.columns(2)

        with col1:

            crop = st.selectbox(
                "Select Crop",
                [
                    "Wheat",
                    "Rice",
                    "Mustard",
                    "Cotton",
                    "Maize",
                    "Barley",
                    "Groundnut",
                    "Soybean",
                    "Sugarcane",
                    "Pearl Millet"
                ]
            )

            area_acres = st.number_input(
                "Farm Area (Acres)",
                min_value=0.1,
                max_value=10000.0,
                value=5.0,
                step=0.5
            )

        with col2:

            expected_yield_per_acre = st.number_input(
                "Expected Yield (Quintals / Acre)",
                min_value=0.1,
                value=20.0,
                step=1.0
            )

            selling_price_per_quintal = st.number_input(
                "Expected Selling Price (₹ / Quintal)",
                min_value=1.0,
                value=2500.0,
                step=100.0
            )

        st.markdown("### Cultivation Cost Breakdown")

        st.caption(
            "Enter estimated expenses per acre in Indian Rupees."
        )

        default_costs = {
            "seed": 2000,
            "fertilizer": 3500,
            "pesticides": 1000,
            "irrigation": 1500,
            "labour": 3000,
            "machinery": 2000,
            "transport": 1000,
            "other": 0
        }

        costs_per_acre = {}

        cost_columns = st.columns(2)

        for index, category in enumerate(COST_CATEGORIES):

            with cost_columns[index % 2]:

                costs_per_acre[category] = st.number_input(
                    f"{category.replace('_', ' ').title()} (₹)",
                    min_value=0.0,
                    value=float(default_costs.get(category, 0)),
                    step=500.0,
                    key=f"farm_cost_{category}"
                )

        submitted = st.form_submit_button(
            "Calculate Farm Profitability",
            use_container_width=True,
            type="primary"
        )

    # ==========================================
    # FINANCIAL SIMULATION
    # ==========================================

    if submitted:

        try:

            result = simulate_farm(
                crop=crop,
                area_acres=area_acres,
                expected_yield_per_acre=expected_yield_per_acre,
                selling_price_per_quintal=selling_price_per_quintal,
                costs_per_acre=costs_per_acre
            )

            st.session_state["farm_simulation_result"] = result

            st.success(
                "Farm financial simulation completed successfully."
            )

        except (ValueError, TypeError) as error:

            st.error(f"Unable to complete simulation: {error}")

            return

        except Exception as error:

            st.error(f"Unexpected simulation error: {error}")

            return

    # Display previously calculated results after reruns.

    result = st.session_state.get("farm_simulation_result")

    if result is None:

        st.info(
            "Enter your farm details above and calculate profitability "
            "to view your financial analysis."
        )

        return

    st.divider()

    # ==========================================
    # FINANCIAL SUMMARY
    # ==========================================

    render_section_header(
        "Financial Performance",
        "Estimated financial outcomes for your selected crop."
    )

    summary = get_financial_summary(result)

    st.caption(
        f"Crop: {result['crop']} | "
        f"Farm Area: {result['area_acres']} Acres"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Investment",
        summary["Total Investment"]
    )

    col2.metric(
        "Expected Revenue",
        summary["Expected Revenue"]
    )

    col3.metric(
        "Estimated Profit / Loss",
        summary["Estimated Profit/Loss"],
        delta=(
            "Profitable"
            if result["net_profit"] > 0
            else "Loss"
        )
    )

    col4.metric(
        "Return on Investment",
        summary["ROI"]
    )

    st.divider()

    # ==========================================
    # PRODUCTION INFORMATION
    # ==========================================

    render_section_header(
        "Production Analysis",
        "Understand the expected output and cultivation economics."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Production",
        f"{result['total_production_quintals']:,.2f} Q"
    )

    col2.metric(
        "Profit Per Acre",
        f"₹{result['profit_per_acre']:,.2f}"
    )

    col3.metric(
        "Cultivation Cost",
        f"₹{result['total_cultivation_cost']:,.2f}"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Break-even Price",
        (
            f"₹{result['break_even_price']:,.2f}"
            if result["break_even_price"] is not None
            else "Not Available"
        )
    )

    col2.metric(
        "Cost Per Quintal",
        (
            f"₹{result['cost_per_quintal']:,.2f}"
            if result["cost_per_quintal"] is not None
            else "Not Available"
        )
    )

    col3.metric(
        "Financial Status",
        result["financial_status"]
    )

    # ==========================================
    # COST BREAKDOWN
    # ==========================================

    st.divider()

    render_section_header(
        "Cultivation Cost Analysis",
        "See how your investment is distributed across farming activities."
    )

    cost_data = result["cost_breakdown"]

    cost_df = pd.DataFrame(
        [
            {
                "Category": category.replace("_", " ").title(),
                "Cost": amount
            }
            for category, amount in cost_data.items()
        ]
    )

    cost_df = cost_df[cost_df["Cost"] > 0]

    if not cost_df.empty:

        col1, col2 = st.columns(2)

        with col1:

            fig = px.pie(
                cost_df,
                names="Category",
                values="Cost",
                hole=0.55,
                title="Cultivation Cost Distribution"
            )

            fig.update_layout(
                height=400,
                margin=dict(t=50, b=20, l=20, r=20)
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col2:

            fig = px.bar(
                cost_df.sort_values("Cost", ascending=True),
                x="Cost",
                y="Category",
                orientation="h",
                title="Expense Comparison",
                text_auto=".2s"
            )

            fig.update_layout(
                height=400,
                xaxis_title="Cost (₹)",
                yaxis_title="Expense Category"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        st.dataframe(
            cost_df,
            use_container_width=True,
            hide_index=True
        )

    # ==========================================
    # REVENUE VS COST
    # ==========================================

    st.divider()

    render_section_header(
        "Revenue & Profitability",
        "Compare estimated revenue against cultivation investment."
    )

    financial_df = pd.DataFrame({
        "Financial Metric": [
            "Cultivation Investment",
            "Expected Revenue",
            "Net Profit"
        ],
        "Amount": [
            result["total_cultivation_cost"],
            result["gross_revenue"],
            result["net_profit"]
        ]
    })

    fig = px.bar(
        financial_df,
        x="Financial Metric",
        y="Amount",
        color="Financial Metric",
        text_auto=".2s",
        title="Farm Financial Performance"
    )

    fig.update_layout(
        showlegend=False,
        height=400,
        yaxis_title="Amount (₹)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================================
    # CROP SCENARIO COMPARISON
    # ==========================================

    st.divider()

    render_section_header(
        "Crop Scenario Comparison",
        "Compare the estimated profitability of different crops."
    )

    st.caption(
        "Use the same land area and cost assumptions to compare "
        "alternative crop choices."
    )

    with st.form("crop_comparison_form"):

        compare_col1, compare_col2 = st.columns(2)

        crop_options = [
            "Wheat",
            "Rice",
            "Mustard",
            "Cotton",
            "Maize",
            "Barley",
            "Groundnut",
            "Soybean",
            "Sugarcane",
            "Pearl Millet"
        ]

        with compare_col1:

            comparison_crop_1 = st.selectbox(
                "First Crop",
                crop_options,
                index=0
            )

            comparison_yield_1 = st.number_input(
                "First Crop Yield (Quintals/Acre)",
                min_value=0.1,
                value=20.0
            )

            comparison_price_1 = st.number_input(
                "First Crop Selling Price (₹/Quintal)",
                min_value=1.0,
                value=2500.0
            )

        with compare_col2:

            comparison_crop_2 = st.selectbox(
                "Second Crop",
                crop_options,
                index=1
            )

            comparison_yield_2 = st.number_input(
                "Second Crop Yield (Quintals/Acre)",
                min_value=0.1,
                value=25.0
            )

            comparison_price_2 = st.number_input(
                "Second Crop Selling Price (₹/Quintal)",
                min_value=1.0,
                value=2200.0
            )

        compare_submitted = st.form_submit_button(
            "Compare Crop Scenarios",
            use_container_width=True
        )

    if compare_submitted:

        try:

            scenarios = [
                {
                    "crop": comparison_crop_1,
                    "area_acres": area_acres,
                    "expected_yield_per_acre": comparison_yield_1,
                    "selling_price_per_quintal": comparison_price_1,
                    "costs_per_acre": costs_per_acre
                },
                {
                    "crop": comparison_crop_2,
                    "area_acres": area_acres,
                    "expected_yield_per_acre": comparison_yield_2,
                    "selling_price_per_quintal": comparison_price_2,
                    "costs_per_acre": costs_per_acre
                }
            ]

            comparison_results = compare_farm_scenarios(
                scenarios
            )

            st.session_state["farm_comparison_results"] = (
                comparison_results
            )

        except (ValueError, TypeError) as error:

            st.error(f"Comparison failed: {error}")

        except Exception as error:

            st.error(f"Unexpected comparison error: {error}")

    comparison_results = st.session_state.get(
        "farm_comparison_results"
    )

    if comparison_results:

        comparison_df = pd.DataFrame([
            {
                "Crop": item["crop"],
                "Production (Quintals)": item[
                    "total_production_quintals"
                ],
                "Investment (₹)": item[
                    "total_cultivation_cost"
                ],
                "Revenue (₹)": item["gross_revenue"],
                "Net Profit (₹)": item["net_profit"],
                "ROI (%)": item["roi_percentage"]
            }
            for item in comparison_results
        ])

        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True
        )

        
        fig = px.bar(
            comparison_df,
            x="Crop",
            y="Net Profit (₹)",
            color="Crop",
            title="Crop-wise Profit Comparison"
        )

        fig.update_traces(
            text=comparison_df["Net Profit (₹)"],
            texttemplate="₹%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Net Profit: ₹%{y:,.2f}"
                "<extra></extra>"
            )
        )

        fig.update_layout(
            height=430,
            showlegend=False,
            yaxis_title="Net Profit (₹)",
            xaxis_title="Crop",
            uniformtext_minsize=10,
            uniformtext_mode="hide",
            margin=dict(t=60, b=40)
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


        best_crop = max(
            comparison_results,
            key=lambda item: item["net_profit"]
        )

        st.success(
            f"Based on the entered assumptions, "
            f"{best_crop['crop']} has the highest estimated "
            f"net profit of ₹{best_crop['net_profit']:,.2f}."
        )

    # ==========================================
    # DOWNLOAD FINANCIAL REPORT
    # ==========================================

    st.divider()

    render_section_header(
        "Download Financial Report",
        "Export your farm simulation results for future reference."
    )

    report_df = pd.DataFrame([
        {"Metric": key, "Value": value}
        for key, value in summary.items()
    ])

    st.download_button(
        label="Download Farm Financial Report (CSV)",
        data=report_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{crop.lower()}_farm_financial_report.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.caption(
        "AgroVision AI | Farm financial estimates are based on "
        "user-provided inputs. Actual farming outcomes may vary."
    )



# --------------------------------------------------
# PAGE 8: RESEARCH CENTRE
# --------------------------------------------------

def research_centre():

    render_page_header(
        "Agricultural Research Centre",
        "Discover real agricultural studies, publications and evidence from scholarly research.",
        "RESEARCH & ANALYTICS",
        "🔍"
    )

    st.caption(
        "Live scholarly records are retrieved from OpenAlex. "
        "Search results are publication metadata, not AI-generated research."
    )

    # --------------------------------------------------
    # SEARCH CONTROLS
    # --------------------------------------------------

    render_section_header(
        "Research Library",
        "Search published studies across crop science, soil, irrigation, climate and agricultural technology."
    )

    suggested_topics = [
        "precision agriculture",
        "climate change and crop yield",
        "soil health and fertility",
        "drip irrigation",
        "plant disease detection",
        "agricultural machine learning",
        "remote sensing in agriculture",
        "sustainable farming",
    ]

    with st.form("agrovision_research_search"):
        search_query = st.text_input(
            "Research topic or keywords",
            value=st.session_state.get(
                "research_query",
                "precision agriculture"
            ),
            placeholder="e.g. wheat disease detection using machine learning"
        )

        col1, col2, col3 = st.columns(3)

        current_year = date.today().year

        with col1:
            year_from = st.number_input(
                "From publication year",
                min_value=1900,
                max_value=current_year,
                value=max(2000, current_year - 10),
                step=1
            )

        with col2:
            year_to = st.number_input(
                "To publication year",
                min_value=1900,
                max_value=current_year,
                value=current_year,
                step=1
            )

        with col3:
            sort_by = st.selectbox(
                "Sort results",
                ["Relevance", "Newest", "Most cited"]
            )

        filter_col, count_col = st.columns([2, 1])

        with filter_col:
            open_access_only = st.checkbox(
                "Show only open-access publications",
                value=False
            )

        with count_col:
            result_limit = st.selectbox(
                "Results per search",
                [10, 20, 30, 50],
                index=1
            )

        submitted = st.form_submit_button(
            "Search Research Papers",
            type="primary",
            use_container_width=True
        )

    # Suggested searches are real query shortcuts.
    st.markdown("**Explore a topic**")
    topic_columns = st.columns(4)
    for index, topic in enumerate(suggested_topics):
        with topic_columns[index % 4]:
            if st.button(
                topic,
                key=f"research_topic_{index}",
                use_container_width=True
            ):
                st.session_state["research_query"] = topic
                st.session_state["research_search_pending"] = True
                st.rerun()

    if submitted:
        st.session_state["research_query"] = search_query
        st.session_state["research_search_pending"] = True
        st.session_state["research_filters"] = {
            "year_from": int(year_from),
            "year_to": int(year_to),
            "sort_by": sort_by,
            "open_access_only": open_access_only,
            "result_limit": result_limit,
        }

    if st.session_state.pop("research_search_pending", False):
        filters = st.session_state.get(
            "research_filters",
            {
                "year_from": max(2000, current_year - 10),
                "year_to": current_year,
                "sort_by": "Relevance",
                "open_access_only": False,
                "result_limit": 20,
            }
        )

        try:
            with st.spinner("Searching live scholarly research records..."):
                research_data = search_agricultural_research(
                    query=st.session_state.get("research_query", ""),
                    year_from=filters["year_from"],
                    year_to=filters["year_to"],
                    open_access_only=filters["open_access_only"],
                    sort_by=filters["sort_by"],
                    per_page=filters["result_limit"],
                )

            st.session_state["research_results"] = research_data
            st.session_state["research_error"] = None

        except (ResearchAPIError, ValueError) as error:
            st.session_state["research_error"] = str(error)
            st.session_state["research_results"] = None

    if st.session_state.get("research_error"):
        st.error(st.session_state["research_error"])

    research_data = st.session_state.get("research_results")

    if research_data:
        results = research_data["results"]
        total_count = research_data["total_count"]

        st.divider()
        render_section_header(
            "Search Results",
            f"Live results for: {research_data['query']}"
        )

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Matching records", f"{total_count:,}")
        metric2.metric("Results displayed", len(results))
        metric3.metric(
            "Open access in results",
            sum(1 for item in results if item["is_open_access"])
        )

        if not results:
            st.info(
                "No matching publications were returned. Try broader keywords "
                "or a wider publication-year range."
            )

        for index, paper in enumerate(results, start=1):
            with st.container(border=True):
                st.markdown(f"**{index}. {paper['title']}**")

                authors = ", ".join(paper["authors"][:5])
                if len(paper["authors"]) > 5:
                    authors += ", et al."
                st.caption(
                    f"{authors or 'Author details unavailable'}"
                    f"  ·  {paper['year'] or 'Year unavailable'}"
                    f"  ·  {paper['journal']}"
                )

                badge_col, citation_col = st.columns([3, 1])
                with badge_col:
                    if paper["is_open_access"]:
                        st.success(
                            f"Open access · {paper['oa_status'].replace('_', ' ').title()}",
                            icon="🔓"
                        )
                    else:
                        st.info("Access status not marked as open access")
                with citation_col:
                    st.metric("Citations", f"{paper['citations']:,}")

                if paper["abstract"]:
                    with st.expander("Read abstract"):
                        st.write(paper["abstract"])
                else:
                    st.caption("Abstract is not available in the provider record.")

                if paper["url"]:
                    st.link_button(
                        "Open publication record",
                        paper["url"],
                        use_container_width=False
                    )

        st.caption(
            "Citation counts and publication metadata are supplied by OpenAlex "
            "and may change as its scholarly index is updated."
        )

    elif not st.session_state.get("research_error"):
        st.info(
            "Enter a topic or choose one of the suggested searches to discover "
            "live agricultural research publications."
        )

    # --------------------------------------------------
    # SOURCE TRANSPARENCY
    # --------------------------------------------------

    st.divider()
    render_section_header(
        "About the Research Data",
        "Understand where the publication records come from."
    )

    st.write(
        "AgroVision AI uses the OpenAlex public API to discover scholarly works. "
        "The service provides searchable publication metadata such as titles, "
        "authors, publication dates, source names, open-access status and citation counts."
    )

    st.markdown(
        "[OpenAlex API documentation](https://help.openalex.org/api/)  ·  "
        "[OpenAlex website](https://openalex.org/)"
    )

    st.caption(
        "Research discovery is informational. Always read the original paper "
        "and verify its methods, context and findings before applying results "
        "to farm-level decisions."
    )


# PAGE 9: REPORTS
# --------------------------------------------------

from reports_insights import reports


# --------------------------------------------------
# PAGE 10: DATA SOURCES
# --------------------------------------------------

def data_sources():
    data_sources_page()

# ==========================================
# AGROVISION CUSTOM NAVIGATION
# ==========================================

# PAGE DEFINITIONS

home_page = st.Page(
    home,
    title="Home",
    icon="🏠",
    default=True,
)

dashboard_page = st.Page(
    dashboard,
    title="Dashboard",
    icon="📊",
)

crop_page = st.Page(
    crop_intelligence,
    title="Crop Intelligence",
    icon="🌾",
)

health_page = st.Page(
    crop_health,
    title="Crop Health Lab",
    icon="🔬",
)

simulator_page = st.Page(
    farm_simulator,
    title="Farm Simulator",
    icon="🧮",
)

weather_page = st.Page(
    weather_intelligence,
    title="Weather Intelligence",
    icon="🌦️",
)

market_page = st.Page(
    market_intelligence,
    title="Market Intelligence",
    icon="📈",
)

research_page = st.Page(
    research_centre,
    title="Research Centre",
    icon="🔍",
)

reports_page = st.Page(
    reports,
    title="Reports & Insights",
    icon="📑",
)

sources_page = st.Page(
    data_sources,
    title="Data Sources",
    icon="🌐",
)


# NAVIGATION GROUPS

pages = {

    "OVERVIEW": [
        home_page,
        dashboard_page,
    ],

    "CROP INTELLIGENCE": [
        crop_page,
        health_page,
        simulator_page,
    ],

    "WEATHER & MARKETS": [
        weather_page,
        market_page,
    ],

    "RESEARCH": [
        research_page,
        reports_page,
    ],

    "PLATFORM": [
        sources_page,
    ],

}


# HIDE STREAMLIT'S AUTOMATIC NAVIGATION

navigation = st.navigation(
    pages,
    position="hidden",
)


# ==========================================
# CUSTOM AGROVISION SIDEBAR
# ==========================================

with st.sidebar:

    # BRANDING

    st.html("""
        <div class="av-sidebar-brand">
            <div class="av-sidebar-logo">🌱</div>
            <div class="av-sidebar-name">AgroVision</div>
            <div class="av-sidebar-tagline">
                AGRICULTURAL INTELLIGENCE
            </div>
            <div class="av-sidebar-tagline">
                PLATFORM
            </div>
        </div>
    """)

    st.divider()

    # OVERVIEW

    st.markdown("**OVERVIEW**")

    st.page_link(
        home_page,
        label="Home",
        icon="🏠",
        use_container_width=True,
    )

    st.page_link(
        dashboard_page,
        label="Dashboard",
        icon="📊",
        use_container_width=True,
    )

    st.divider()

    # CROP INTELLIGENCE

    st.markdown("**CROP INTELLIGENCE**")

    st.page_link(
        crop_page,
        label="Crop Intelligence",
        icon="🌾",
        use_container_width=True,
    )

    st.page_link(
        health_page,
        label="Crop Health Lab",
        icon="🔬",
        use_container_width=True,
    )

    st.page_link(
        simulator_page,
        label="Farm Simulator",
        icon="🧮",
        use_container_width=True,
    )

    st.divider()

    # WEATHER & MARKETS

    st.markdown("**WEATHER & MARKETS**")

    st.page_link(
        weather_page,
        label="Weather Intelligence",
        icon="🌦️",
        use_container_width=True,
    )

    st.page_link(
        market_page,
        label="Market Intelligence",
        icon="📈",
        use_container_width=True,
    )

    st.divider()

    # RESEARCH

    st.markdown("**RESEARCH**")

    st.page_link(
        research_page,
        label="Research Centre",
        icon="🔍",
        use_container_width=True,
    )

    st.page_link(
        reports_page,
        label="Reports & Insights",
        icon="📑",
        use_container_width=True,
    )

    st.divider()

    # PLATFORM

    st.markdown("**PLATFORM**")

    st.page_link(
        sources_page,
        label="Data Sources",
        icon="🌐",
        use_container_width=True,
    )

    st.divider()

    # PLATFORM INFORMATION

    st.markdown("**PLATFORM COVERAGE**")

    st.caption("🇮🇳 India-wide Coverage")
    st.caption("📍 Haryana Regional Insights")

    st.markdown(
        """
        <div class="av-sidebar-status">
            <span class="av-status-dot"></span>
            Platform Operational
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.caption("AGROVISION AI · VERSION 0.2")


# RUN APPLICATION

navigation.run()
