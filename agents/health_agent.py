from utils.model_registry import get_active_model_id
import os
from groq import Groq
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class HealthAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    def get_health_intel(self, destination, profile=None, weather_intel=None, news_intel=None):
        """
        Provides health and safety intelligence contextualized to
        travel dates, weather, traveler profile, and active threats.
        """
        if not destination:
            return {"error": "Missing destination"}

        profile = profile or {}
        travel_dates = profile.get("dates", "Not specified")
        group_type = profile.get("group_type", "solo")
        group_size = profile.get("travelers", 1)
        
        # Current month for seasonal health risks
        current_month = datetime.now().strftime("%B")
        current_season = self._get_season(datetime.now().month)

        # Weather context
        weather_str = "Not available"
        if weather_intel and not weather_intel.get("error"):
            temp = weather_intel.get("temp_c", "--")
            condition = weather_intel.get("condition", "Unknown")
            weather_str = f"{condition}, {temp}°C"

        # Active threat extraction from news
        active_threats = "None reported"
        if news_intel and isinstance(news_intel, dict):
            risks = news_intel.get("safety_risks", [])
            if risks:
                active_threats = "; ".join([r.get("title", "") for r in risks[:3]])

        prompt = f"""
        You are a Travel Health Intelligence Agent providing REAL-TIME, season-specific health advice.

        === TRIP CONTEXT ===
        Destination: {destination}
        Travel Dates: {travel_dates}
        Current Month/Season: {current_month} ({current_season})
        Current Weather: {weather_str}
        Group: {group_size} traveler(s), {group_type}
        Active Threats from News: {active_threats}

        === REQUIREMENTS ===
        1. Focus on health risks SPECIFIC to {current_month}/{current_season} at {destination}.
           Example: "February in Thailand = low dengue risk (dry season)" NOT generic "dengue exists in Thailand"
        2. If weather shows extreme heat/cold, provide SPECIFIC precautions.
        3. For "{group_type}" travelers, add relevant advice (children/elderly/pregnancy etc.).
        4. If active threats mention health issues, address them specifically.
        5. Include SPECIFIC hospital/clinic names or areas with good medical facilities.
        6. Mention specific pharmacy chains where tourists can buy medication.
        7. Include COVID/travel health declaration requirements if still active.

        Return VALID JSON ONLY:
        {{
            "seasonal_risks": "Health risks specific to {current_month} at this destination",
            "vaccinations": ["Only vaccines relevant for THIS season and destination"],
            "emergency_numbers": {{"police": "...", "ambulance": "...", "tourist_helpline": "..."}},
            "water_safety": "Specific advice — not just safe/unsafe but which brands to buy, ice safety etc.",
            "medical_facilities": "Specific hospital names and areas with good healthcare",
            "pharmacy_tips": "Specific pharmacy chains and what OTC meds are available",
            "weather_health": "Health precautions for current {weather_str} conditions",
            "group_advice": "Health tips specific to {group_type} travelers",
            "insurance_tip": "Specific travel insurance recommendation for this destination"
        }}
        """

        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[
                    {"role": "system", "content": "You are a travel health expert. Give specific, actionable advice based on current conditions, not generic warnings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            ).choices[0].message.content

            # Clean and parse
            clean_res = res.replace("```json", "").replace("```", "").strip()
            import re
            clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
            if "{" in clean_res:
                s = clean_res.find("{")
                e = clean_res.rfind("}") + 1
                return json.loads(clean_res[s:e])
            
            return {"error": "Could not parse health analysis"}

        except Exception as e:
            return {"error": f"Health analysis failed: {str(e)}"}

    def _get_season(self, month):
        """Returns approximate season for Northern Hemisphere."""
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Autumn"
