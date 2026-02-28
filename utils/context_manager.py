from datetime import datetime

class ContextManager:
    def __init__(self):
        self.context = {
            "user_profile": {},
            "location": {},
            "weather": {},
            "time": {}
        }

    def build_context(self, user_profile, location, weather_data):
        """
        Aggregates all context sources into a unified dictionary.
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
        - User Constriants: {profile}
        """
