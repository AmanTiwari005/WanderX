from utils.model_registry import get_active_model_id
import os
from groq import Groq
import json
from dotenv import load_dotenv

load_dotenv()

class PackingAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate_packing_list(self, destination, duration, weather_summary, travel_profile):
        """
        Generates a smart, categorized packing list based on trip details.
        """
        if not destination:
            return {"error": "Missing destination"}

        # Extract profile details safely
        gender = travel_profile.get("gender", "gender-neutral") if travel_profile else "gender-neutral"
        trip_type = travel_profile.get("trip_type", "leisure") if travel_profile else "leisure"

        prompt = f"""
        Generate a smart packing list for a {duration}-day trip to {destination}.
        
        Context:
        - Weather: {weather_summary}
        - Trip Type: {trip_type}
        - Traveler: {gender}
        
        Requirements:
        1. Categorize items into: Clothing, Toiletries, Electronics, Documents, Medicine, Miscellaneous.
        2. Highlight 3 "Must Haves" specific to this location/weather (e.g., power adapter type, specific clothing).
        3. Be specific (e.g., instead of "Adapter", say "Type G Adapter").
        
        Return VALID JSON ONLY:
        {{
            "must_haves": ["Item 1", "Item 2", "Item 3"],
            "categories": {{
                "Clothing": ["Item 1", "Item 2"],
                "Toiletries": ["Item 1", "Item 2"],
                "Electronics": ["Item 1", "Item 2"],
                "Documents": ["Item 1", "Item 2"],
                "Medicine": ["Item 1", "Item 2"],
                "Miscellaneous": ["Item 1", "Item 2"]
            }}
        }}
        """

        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            ).choices[0].message.content

            # Clean and parse
            clean_res = res.replace("```json", "").replace("```", "").strip()
            if "{" in clean_res:
                s = clean_res.find("{")
                e = clean_res.rfind("}") + 1
                return json.loads(clean_res[s:e])
            
            return {"error": "Could not parse packing list"}

        except Exception as e:
            return {"error": f"Packing list generation failed: {str(e)}"}
