from utils.model_registry import get_active_model_id
import os
from groq import Groq
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class CulturalAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    def get_cultural_intel(self, destination, profile=None):
        """
        Provides cultural insights contextualized to travel dates,
        group type, and planned interests.
        """
        if not destination:
            return {"error": "Missing destination"}

        profile = profile or {}
        travel_dates = profile.get("dates", "Not specified")
        group_type = profile.get("group_type", "solo")
        interests = profile.get("interests", [])
        
        current_month = datetime.now().strftime("%B %Y")

        prompt = f"""
        You are a Cultural Intelligence Agent providing SPECIFIC, date-aware cultural advice.

        === TRIP CONTEXT ===
        Destination: {destination}
        Travel Dates: {travel_dates}
        Current Month: {current_month}
        Group Type: {group_type}
        Interests: {', '.join(interests) if interests else 'General sightseeing'}

        === REQUIREMENTS ===
        1. FESTIVALS & EVENTS: List festivals/events happening AT or NEAR {destination} during {travel_dates or current_month}. 
           Be specific with dates, not generic festivals that happen year-round.
        2. ETIQUETTE: Tailor do's and don'ts to what a "{group_type}" group would actually encounter.
           E.g., family with kids at temples vs. solo backpacker at nightlife.
        3. LANGUAGE: Include phrases relevant to the traveler's interests ({', '.join(interests) if interests else 'general tourism'}).
        4. LOCAL LAWS: Focus on laws that TOURISTS commonly violate unknowingly.
        5. DRESS CODE: Be specific about what to wear for the CURRENT WEATHER/SEASON, not generic advice.
        6. TIPPING: Give specific amounts (not just percentages) in LOCAL CURRENCY.
        7. SCAM AWARENESS: Common tourist scams at this specific destination.

        Return VALID JSON ONLY:
        {{
            "current_festivals": [
                {{"name": "Festival name", "dates": "Specific dates", "description": "Brief and why it matters for travelers", "location": "Where in {destination}"}}
            ],
            "etiquette_dos": ["Specific tip relevant to {group_type} travelers"],
            "etiquette_donts": ["Specific mistake {group_type} travelers commonly make"],
            "language_tips": [
                {{"phrase": "Useful phrase", "local": "Translation", "pronunciation": "Phonetic", "when_to_use": "Specific situation"}}
            ],
            "tipping_guide": {{
                "restaurants": "Specific amount in local currency",
                "taxis": "Specific amount",
                "hotels": "Specific amount",
                "general": "Overall tipping culture summary"
            }},
            "dress_code": "Season-appropriate dress advice for {current_month}",
            "local_laws": ["Law that tourists commonly violate"],
            "scam_alerts": ["Common tourist scam with how to avoid it"]
        }}
        """

        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[
                    {"role": "system", "content": "You are a local cultural expert. Give specific, current advice — not Wikipedia summaries. Include actual dates for festivals and amounts in local currency for tipping."},
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
            
            return {"error": "Could not parse cultural analysis"}

        except Exception as e:
            return {"error": f"Cultural analysis failed: {str(e)}"}
