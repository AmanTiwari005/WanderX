"""
📸 Golden Hour Planner — Best photography times and photo spots.
"""
import json
import logging
import math
import datetime
from utils.web_search import search_web

logger = logging.getLogger("wanderx.golden_hour")


def calculate_golden_hours(lat, lon, date=None):
    """
    Estimates sunrise/sunset times using a simplified solar position algorithm.
    Returns golden hour and blue hour windows.
    """
    if date is None:
        date = datetime.date.today()
    
    # Day of year
    n = date.timetuple().tm_yday
    
    # Solar declination (simplified)
    declination = -23.45 * math.cos(math.radians(360 / 365 * (n + 10)))
    
    # Hour angle
    lat_rad = math.radians(lat)
    decl_rad = math.radians(declination)
    
    try:
        cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)
        cos_omega = max(-1, min(1, cos_omega))  # Clamp
        omega = math.degrees(math.acos(cos_omega))
    except:
        omega = 90  # Fallback

    # Sunrise/Sunset in hours (UTC-approximate)
    solar_noon = 12.0 - lon / 15.0
    sunrise_utc = solar_noon - omega / 15.0
    sunset_utc = solar_noon + omega / 15.0
    
    # Convert to local-ish time (rough estimate using longitude)
    tz_offset = round(lon / 15.0)
    sunrise_local = sunrise_utc + tz_offset
    sunset_local = sunset_utc + tz_offset
    
    def hours_to_time(h):
        h = h % 24
        hours = int(h)
        minutes = int((h - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    return {
        "sunrise": hours_to_time(sunrise_local),
        "sunset": hours_to_time(sunset_local),
        "golden_hour_morning": f"{hours_to_time(sunrise_local)} - {hours_to_time(sunrise_local + 1)}",
        "golden_hour_evening": f"{hours_to_time(sunset_local - 1)} - {hours_to_time(sunset_local)}",
        "blue_hour_morning": f"{hours_to_time(sunrise_local - 0.5)} - {hours_to_time(sunrise_local)}",
        "blue_hour_evening": f"{hours_to_time(sunset_local)} - {hours_to_time(sunset_local + 0.5)}",
    }


def get_photo_spots(client, location):
    """
    Finds best photography spots using web search + LLM.
    """
    try:
        results = search_web(f"best photo spots {location} instagram viewpoints 2025", max_results=6)
        
        prompt = f"""
Based on these search results, identify the top 5 photography spots in {location}.

Results: {json.dumps(results[:4])}

Return ONLY valid JSON:
{{
    "spots": [
        {{
            "name": "Spot Name",
            "type": "Viewpoint/Monument/Street/Nature/Rooftop",
            "best_time": "Golden Hour/Blue Hour/Night/Any",
            "tip": "Specific photography tip for this spot"
        }}
    ]
}}
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Photo Spots Error: {e}")
        return {"spots": []}
