import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_current_weather(lat: float, lon: float):
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return {"error": "No weather API key configured"}

    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
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
            "confidence": "high"
        }
    except Exception as e:
        return {"error": str(e)}

def is_raining(weather_data):
    return weather_data.get("rain_probability", 0) > 0.5 or "rain" in weather_data.get("description", "").lower()

def is_too_hot(weather_data):
    return weather_data.get("temperature_c", 20) > 35

def get_daylight_status(weather_data):
    return weather_data.get("is_day", "day")
