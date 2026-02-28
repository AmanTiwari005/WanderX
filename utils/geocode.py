import requests
import time
from utils.cache_manager import get_cache

_last_request_time = 0

def geocode_location(query: str):
    global _last_request_time

    query = query.strip()
    if not query:
        return None

    # Check cache first using CacheManager
    cache = get_cache()
    cached = cache.get("geocode", query.lower())
    if cached:
        return cached

    # Rate limiting: respect Nominatim's 1 request/second rule
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:  # Small buffer
        time.sleep(1.1 - elapsed)

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        # CRITICAL: Use a proper, unique User-Agent with your contact
        headers = {
            "User-Agent": "WanderTrip-App/1.0 (amantiwari312003@gmail.com)"  # ← CHANGE THIS!
        }

        res = requests.get(url, params=params, headers=headers, timeout=20)
        _last_request_time = time.time()

        if res.status_code == 403:
            print("Blocked by Nominatim (403) – check your User-Agent and usage policy.")
            return None
        res.raise_for_status()

        data = res.json()
        if not data:
            return None

        item = data[0]
        city_part = item.get("display_name", "").split(",")[0].strip()

        result = {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "label": city_part or "Location"
        }

        # Cache result using CacheManager
        cache = get_cache()
        cache.set("geocode", query.lower(), result)
        return result

    except requests.exceptions.Timeout:
        print("Nominatim timeout – try again in a moment.")
        return None
    except Exception as e:
        print(f"Geocode error: {e}")
        return None