import requests
import os
from dotenv import load_dotenv
from utils.geocode import geocode_location  # Reuse existing

load_dotenv()

ORS_API_KEY = os.getenv("ORS_API_KEY")

def get_route(user_lat, user_lon, dest_lat, dest_lon, profile="foot-walking"):
    if not ORS_API_KEY:
        return {"error": "No ORS API key configured"}

    url = "https://api.openrouteservice.org/v2/directions/" + profile + "?api_key=" + ORS_API_KEY

    payload = {
        "coordinates": [[user_lon, user_lat], [dest_lon, dest_lat]],
        "instructions": False,
        "preference": "fastest"
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()

        if "features" not in data or not data["features"]:
            return {"error": "No route found"}

        route = data["features"][0]["properties"]["segments"][0]

        return {
            "duration_min": round(route["duration"] / 60, 1),
            "distance_km": round(route["distance"] / 1000, 2),
            "profile": profile.replace("foot-", "walk").replace("driving-", "drive")
        }
    except Exception as e:
        return {"error": str(e)}

def estimate_fatigue(distance_km, mode="foot-walking", group_type="adults"):
    """
    Returns a fatigue score (0-10) based on distance, mode and group.
    """
    base_fatigue = distance_km * 2 if "walk" in mode else distance_km * 0.5
    
    multiplier = 1.0
    if group_type in ["kids", "elderly"]:
        multiplier = 1.5
        
    score = base_fatigue * multiplier
    return min(round(score, 1), 10)
