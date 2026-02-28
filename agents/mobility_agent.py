import requests
import os
from dotenv import load_dotenv

load_dotenv()

class MobilityAgent:
    def __init__(self):
        self.ors_api_key = os.getenv("ORS_API_KEY")

    def get_mobility_intel(self, origin_coords, dest_coords, mode="driving"):
        """
        Calculates route and travel time.
        """
        if not origin_coords or not dest_coords:
            return {"error": "Missing coordinates"}
            
        route = self._get_route(
            origin_coords["lat"], origin_coords["lon"],
            dest_coords["lat"], dest_coords["lon"],
            mode
        )
        
        # Add transport options if route found
        transport_options = []
        if "distance_km" in route:
             transport_options = self._get_all_transport_options(route["distance_km"])

        return {
            "distance_km": route.get("distance_km"),
            "duration_h": route.get("duration_hours"),
            "route_geometry": route.get("geometry"),
            "transport_options": transport_options
        }

    def _get_route(self, user_lat, user_lon, dest_lat, dest_lon, profile="foot-walking"):
        if not self.ors_api_key:
            return {"error": "No ORS API key configured"}

        # Map generic modes to ORS profiles if needed
        ors_profile = profile
        if profile == "driving": ors_profile = "driving-car"
        elif profile == "walking": ors_profile = "foot-walking"

        url = "https://api.openrouteservice.org/v2/directions/" + ors_profile + "?api_key=" + self.ors_api_key

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
                "duration_hours": round(route["duration"] / 3600, 2), # Converted to hours for agent
                "duration_min": round(route["duration"] / 60, 1),
                "distance_km": round(route["distance"] / 1000, 2),
                "geometry": data["features"][0]["geometry"]["coordinates"], # Added geometry
                "profile": ors_profile
            }
        except Exception as e:
            return {"error": str(e)}

    def _estimate_fatigue(self, distance_km, mode="foot-walking", group_type="adults"):
        """
        Returns a fatigue score (0-10) based on distance, mode and group.
        """
        base_fatigue = distance_km * 2 if "walk" in mode else distance_km * 0.5
        
        multiplier = 1.0
        if group_type in ["kids", "elderly"]:
            multiplier = 1.5
            
        score = base_fatigue * multiplier
        return min(round(score, 1), 10)

    def _estimate_transport_cost(self, distance_km, mode="auto", budget_tier="Mid-Range"):
        """
        Estimates transport cost in INR.
        """
        costs = {}
        
        # Auto-rickshaw rates
        if mode == "auto":
            base_fare = 25
            per_km = 12 if budget_tier == "Budget (₹ Low)" else 15
            total = max(base_fare, distance_km * per_km)
            costs = {
                "mode": "Auto-rickshaw",
                "estimated_cost": round(total, 2),
                "currency": "INR",
                "breakdown": f"₹{per_km}/km × {distance_km}km"
            }
        
        # Taxi/Cab rates
        elif mode == "taxi":
            base_fare = 40
            per_km = 18 if budget_tier == "Budget (₹ Low)" else 25
            total = max(base_fare, distance_km * per_km)
            costs = {
                "mode": "Taxi/Cab",
                "estimated_cost": round(total, 2),
                "currency": "INR",
                "breakdown": f"₹{per_km}/km × {distance_km}km"
            }
        
        # Metro
        elif mode == "metro":
            if distance_km < 2: fare = 10
            elif distance_km < 5: fare = 20
            elif distance_km < 10: fare = 30
            elif distance_km < 15: fare = 40
            else: fare = 60
            
            costs = {
                "mode": "Metro",
                "estimated_cost": fare,
                "currency": "INR",
                "breakdown": f"Zone-based fare (~{distance_km}km)"
            }
        
        # Bus
        elif mode == "bus":
            if distance_km < 5: fare = 10
            elif distance_km < 15: fare = 20
            else: fare = 30
            
            costs = {
                "mode": "Bus",
                "estimated_cost": fare,
                "currency": "INR",
                "breakdown": f"Flat fare for ~{distance_km}km"
            }
        
        # Walking
        elif mode == "walk":
            costs = {
                "mode": "Walking",
                "estimated_cost": 0,
                "currency": "INR",
                "breakdown": f"Free • ~{distance_km * 12} min"
            }
        
        else:
            costs = {
                "mode": "Unknown",
                "estimated_cost": 0,
                "currency": "INR",
                "breakdown": "No fare data"
            }
        
        return costs

    def _get_all_transport_options(self, distance_km, budget_tier="Mid-Range"):
        """
        Returns cost estimates for all available transport modes.
        """
        modes = ["walk", "bus", "metro", "auto", "taxi"]
        options = []
        
        for mode in modes:
            if distance_km < 1 and mode in ["metro", "bus"]: continue
            if distance_km > 5 and mode == "walk": continue
            
            cost_data = self._estimate_transport_cost(distance_km, mode, budget_tier)
            options.append(cost_data)
        
        options.sort(key=lambda x: x["estimated_cost"])
        return options
