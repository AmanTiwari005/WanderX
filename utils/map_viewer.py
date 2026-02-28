import folium
from streamlit_folium import st_folium
import streamlit as st


def create_route_map(origin_coords, destination_coords, route_waypoints=None, zoom_start=12):
    """
    Creates an interactive map showing the route from origin to destination.
    
    Args:
        origin_coords: Tuple (lat, lon) for starting point
        destination_coords: Tuple (lat, lon) for ending point
        route_waypoints: Optional list of (lat, lon) waypoints along the route
        zoom_start: Initial zoom level
    
    Returns:
        folium.Map object
    """
    # Calculate center point
    center_lat = (origin_coords[0] + destination_coords[0]) / 2
    center_lon = (origin_coords[1] + destination_coords[1]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap"
    )
    
    # Add origin marker
    folium.Marker(
        origin_coords,
        popup="Start",
        tooltip="Starting Point",
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(m)
    
    # Add destination marker
    folium.Marker(
        destination_coords,
        popup="Destination",
        tooltip="Your Destination",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa")
    ).add_to(m)
    
    # Draw route line
    if route_waypoints:
        folium.PolyLine(
            route_waypoints,
            color="blue",
            weight=4,
            opacity=0.7
        ).add_to(m)
    else:
        # Simple direct line if no waypoints
        folium.PolyLine(
            [origin_coords, destination_coords],
            color="blue",
            weight=4,
            opacity=0.7,
            dash_array="10"
        ).add_to(m)
    
    return m


def create_destination_map(locations, pois=None, suggestions=None, zoom_start=12):
    """
    Creates a map with destination markers and optional POIs.
    """
    if not locations:
        return None
    
    # Center on first location
    center = locations[0]['coords']
    
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="OpenStreetMap"
    )
    
    # Main Destination Markers
    for loc in locations:
        folium.Marker(
            loc['coords'],
            popup=f"<b>{loc['name']}</b><br>{loc.get('description', '')}",
            tooltip=loc['name'],
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)

    # POI Layers
    if pois:
        # Pous structure: {"Category": [{"lat": x, "lon": y, "name": "z"}, ...]}
        for category, items in pois.items():
            fg = folium.FeatureGroup(name=category)
            
            # Icon mapping
            icon_name = "info-sign"
            color = "blue"
            if category == "Food & Drink": icon_name, color = "cutlery", "orange"
            elif category == "Sightseeing": icon_name, color = "camera", "purple"
            elif category == "Relax & Nature": icon_name, color = "tree", "green"
            elif category == "Hotels": icon_name, color = "bed", "darkblue"
            
            for item in items:
                folium.Marker(
                    location=(item['lat'], item['lon']),
                    popup=f"<b>{item['name']}</b>",
                    tooltip=f"{category}: {item['name']}",
                    icon=folium.Icon(color=color, icon=icon_name, prefix="fa")
                ).add_to(fg)
            
            fg.add_to(m)
            
        folium.LayerControl().add_to(m)
        
    # Suggestions Layer (Distinct Pins)
    if suggestions:
        fg_sugg = folium.FeatureGroup(name="Smart Suggestions")
        for item in suggestions:
            if item.get('lat') and item.get('lon'):
                folium.Marker(
                location=(item['lat'], item['lon']),
                popup=f"<b>✨ {item['name']}</b><br>{item.get('description', 'Recommended for you')}",
                tooltip=f"Suggestion: {item['name']}",
                icon=folium.Icon(color="green", icon="star", prefix="fa")
            ).add_to(fg_sugg)
        fg_sugg.add_to(m)
    
    return m


def create_itinerary_map(destination_coords, destination_name, num_days, zoom_start=12):
    """
    Creates a map with day-number pins for a multi-day itinerary.
    Useful for visualizing daily activities around a destination.
    
    Args:
        destination_coords: Tuple (lat, lon) for destination center
        destination_name: Name of the destination
        num_days: Number of days in the itinerary
        zoom_start: Initial zoom level
    
    Returns:
        folium.Map object
    """
    # Handle dictionary input (e.g., from geocode_location)
    if isinstance(destination_coords, dict):
        lat = destination_coords.get("lat")
        lon = destination_coords.get("lon")
        if lat is not None and lon is not None:
             destination_coords = (lat, lon)
        else:
             # Fallback or error handling if lat/lon missing
             st.error(f"Invalid coordinate format: {destination_coords}")
             return None

    m = folium.Map(
        location=destination_coords,
        zoom_start=zoom_start,
        tiles="OpenStreetMap"
    )
    
    # Add a central marker for the destination
    folium.Marker(
        destination_coords,
        popup=f"<b>{destination_name}</b><br>Main Destination",
        tooltip=destination_name,
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)
    
    # Add numbered day markers in a circular pattern (simulated locations)
    # In a real implementation, these would be geocoded from the itinerary
    import math
    radius = 0.02  # Approx 2km offset
    
    for day in range(1, num_days + 1):
        angle = (2 * math.pi / num_days) * (day - 1)
        lat_offset = radius * math.cos(angle)
        lon_offset = radius * math.sin(angle)
        
        day_coords = (
            destination_coords[0] + lat_offset,
            destination_coords[1] + lon_offset
        )
        
        # Create a custom HTML icon with day number
        html = f"""
        <div style="
            background-color: #4285F4;
            border: 2px solid white;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        ">{day}</div>
        """
        
        folium.Marker(
            day_coords,
            popup=f"<b>Day {day}</b><br>Explore this area",
            tooltip=f"Day {day}",
            icon=folium.DivIcon(html=html)
        ).add_to(m)
    
    return m


def render_map_in_streamlit(folium_map, height=400):
    """
    Renders a folium map in Streamlit.
    
    Args:
        folium_map: folium.Map object
        height: Height of the map in pixels
    
    Returns:
        Map data from user interactions
    """
    return st_folium(folium_map, width=700, height=height)
