import requests
import os
from dotenv import load_dotenv
import datetime
import logging
import time

load_dotenv()
logger = logging.getLogger("wanderx.weather_agent")


class WeatherAgent:
    def __init__(self):
        self.api_key = os.getenv("OWM_API_KEY")

    def get_weather_intel(self, location_coords, hour=None):
        if not location_coords:
            return {"error": "No location"}
        if hour is None:
            hour = datetime.datetime.now().hour + datetime.datetime.now().minute / 60.0

        fetch_start = time.time()
        weather = self._get_current_weather(location_coords["lat"], location_coords["lon"])
        fetch_ms = round((time.time() - fetch_start) * 1000)

        if weather.get("error"):
            return {"error": weather["error"], "weather_data": weather}

        daylight = self._get_remaining_daylight_hours(weather, hour)
        rain_prob = self._compute_rain_probability(weather)
        heat_index = self._compute_heat_index(weather.get("temperature_c", 25), weather.get("humidity", 50))
        wind_chill = self._compute_wind_chill(weather.get("temperature_c", 25), weather.get("wind_speed", 0))

        return {
            "weather_data": {
                **weather,
                "rain_probability": rain_prob,
                "heat_index_c": heat_index,
                "wind_chill_c": wind_chill,
            },
            "daylight_remaining": daylight,
            "condition": weather.get("description", "Unknown"),
            "temp_c": weather.get("temperature_c", 0),
            "data_age_minutes": 0,
            "fetched_at": datetime.datetime.now().isoformat(),
            "fetch_latency_ms": fetch_ms,
        }

    def _get_current_weather(self, lat, lon):
        if not self.api_key:
            return {"error": "No weather API key configured"}
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if resp.status_code != 200:
                return {"error": f"Weather API error: {data.get('message', 'Unknown')}"}
            main = data.get("main", {})
            wind = data.get("wind", {})
            clouds = data.get("clouds", {})
            rain_data = data.get("rain", {})
            snow_data = data.get("snow", {})
            sys_data = data.get("sys", {})
            vis_m = data.get("visibility", 10000)
            return {
                "temperature_c": round(main.get("temp", 25), 1),
                "feels_like_c": round(main.get("feels_like", 25), 1),
                "temp_min_c": round(main.get("temp_min", 25), 1),
                "temp_max_c": round(main.get("temp_max", 25), 1),
                "humidity": main.get("humidity", 50),
                "pressure_hpa": main.get("pressure", 1013),
                "description": data["weather"][0]["description"].capitalize(),
                "weather_id": data["weather"][0].get("id", 800),
                "weather_main": data["weather"][0].get("main", "Clear"),
                "rain_1h_mm": rain_data.get("1h", 0),
                "rain_3h_mm": rain_data.get("3h", 0),
                "snow_1h_mm": snow_data.get("1h", 0),
                "snow_3h_mm": snow_data.get("3h", 0),
                "wind_speed": wind.get("speed", 0),
                "wind_gust": wind.get("gust", 0),
                "wind_deg": wind.get("deg", 0),
                "visibility_m": vis_m,
                "visibility_km": round(vis_m / 1000, 1),
                "cloud_cover_pct": clouds.get("all", 0),
                "is_day": "day" if data["weather"][0]["icon"].endswith("d") else "night",
                "sunrise": sys_data.get("sunrise"),
                "sunset": sys_data.get("sunset"),
                "city": data.get("name", "Unknown"),
                "country": sys_data.get("country", ""),
                "lat": lat, "lon": lon,
                "confidence": "high",
                "source": "OpenWeatherMap",
                "timestamp": datetime.datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return {"error": str(e)}

    def _compute_rain_probability(self, weather):
        prob = 0.0
        wid = weather.get("weather_id", 800)
        desc = (weather.get("description") or "").lower()
        clouds = weather.get("cloud_cover_pct", 0)
        rain_mm = weather.get("rain_1h_mm", 0) + weather.get("rain_3h_mm", 0) / 3
        if 200 <= wid < 300: prob = 0.95
        elif 300 <= wid < 400: prob = 0.75
        elif 500 <= wid < 505: prob = 0.85
        elif 505 <= wid < 600: prob = 0.95
        elif 600 <= wid < 700: prob = 0.80
        elif 700 <= wid < 800: prob = 0.15
        elif wid == 800: prob = 0.02
        elif 801 <= wid <= 802: prob = 0.10 + clouds / 500
        elif 803 <= wid <= 804: prob = 0.20 + clouds / 400
        if rain_mm > 5: prob = max(prob, 0.95)
        elif rain_mm > 1: prob = max(prob, 0.80)
        elif rain_mm > 0: prob = max(prob, 0.60)
        if any(kw in desc for kw in ["rain", "shower", "drizzle", "thunder", "storm"]):
            prob = max(prob, 0.70)
        if any(kw in desc for kw in ["snow", "sleet", "blizzard"]):
            prob = max(prob, 0.75)
        return round(min(prob, 1.0), 2)

    def _compute_heat_index(self, temp_c, humidity):
        if temp_c < 27 or humidity < 40: return None
        t_f = temp_c * 9 / 5 + 32
        hi = (-42.379 + 2.04901523*t_f + 10.14333127*humidity - 0.22475541*t_f*humidity
              - 0.00683783*t_f**2 - 0.05481717*humidity**2 + 0.00122874*t_f**2*humidity
              + 0.00085282*t_f*humidity**2 - 0.00000199*t_f**2*humidity**2)
        return round((hi - 32) * 5 / 9, 1)

    def _compute_wind_chill(self, temp_c, wind_ms):
        wind_kmh = wind_ms * 3.6
        if temp_c > 10 or wind_kmh < 4.8: return None
        wc = 13.12 + 0.6215*temp_c - 11.37*(wind_kmh**0.16) + 0.3965*temp_c*(wind_kmh**0.16)
        return round(wc, 1)

    def _get_remaining_daylight_hours(self, weather_data, current_hour):
        sunset_ts = weather_data.get("sunset")
        if not sunset_ts: return max(0, 18 - current_hour)
        sunset_time = datetime.datetime.fromtimestamp(sunset_ts)
        sunset_hour = sunset_time.hour + sunset_time.minute / 60.0
        return round(max(0, sunset_hour - current_hour), 2)
