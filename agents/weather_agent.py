import requests
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

class WeatherAgent:
    def __init__(self):
        self.api_key = os.getenv("OWM_API_KEY")

    def get_weather_intel(self, location_coords, hour=12):
        """
        Fetches weather and daylight info.
        """
        if not location_coords:
             return {"error": "No location"}
             
        weather = self._get_current_weather(location_coords["lat"], location_coords["lon"])
        daylight = self._get_remaining_daylight_hours(weather, hour)
        
        return {
            "weather_data": weather,
            "daylight_remaining": daylight,
            "condition": weather.get("description", "Unknown"),
            "temp_c": weather.get("temperature_c", 0)
        }

    def _get_current_weather(self, lat: float, lon: float):
        if not self.api_key:
            return {"error": "No weather API key configured"}

        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if resp.status_code != 200:
                return {"error": f"Weather API error: {data.get('message', 'Unknown')}"}

            return {
                "temperature_c": round(data["main"]["temp"]),
                "feels_like_c": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"].capitalize(),
                "rain_probability": data.get("rain", {}).get("1h", 0),  # mm in last hour as proxy
                "is_day": "day" if data["weather"][0]["icon"].endswith("d") else "night",
                "city": data["name"],
                "confidence": "high",
                "sunset": data.get("sys", {}).get("sunset")
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_remaining_daylight_hours(self, weather_data, current_hour):
        sunset_ts = weather_data.get("sunset")
        if not sunset_ts:
            return max(0, 18 - current_hour)
        
        sunset_time = datetime.datetime.fromtimestamp(sunset_ts)
        sunset_hour = sunset_time.hour + sunset_time.minute / 60.0
        
        remaining = sunset_hour - current_hour
        return max(0, remaining)
