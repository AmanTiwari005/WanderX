import requests

def get_nearby_places(lat, lon, radius=5000, limit=10, pace="Moderate"):
    """
    Get nearby places with dynamic radius based on user pace.
    
    Args:
        lat, lon: Coordinates
        radius: Base radius in meters (will be adjusted by pace)
        limit: Max results
        pace: User's pace preference - "Relaxed", "Moderate", "Fast"
    """
    # Dynamic radius based on pace
    if isinstance(pace, str):
        if "relaxed" in pace.lower():
            radius = 2000  # 2km for relaxed pace
        elif "fast" in pace.lower():
            radius = 10000  # 10km for fast pace
        else:
            radius = 5000  # 5km default for moderate
    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})[tourism];
      node(around:{radius},{lat},{lon})[amenity];
      node(around:{radius},{lat},{lon})[leisure];
    );
    out center {limit};
    """

    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query.encode("utf-8"),
            timeout=20
        )
        data = resp.json()

        places = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            
            # Smart Categorization
            category = "General"
            if "tourism" in tags: category = "Sightseeing"
            if tags.get("amenity") in ["cafe", "restaurant", "bar"]: category = "Food & Drink"
            if tags.get("leisure") in ["park", "garden", "nature_reserve"]: category = "Relax & Nature"
            if tags.get("historic") or "castle" in tags.get("tourism",""): category = "Heritage"
            
            places.append({
                "name": tags.get("name", "Unnamed spot"),
                "lat": elem["lat"],
                "lon": elem["lon"],
                "category": category,
                "type": tags.get("tourism") or tags.get("amenity") or tags.get("leisure") or "place"
            })

        return places[:limit]
    except:
        return []

def get_utility_places(lat, lon, category="atm", radius=3000, limit=5):
    """
    Search for utility places (ATM, Pharmacy, EV Charging) for emergency needs.
    
    Args:
        lat, lon: Coordinates
        category: "atm", "pharmacy", "charging_station", "hospital"
        radius: Search radius in meters (default 3km)
        limit: Max results
    
    Returns:
        List of utility places with name, location, and type
    """
    # Map categories to OSM tags
    category_tags = {
        "atm": "amenity=atm",
        "pharmacy": "amenity=pharmacy",
        "charging_station": "amenity=charging_station",
        "hospital": "amenity=hospital",
        "fuel": "amenity=fuel"
    }
    
    tag = category_tags.get(category, "amenity=atm")
    
    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})[{tag}];
    );
    out center {limit};
    """
    
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query.encode("utf-8"),
            timeout=20
        )
        data = resp.json()
        
        places = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            places.append({
                "name": tags.get("name", f"{category.upper()} location"),
                "lat": elem["lat"],
                "lon": elem["lon"],
                "category": category.upper(),
                "type": category,
                "operator": tags.get("operator", "Unknown")
            })
        
        return places[:limit]
    except:
        return []