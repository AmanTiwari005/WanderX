from utils.model_registry import get_active_model_id
import os
from groq import Groq
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class BudgetAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    def get_budget_intel(self, destination, budget_str, duration_days=3, profile=None, weather_intel=None):
        """
        Analyzes budget feasibility with real-time context:
        travel dates, group size, weather, and user budget tier.
        """
        if not destination or not budget_str:
            return {"error": "Missing destination or budget info"}

        # Extract real-time context
        profile = profile or {}
        group_size = profile.get("travelers", profile.get("group_size", 1))
        group_type = profile.get("group_type", "solo")
        travel_dates = profile.get("dates", "Not specified")
        interests = profile.get("interests", [])

        # Weather context for activity-appropriate budgeting
        weather_str = "Not available"
        if weather_intel and not weather_intel.get("error"):
            temp = weather_intel.get("temp_c", "--")
            condition = weather_intel.get("condition", "Unknown")
            weather_str = f"{condition}, {temp}°C"

        # Current month for seasonality
        current_month = datetime.now().strftime("%B %Y")

        prompt = f"""
        You are a REAL-TIME Travel Budget Analyst. Provide specific, actionable budget intelligence.

        === TRIP DETAILS ===
        Destination: {destination}
        Duration: {duration_days} days
        Budget: {budget_str} (total for entire trip)
        Group: {group_size} traveler(s), {group_type}
        Travel Dates: {travel_dates}
        Current Month: {current_month}
        Weather: {weather_str}
        Interests: {', '.join(interests) if interests else 'General sightseeing'}

        === REQUIREMENTS ===
        1. Give costs strictly in INDIAN RUPEES (INR) (symbol: ₹) regardless of destination. Do not use USD, EUR, or local currency. Convert all prices to INR.
        2. Factor in SEASONAL pricing — is this peak/off-peak/shoulder season? How does that affect prices?
        3. Provide PER-PERSON costs (since there are {group_size} travelers).
        4. Match recommendations to the "{budget_str}" budget tier specifically.
        5. Include 3 SPECIFIC money-saving tips that work RIGHT NOW at this destination (not generic advice).
        6. If weather is poor, suggest budget-friendly indoor alternatives.
        7. Mention specific neighborhoods/areas that are budget-friendly vs tourist-trap expensive.

        Return VALID JSON ONLY:
        {{
            "feasibility": "Comfortable" | "Tight" | "Insufficient",
            "daily_needed": "Specific amount per person per day in INR (e.g., ₹5000)",
            "season_impact": "How current season affects prices (e.g. 'Peak season — hotels 40% above average')",
            "breakdown": {{
                "accommodation": "Specific nightly cost range for {budget_str} tier",
                "food": "Daily food cost with specific cheap eat areas",
                "transport": "Daily transport with specific options (metro pass, grab, etc.)",
                "activities": "Daily activity cost with specific {budget_str}-appropriate attractions"
            }},
            "tips": ["Specific actionable tip 1", "Specific actionable tip 2", "Specific actionable tip 3"],
            "budget_areas": "Neighborhoods/areas that match this budget tier",
            "splurge_worthy": "One experience worth spending extra on at this destination"
        }}
        """

        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[
                    {"role": "system", "content": "You are a precise travel budget analyst. Give specific numbers, not ranges when possible. Use Indian Rupees (INR) for all costs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            ).choices[0].message.content

            # Clean and parse
            clean_res = res.replace("```json", "").replace("```", "").strip()
            # Remove thinking tags if present
            import re
            clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
            if "{" in clean_res:
                s = clean_res.find("{")
                e = clean_res.rfind("}") + 1
                return json.loads(clean_res[s:e])
            
            return {"error": "Could not parse budget analysis"}

        except Exception as e:
            return {"error": f"Budget analysis failed: {str(e)}"}
