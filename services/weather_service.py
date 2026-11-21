
import requests


# Open-Meteo API endpoints
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_coordinates(place_name):
    """
    Find the geographical coordinates of an Indian city.
    """

    params = {
        "name": place_name,
        "count": 5,
        "language": "en",
        "countryCode": "IN"
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    locations = data.get("results", [])

    if not locations:
        raise ValueError(
            f"No location found for: {place_name}"
        )

    location = locations[0]

    return {
        "name": location["name"],
        "state": location.get("admin1", "Unknown"),
        "country": location.get("country", "India"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location.get("timezone", "auto")
    }


def get_weather(latitude, longitude):
    """
    Retrieve current weather and a 7-day forecast.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "is_day",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m"
        ],

        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "wind_speed_10m"
        ],

        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "sunrise",
            "sunset"
        ],

        "forecast_days": 7,
        "timezone": "auto"
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_weather_description(weather_code):
    """
    Convert WMO weather codes into readable descriptions.
    """

    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail"
    }

    return descriptions.get(
        weather_code,
        "Unknown weather condition"
    )
