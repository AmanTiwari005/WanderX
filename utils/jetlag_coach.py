"""
🧳 Jet Lag Coach — Sleep/caffeine schedule based on timezone difference.
"""
import json
import logging

logger = logging.getLogger("wanderx.jetlag_coach")


def generate_jetlag_plan(client, origin, destination, travel_date=None):
    """
    Generates a personalized jet lag recovery plan.
    """
    try:
        prompt = f"""
You are a sleep scientist and travel wellness expert. Create a jet lag recovery plan.

Origin: {origin}
Destination: {destination}
Travel Date: {travel_date or "upcoming"}

Return ONLY valid JSON:
{{
    "timezone_difference": "+/- hours",
    "severity": "Mild/Moderate/Severe",
    "direction": "Eastward/Westward",
    "pre_flight": [
        {{ "day": "2 days before", "sleep_advice": "Go to bed 1 hour earlier", "caffeine": "Stop caffeine after 2pm", "light": "Get morning sunlight" }}
    ],
    "flight_day": {{
        "sleep_on_plane": true,
        "when_to_sleep": "Specific timing advice",
        "hydration": "Water intake advice",
        "meal_timing": "When to eat on the plane"
    }},
    "post_arrival": [
        {{ "day": "Day 1", "wake_time": "7:00 AM local", "sleep_time": "10:00 PM local", "caffeine_window": "Before 1 PM only", "activity": "Light outdoor walk", "key_tip": "Specific tip" }}
    ],
    "quick_tips": [
        "Tip 1",
        "Tip 2", 
        "Tip 3"
    ],
    "recovery_days": 3
}}

Include 2 pre-flight days and 3 post-arrival days. Be specific with timings.
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Jet Lag Coach Error: {e}")
        return {"error": str(e)}
