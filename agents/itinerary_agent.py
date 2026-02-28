from utils.model_registry import get_active_model_id, get_complex_task_model_id
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class ItineraryAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client or Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Use stronger model for complex JSON generation
        self.model = get_complex_task_model_id()

    def generate_itinerary(self, destination, duration=1, context=None, profile=None):
        """
        Generates a deeply detailed multi-day itinerary enriched with full context.
        Each time slot is a structured object with activity, location, duration, cost, and tips.
        """
        if not destination:
            return {"error": "Missing destination"}
            
        # ── Build Rich Context String ──
        ctx_str = f"Destination: {destination}\nDuration: {duration} days"
        
        # Profile Info
        if profile:
            if profile.get("budget"):
                ctx_str += f"\nBudget Tier: {profile['budget']}"
            if profile.get("interests"):
                ctx_str += f"\nInterests: {profile['interests']}"
            if profile.get("group_type"):
                ctx_str += f"\nTravelers: {profile['group_type']}"
            if profile.get("dates"):
                ctx_str += f"\nTravel Dates: {profile['dates']}"
            if profile.get("pace"):
                ctx_str += f"\nPace: {profile['pace']}"
        
        # Context Intel
        if context:
            # Weather
            weather = context.get("weather_intel") or context.get("weather")
            if isinstance(weather, dict):
                wd = weather.get("weather_data", weather)
                ctx_str += f"\nWeather: {wd.get('condition', wd.get('weather', 'Unknown'))}"
                if wd.get("temperature_c"):
                    ctx_str += f", {wd['temperature_c']}°C"
            elif weather:
                ctx_str += f"\nWeather: {weather}"
            
            # Risk / Safety
            risk = context.get("risk_assessment") or context.get("risk")
            if isinstance(risk, dict):
                ctx_str += f"\nSafety: {risk.get('verdict', 'Unknown')} (Score: {risk.get('total_risk_score', 0)}/100)"
                factors = risk.get("risk_factors", [])
                if factors:
                    ctx_str += f"\nRisk Factors: {json.dumps(factors)}"
            
            # Active Threats
            news = context.get("news_intel")
            if isinstance(news, dict):
                threats = news.get("safety_risks", [])
                if threats:
                    threat_list = "; ".join([f"{t.get('title','')}: {t.get('summary','')}" for t in threats[:3]])
                    ctx_str += f"\n⚠️ ACTIVE THREATS: {threat_list}"
                opps = news.get("opportunities", [])
                if opps:
                    opp_list = "; ".join([f"{o.get('title','')}" for o in opps[:3]])
                    ctx_str += f"\n🎉 LOCAL EVENTS: {opp_list}"
            
            # Budget Intel
            budget_intel = context.get("budget_intel")
            if isinstance(budget_intel, dict) and not budget_intel.get("error"):
                ctx_str += f"\nBudget Feasibility: {budget_intel.get('feasibility', 'Unknown')}"
                ctx_str += f"\nEstimated Daily Budget: {budget_intel.get('daily_needed', '--')}"
            
            # Health Intel
            health = context.get("health_intel")
            if isinstance(health, dict) and not health.get("error"):
                ctx_str += f"\nWater Safety: {health.get('water_safety', 'Check locally')}"
            
            # Crowd Intel
            crowd = context.get("crowd_intel")
            if isinstance(crowd, dict) and not crowd.get("error"):
                ctx_str += f"\nCrowd Level: {crowd.get('crowd_level', 'Moderate')}"

        # ─── NEW: Intelligent Constraints ───
        special_constraints = []
        
        # 1. Pacing Rules
        pace = (profile or {}).get("pace", "Moderate")
        if pace == "Relaxed":
            special_constraints.append("PACING: RELAXED. Start days after 10 AM. Max 2 main activities per day. Allow 2-hour leisurely lunches. No rushing.")
        elif pace == "Fast":
            special_constraints.append("PACING: FAST. Start by 8 AM. Pack in as much as possible. Minimize transit time.")
        else:
            special_constraints.append("PACING: MODERATE. Balanced itinerary. Start around 9 AM.")
        
        # 2. Weather Contingency
        weather_intel = context.get("weather_intel") or {}
        is_rainy = False
        if isinstance(weather_intel, dict):
             wd = weather_intel.get("weather_data", weather_intel)
             cond = wd.get("condition", "").lower() if isinstance(wd, dict) else str(wd).lower()
             if "rain" in cond or "storm" in cond or "shower" in cond or "snow" in cond:
                 is_rainy = True
        
        if is_rainy:
            special_constraints.append("WEATHER ALERT: Precipitation predicted. You MUST prioritize Indoor Activities (Museums, Malls, Cafes). For every outdoor stop, provide a specific Indoor Backup plan.")

        # 3. Live Events
        news_intel = context.get("news_intel") or {}
        if isinstance(news_intel, dict):
            events = news_intel.get("opportunities", [])
            if events:
                for cal_event in events[:2]: # Top 2 events
                    title = cal_event.get('title', 'Event')
                    summary = cal_event.get('summary', '')
                    special_constraints.append(f"LIVE EVENT: You MUST try to include '{title}' ({summary}) in the plan if dates/timings align.")

        constraints_str = "\n".join([f"           - {c}" for c in special_constraints])

        # ── Build Enriched Prompt ──
        budget_label = (profile or {}).get("budget", "Moderate")
        group_label = (profile or {}).get("group_type", "Solo traveler")
        
        prompt = f"""
        Create a DEEPLY DETAILED {duration}-day travel itinerary for {destination}.
        This is the user's PRIMARY TRIP PLANNER — make it comprehensive and actionable.
        
        === FULL CONTEXT ===
        {ctx_str}
        
        === CRITICAL CONSTRAINTS (MUST FOLLOW) ===
        1. **INTERESTS**: The itinerary MUST strictly and heavily focus on: {profile.get('interests', 'General Highlights')}.
           - Tailor the entire experience to these specific interests.
        2. **BUDGET & CURRENCY**: User is on a {budget_label} budget.
           - Provide REALISTIC cost estimates ONLY IN INDIAN RUPEES (INR) (symbol: ₹). Do not use USD, EUR, or local currency.
        3. **GROUP**: Traveling as: {group_label}.
           - Absolutely ensure experiences, logistics, and pacing are perfect for {group_label}.
        4. **INTELLIGENT ADJUSTMENTS (Real-Time Alerts & Weather)**:
{constraints_str}
        5. **FASCINATING FACTS & REFINEMENT**: Add AS MANY fascinating historical, cultural, and local facts as possible to refine the plan. Prove your deep local expertise and tie facts directly to the user's interests.
        
        === DETAIL REQUIREMENTS ===
        Each time slot (morning, lunch, afternoon, evening) must be a STRUCTURED OBJECT with:
        - "preview_desc": A detailed 25-40 word summary of the activity highlighting what makes it special and why it was chosen.
        - "activity": A MASSIVELY DETAILED 100-150 word deep-dive description. It MUST organically include multiple fascinating facts, tell a story, and directly cater to the user's interests, group type, and real-time alerts.
        - "location": Specific area/neighborhood/address in {destination}
        - "duration": Estimated time needed (e.g. "2-3 hours")
        - "cost": Estimated cost per person strictly in INR (e.g. "₹500")
        - "transport": How to get there from previous activity (e.g. "10 min walk", "Metro Line 2", "Grab/taxi ~₹200")
        - "insider_tip": One specific pro-tip only a local would know (not generic advice)
        
        === QUALITY RULES ===
        1. SPECIFIC PLACES: Use real venue/restaurant/attraction names.
        2. GEOGRAPHICAL FLOW: Activities within each day should be in the same area to minimize travel.
        3. DAY TITLES: Use consistent, thematic titles (e.g., "Day 1: Historical Kyoto", NOT just "Day 1").
        4. ALTERNATIVES: Each day should have a backup plan.
        
        Return VALID JSON ONLY:
        {{
            "day_1": {{
                "title": "Day 1: [Thematic Title]",
                "morning": {{
                    "preview_desc": "Detailed 25-40 word summary for preview",
                    "activity": "Massively detailed 100-150 word activity description with specific venue name, deep storytelling, constraints adherence, and fascinating facts.",
                    "location": "Specific neighborhood/area",
                    "duration": "2-3 hours",
                    "cost": "~₹500/person",
                    "transport": "How to get here from hotel",
                    "insider_tip": "Specific local pro-tip"
                }},
                "lunch": {{
                    "preview_desc": "Detailed 25-40 word summary of lunch",
                    "activity": "Massively detailed 100-150 word description of specific restaurant, dish history, and why it fits the user.",
                    "location": "Area name",
                    "duration": "1-1.5 hours",
                    "cost": "~₹300/person",
                    "transport": "5 min walk from morning activity",
                    "insider_tip": "Must-try dish"
                }},
                "afternoon": {{ ... }},
                "evening": {{ ... }},
                "estimated_cost": "Total range for this day per person",
                "safety_note": "Any relevant safety info",
                "group_tip": "Tip specific to {group_label}",
                "backup_plan": "Alternative activity"
            }},
            "day_2": {{...}}
        }}
        
        Generate ALL {duration} days. DO NOT skip any day.
        """
        
        try:
            res = self.client.chat.completions.create(
                model=get_active_model_id(),
                messages=[
                    {"role": "system", "content": "You are an expert local travel guide. Generate deeply detailed, actionable itineraries with specific venue names, costs, and insider tips. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=8000
            ).choices[0].message.content
            
            # Clean response
            clean_res = res.strip()
            clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
            
            if "{" in clean_res and "}" in clean_res:
                s = clean_res.find("{")
                e = clean_res.rfind("}") + 1
                clean_res = clean_res[s:e]
                
            return json.loads(clean_res)
            
        except Exception as e:
            print(f"Itinerary Gen Error: {e}")
            return self._get_fallback(destination, duration)

    def _get_fallback(self, destination, duration):
        return {
            f"day_{i+1}": {
                "title": f"Explore {destination} Day {i+1}",
                "morning": {"activity": "Visit city center", "location": "City center", "duration": "2-3 hours", "cost": "Varies", "transport": "Taxi/walk", "insider_tip": "Go early to avoid crowds"},
                "lunch": {"activity": "Local restaurant", "location": "Near morning activity", "duration": "1 hour", "cost": "$$", "transport": "Walk", "insider_tip": "Ask locals for recommendations"},
                "afternoon": {"activity": "Museum or Park", "location": "City area", "duration": "2-3 hours", "cost": "Varies", "transport": "Short taxi/walk", "insider_tip": "Check opening hours"},
                "evening": {"activity": "Dinner at popular spot", "location": "Dining district", "duration": "2 hours", "cost": "$$", "transport": "Taxi", "insider_tip": "Reserve ahead if possible"},
                "estimated_cost": "Varies",
                "safety_note": "Check local conditions",
                "group_tip": "Suitable for all",
                "backup_plan": "Indoor museum or shopping mall"
            } for i in range(duration)
        }
