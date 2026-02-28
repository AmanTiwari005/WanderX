from datetime import datetime

class ContextAgent:
    def __init__(self):
        self.context = {
            "user_profile": {},
            "location": {},
            "weather": {},
            "time": {}
        }

    def build_user_context(self, profile):
        """
        Validates and structures the user profile for other agents.
        """
        # Ensure minimal viable profile
        context = {
            "profile": profile,
            "constraints": {
                "budget": profile.get("budget", "Standard"),
                "pace": profile.get("pace", "Medium"),
                "group_size": profile.get("group_type", "Solo")
            }
        }
        return context

    def build_context(self, user_profile, location, weather_data):
        """
        Aggregates all context sources into a unified dictionary.
        Legacy support for app.py
        """
        self.context["user_profile"] = user_profile or {}
        self.context["location"] = location or {}
        self.context["weather"] = weather_data or {}
        
        # Time Context
        now = datetime.now()
        self.context["time"] = {
            "current_time": now.strftime("%H:%M"),
            "is_weekend": now.weekday() >= 5,
            "hour": now.hour
        }
        
        return self.context

    def get_context_string(self):
        """
        Returns a formatted string of the current context for LLM injection.
        """
        c = self.context
        weather = c.get("weather", {})
        loc = c.get("location", {})
        time = c.get("time", {})
        profile = c.get("user_profile", {})

        return f"""
        [CURRENT CONTEXT]
        - Location: {loc.get('label', 'Unknown')} ({loc.get('lat')}, {loc.get('lon')})
        - Time: {time.get('current_time')} (Hour: {time.get('hour')})
        - Weather: {weather.get('description', 'Unknown')}, Temp: {weather.get('temperature_c')}°C, Rain Prob: {weather.get('rain_probability', 0)}
        - User Constraints: {profile}
        
        CRITICAL: If user specified trip duration, generate itinerary for EXACTLY that many days. 
        Duration from profile: {profile.get('duration', 'Not specified')} days
        """
