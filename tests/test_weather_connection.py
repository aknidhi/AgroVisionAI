
from services.weather_service import (
    get_coordinates,
    get_weather,
    get_weather_description
)


def main():

    print("=" * 45)
    print("AGROVISION - WEATHER API CONNECTION TEST")
    print("=" * 45)

    city = "Panipat"

    try:

        print("\n1. Connecting to Geocoding API...")

        location = get_coordinates(city)

        print("Location found successfully!")

        print("City:", location["name"])
        print("State:", location["state"])
        print("Latitude:", location["latitude"])
        print("Longitude:", location["longitude"])

        print("\n2. Connecting to Weather API...")

        weather = get_weather(
            location["latitude"],
            location["longitude"]
        )

        current = weather["current"]

        print("\nWeather retrieved successfully!")

        print("Temperature:",
              current["temperature_2m"], "°C")

        print("Feels Like:",
              current["apparent_temperature"], "°C")

        print("Humidity:",
              current["relative_humidity_2m"], "%")

        print("Wind Speed:",
              current["wind_speed_10m"], "km/h")

        print("Rainfall:",
              current["precipitation"], "mm")

        print("Condition:",
              get_weather_description(
                  current["weather_code"]
              ))

        print("\n3. Seven-Day Forecast")

        daily = weather["daily"]

        for i, date in enumerate(daily["time"]):

            print(
                date,
                "| Max:",
                daily["temperature_2m_max"][i],
                "°C | Min:",
                daily["temperature_2m_min"][i],
                "°C | Rain:",
                daily["precipitation_sum"][i],
                "mm"
            )

        print("\nAPI CONNECTION SUCCESSFUL!")

    except Exception as error:

        print("\nAPI CONNECTION FAILED!")
        print("Error:", error)


if __name__ == "__main__":
    main()
