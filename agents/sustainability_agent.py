from utils.model_registry import get_active_model_id
import os
from groq import Groq
import json
from dotenv import load_dotenv

load_dotenv()

class SustainabilityAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    def get_sustainability_intel(self, destination, transport_mode="flight", profile=None):
        """
        Provides eco-friendly travel tips contextualized to
        transport mode, travel style, and group size.
        """
        if not destination:
            return {"error": "Missing destination"}

        profile = profile or {}
        group_size = profile.get("travelers", 1)
        duration = profile.get("duration", 3)
        accommodation = profile.get("accommodation", "hotel")
        budget = profile.get("budget", "Moderate")

        prompt = f"""
        You are a Sustainable Travel Advisor providing SPECIFIC, actionable eco-intelligence.

        === TRIP CONTEXT ===
        Destination: {destination}
        Transport: {transport_mode}
        Group Size: {group_size} traveler(s)
        Duration: {duration} days
        Accommodation: {accommodation}
        Budget Tier: {budget}

        === REQUIREMENTS ===
        1. CARBON ESTIMATE: Calculate approximate CO2 for {transport_mode} travel to {destination} for {group_size} people.
        2. ECO TRANSPORT: List SPECIFIC public transit options at {destination} — metro lines, bus apps, bike-share names.
        3. ECO ACCOMMODATION: Suggest SPECIFIC eco-friendly stays matching "{budget}" budget at {destination}.
        4. RESPONSIBLE TOURISM: Specific practices for {destination} — not generic "reduce plastic" advice.
           E.g., "Coral reefs at X beach — don't use chemical sunscreen" or "Buy from local cooperatives at Y market"
        5. CARBON OFFSET: Specific program/organization to offset this trip's emissions with estimated cost.
        6. SUSTAINABLE DINING: Specific restaurants or food practices that support local economy.

        Return VALID JSON ONLY:
        {{
            "carbon_footprint_est": "Estimated CO2 for {group_size} travelers via {transport_mode}",
            "eco_transport": ["Specific transit option with app/card name"],
            "eco_stays": ["Specific eco-friendly accommodation matching {budget} tier"],
            "responsible_practices": ["Specific to {destination}, not generic"],
            "carbon_offset": {{"provider": "Specific org", "est_cost": "Approximate cost to offset"}},
            "sustainable_dining": ["Specific restaurant or food market supporting local economy"],
            "green_rating": "How eco-friendly {destination} is as a destination (High/Medium/Low with reason)"
        }}
        """

        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[
                    {"role": "system", "content": "You are a sustainable travel expert. Give specific names, apps, and places — not generic eco advice."},
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
            
            return {"error": "Could not parse sustainability analysis"}

        except Exception as e:
            return {"error": f"Sustainability analysis failed: {str(e)}"}
