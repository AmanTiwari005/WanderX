"""
🍜 AI Food Concierge — Seasonal dishes, trending restaurants, street food alerts.
"""
import json
import logging
from utils.web_search import search_web

logger = logging.getLogger("wanderx.food_agent")


class FoodAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "qwen/qwen3-32b"

    def get_food_intel(self, location, month=None):
        """
        Full food intelligence: seasonal dishes, trending spots, street food, dietary tips.
        """
        try:
            month_str = month or "current season"
            search_results = search_web(f"best food {location} {month_str} seasonal dishes trending restaurants 2025", max_results=8)
            
            prompt = f"""
You are a food travel expert. Based on these search results about {location}, create a comprehensive food guide.

Search Results: {json.dumps(search_results[:5])}

Return ONLY valid JSON:
{{
    "seasonal_dishes": [
        {{ "name": "Dish Name", "description": "Brief description", "where_to_try": "Specific place/area", "price_range": "$-$$$$" }}
    ],
    "trending_restaurants": [
        {{ "name": "Restaurant", "cuisine": "Type", "why_trending": "Reason", "price_range": "$-$$$$" }}
    ],
    "street_food": [
        {{ "name": "Street food item", "area": "Where to find it", "price": "approx cost", "must_try": true }}
    ],
    "dietary_tips": [
        "Tip about local food customs or dietary considerations"
    ],
    "food_neighborhoods": [
        {{ "name": "Neighborhood", "known_for": "What it's famous for", "vibe": "Description" }}
    ]
}}

Include 3-5 items per category. Be specific with real places and dishes.
"""
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            content = res.choices[0].message.content
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            
            return json.loads(content)

        except Exception as e:
            logger.error(f"Food Intel Error: {e}")
            return {"error": str(e)}
