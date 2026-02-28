from utils.model_registry import get_active_model_id, get_complex_task_model_id
import os
import json
import logging
from utils.llm_client import call_llm_json

logger = logging.getLogger("wanderx.recommendation_agent")


class RecommendationAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = get_complex_task_model_id()



    def generate_recommendation(
        self, 
        user_context, 
        risk_assessment, 
        weather_intel, 
        news_intel, 
        suggestions,
        user_query="What should I do?",
        budget_intel=None,
        cultural_intel=None,
        health_intel=None,
        sustainability_intel=None,
        itinerary=None,
        conversation_history=None,
        live_pulse_intel=None # NEW ARGUMENT
    ):
        """
        Synthesizes ALL agent intel into a final recommendation.
        If 'itinerary' is provided (from ItineraryAgent), forces alignment.
        """
        dest = user_context.get("destination", "Unknown Destination")
        
        # EXTRACT DURATION FOR STRICT COMPLIANCE
        trip_duration = user_context.get("duration", 3)
        try:
            trip_duration = int(str(trip_duration).split()[0])
        except Exception:
            trip_duration = 3
            
        chosen_stay = user_context.get("accommodation", "Central Location")
        budget_str = user_context.get("budget", "Moderate")
        
        # Build comprehensive intel summary
        intel_sections = []
        
        # Core intel (always available)
        intel_sections.append(
            f"RISK ASSESSMENT: {risk_assessment.get('verdict', 'Unknown')} "
            f"(Score: {risk_assessment.get('total_risk_score', 0)})\n"
            f"RISK FACTORS: {json.dumps(risk_assessment.get('risk_factors', []))}"
        )
        intel_sections.append(
            f"WEATHER: {weather_intel.get('condition', 'Unknown')} "
            f"({weather_intel.get('temp_c', '--')}°C)"
        )
        intel_sections.append(f"NEWS: {json.dumps(news_intel) if news_intel else 'No alerts'}")
        intel_sections.append(f"SUGGESTED ACTIONS: {json.dumps(suggestions) if suggestions else '[]'}")
        
        # Deep intelligence (new — connected from other agents)
        # CRITICAL: Put Itinerary FIRST to ensure it is never truncated
        if itinerary and not itinerary.get("error"):
            # Only include a compact summary to save tokens — the full itinerary is in the sidebar
            itin_days = sorted([k for k in itinerary.keys() if k.startswith("day_")])
            if itin_days:
                trip_duration = len(itin_days) # Force alignment with actual itinerary length
            
            # extract summaries only
            itin_summary_dict = {}
            for k, v in itinerary.items():
                if k.startswith("day_") and isinstance(v, dict):
                    itin_summary_dict[k] = {
                        "title": v.get("title"),
                        "summary": v.get("summary", "See detailed itinerary")
                    }

            intel_sections.append(
                f"=== EXISTING ITINERARY (SOURCE OF TRUTH) ===\n"
                f"You MUST use these summaries for the preview:\n" + 
                json.dumps(itin_summary_dict, indent=2)
            )

        if budget_intel and not budget_intel.get("error"):
            intel_sections.append(
                f"BUDGET ANALYSIS: Feasibility={budget_intel.get('feasibility', 'Unknown')}, "
                f"Daily needed={budget_intel.get('daily_needed', '--')}, "
                f"Tips: {json.dumps(budget_intel.get('tips', []))}"
            )
        
        if cultural_intel and not cultural_intel.get("error"):
            intel_sections.append(
                f"CULTURAL TIPS: Do's={json.dumps(cultural_intel.get('etiquette_dos', []))}, "
                f"Don'ts={json.dumps(cultural_intel.get('etiquette_donts', []))}, "
                f"Dress code={cultural_intel.get('dress_code', 'Standard')}, "
                f"Tipping={cultural_intel.get('tipping_guide', 'Standard')}"
            )
        
        if health_intel and not health_intel.get("error"):
            intel_sections.append(
                f"HEALTH ADVISORY: Water={health_intel.get('water_safety', 'Check locally')}, "
                f"Vaccinations={json.dumps(health_intel.get('vaccinations', []))}"
            )
        
        if sustainability_intel and not sustainability_intel.get("error"):
            intel_sections.append(
                f"ECO INFO: Carbon={sustainability_intel.get('carbon_footprint_est', '--')}, "
                f"Green rating={sustainability_intel.get('green_rating', 'Moderate')}"
            )

        # LIVE PULSE INTEL (Events & Vibe)
        if live_pulse_intel and not live_pulse_intel.get("error"):
            intel_sections.append(
                f"🔴 LIVE PULSE INTELLIGENCE (REAL-TIME):\n"
                f"EVENTS: {json.dumps(live_pulse_intel.get('events', []))}\n"
                f"TRENDING SPOTS: {json.dumps(live_pulse_intel.get('trends', []))}\n"
                f"VIBE CHECK: {json.dumps(live_pulse_intel.get('vibe', {}))}"
            )
        
        full_intel = "\n\n".join(intel_sections)
        # TRUNCATE INTEL to avoid Rate Limit Errors (approx 3500 tokens max for intel)
        if len(full_intel) > 15000: 
            full_intel = full_intel[:15000] + "... [TRUNCATED DUE TO SIZE]"
        
        # Extract travelers / group type
        group_type = user_context.get("group_type", "Solo traveler")
        travel_dates = user_context.get("dates", "Not specified")
        
        # Extract active threat summary for itinerary awareness
        active_threats_summary = "None reported"
        if news_intel and isinstance(news_intel, dict):
            threats = news_intel.get("safety_risks", [])
            if threats:
                active_threats_summary = "; ".join(
                    [f"{t.get('title','')}: {t.get('summary','')}" for t in threats[:3]]
                )
        
        # Extract safety status
        safety_verdict = "Unknown"
        risk_score = 0
        if risk_assessment and isinstance(risk_assessment, dict):
            safety_verdict = risk_assessment.get("verdict", "Unknown")
            risk_score = risk_assessment.get("total_risk_score", 0)
        
        # Determine extra instructions if itinerary is present
        itin_instruction = ""
        if itinerary and not itinerary.get("error"):
            itin_instruction = f"CRITICAL: You are provided with an EXISTING ITINERARY in the context. You MUST generate the 'itinerary_preview' array by extracting the 'summary' field from the existing itinerary for the 'description' field. \n\nRULES:\n1. EXACTLY {trip_duration} items (Day 1 to Day {trip_duration}).\n2. ORDER MUST MATCH EXACTLY.\n3. DO NOT INVENT new activities.\n4. USE THE PROVIDED SUMMARY TEXT."

        system_prompt = f"""
        You are the Head User Interface Agent for WanderTrip.
        Synthesize the detailed intel from ALL of our intelligence subnetworks into a concise, helpful response.
        
        === FULL INTELLIGENCE BRIEFING ===
        {full_intel}
        
        USER PROFILE: {user_context}
        TRIP DURATION: {trip_duration} DAYS (CRITICAL: PLAN FOR ALL {trip_duration} DAYS)
        ACCOMMODATION: {chosen_stay}
        TRAVELERS: {group_type}
        TRAVEL DATES: {travel_dates}
        SAFETY STATUS: {safety_verdict} (Risk Score: {risk_score}/100)
        ACTIVE THREATS: {active_threats_summary}
        
        Task:
        1. Synthesize ALL available data into a Recommendation Object answering the USER QUERY.
        2. STRICTLY OUTPUT VALID JSON ONLY. NO MARKDOWN.
        3. VALUES MUST BE PLAIN TEXT. NO HTML.
        4. WEAVE IN cultural tips, budget advice, and health warnings naturally into your recommendation.
        
        CRITICAL RULES:
        - YOU MUST GENERATE EXACTLY {trip_duration} ITEMS for 'itinerary_preview' (ONE PER DAY).
        {itin_instruction}
        - "time": Use "Day 1" to "Day {trip_duration}".
        - "title": A catchy theme for the day (e.g. "Historical Dive").
        - "description": The extracted summary of the day's activities. Max 50 words.
        - "location": Main area/city.
        - "highlight": Key experience (under 10 words).
        - "cost_estimate": Daily total estimate strictly in Indian Rupees (INR) (symbol: ₹).
        
        ⚠️ FINAL CHECK: You MUST have EXACTLY {trip_duration} items.
        
        JSON FORMAT (keep descriptions SHORT — this is a preview):
        {{
            "type": "recommendation",
            "best_call": {{ "title": "...", "badge": "...", "description": "..." }},
            "itinerary_preview": [
                {{ "day": "Day 1", "time": "Day 1", "title": "Arrival & Exploration", "description": "Land in Tokyo, check into Shinjuku hotel, evening food tour in Omoide Yokocho.", "location": "Shinjuku", "cost_estimate": "₹4000", "highlight": "Omoide Yokocho" }},
                {{ "day": "Day 2", "time": "Day 2", "title": "...", "description": "...", "location": "...", "cost_estimate": "...", "highlight": "..." }},
                // ... CRITICAL: YOU MUST GENERATE OBJECTS FOR ALL {trip_duration} DAYS. DO NOT STOP AT DAY 2.
            ],
            "detailed_options": [
                {{ "title": "...", "description": "...", "rating": "4.5/5", "cost": "₹₹" }},
                ... (Min 5 items)
            ],
            "avoid": {{ "title": "...", "reason": "..." }},
            "backup": {{ "title": "...", "reason": "..." }},
            "pro_tips": ["..."],
            "confidence_score": "High",
            "confidence_reason": "..."
        }}
        """
        
        # Build messages with conversation history for context
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            # Include last 2 exchanges only to save tokens
            for msg in conversation_history[-2:]:
                content = msg.get("content", "")
                if isinstance(content, dict):
                    # Only include a brief summary of previous recommendations to save tokens
                    if content.get("type") == "recommendation":
                        content = f"[Previous recommendation: {content.get('best_call', {}).get('title', 'trip')}]"
                    else:
                        content = str(content)[:500] + "..." # Truncate JSON
                else:
                    # Truncate long user messages
                    content = str(content)[:500]
                messages.append({"role": msg["role"], "content": content})
        
        messages.append({"role": "user", "content": user_query})
        
        fallback = {
            "type": "error",
            "message": "I'm having trouble thinking clearly (Rate Limit). Please try again in moment.",
            "best_call": {"title": "Error", "badge": "System", "description": "Rate limit exceeded."},
            "itinerary_preview": [
                {"day": "Day 1", "time": "Morning", "title": "System Overload", "description": "Please wait a moment and try again.", "location": "Server", "time": "Morning"}
            ]
        }
        
        result = call_llm_json(
            self.client,
            messages,
            model=self.model,
            temperature=0.6,
            max_tokens=16000,
            fallback=fallback
        )
        
        # FORCE SYNC: Overwrite LLM hallucinated preview with Deterministic Source of Truth
        if itinerary and not itinerary.get("error"):
             deterministic_preview = self._generate_preview_from_itinerary(itinerary)
             if deterministic_preview:
                 result["itinerary_preview"] = deterministic_preview
                 logger.info(f"Overwrote itinerary preview with {len(deterministic_preview)} days from source.")

        return result

    def _generate_preview_from_itinerary(self, itinerary):
        """
        Deterministically generates the itinerary preview from the full itinerary source of truth.
        """
        preview = []
        if not itinerary or itinerary.get("error"):
            return preview

        # Sort days numerically
        day_keys = [k for k in itinerary.keys() if k.startswith("day_")]
        
        def get_day_num(k):
             try:
                 return int(k.split("_")[-1])
             except:
                 return 999
        
        day_keys.sort(key=get_day_num)

        for key in day_keys:
            day_data = itinerary[key]
            if not isinstance(day_data, dict):
                 continue
            
            # Extract basic info
            day_num = get_day_num(key)
            title = day_data.get("title", f"Day {day_num}")
            
            # Construct a rich description from ACTUAL activities to ensure 100% consistency
            parts = []
            
            # Helper to extract activity name responsibly
            def get_activity_name(slot_data):
                if isinstance(slot_data, dict):
                    return slot_data.get("preview_desc", slot_data.get("activity", ""))
                return str(slot_data) if slot_data else ""

            m_act = get_activity_name(day_data.get("morning"))
            a_act = get_activity_name(day_data.get("afternoon"))
            e_act = get_activity_name(day_data.get("evening"))
            
            if m_act: parts.append(f"**Morning:** {m_act}")
            if a_act: parts.append(f"**Afternoon:** {a_act}")
            if e_act: parts.append(f"**Evening:** {e_act}")
            
            description = "\n\n".join(parts)

            # Extract highlight/cost
            # prioritizes specific fields if available
            location = day_data.get("morning", {}).get("location", "City Wide") if isinstance(day_data.get("morning"), dict) else "City Wide"
            cost = day_data.get("estimated_cost", "Varies")
            
            # Find a highlight - check insider tips
            highlight = "Explore"
            for time_slot in ["morning", "afternoon", "evening"]:
                slot_data = day_data.get(time_slot, {})
                if isinstance(slot_data, dict) and slot_data.get("insider_tip"):
                    highlight = slot_data["insider_tip"][:30] # Short highlight
                    break

            preview.append({
                "day": f"Day {day_num}",
                "time": f"Day {day_num}", # Used for grouping in UI
                "title": title,
                "description": description,
                "location": location,
                "highlight": highlight,
                "cost_estimate": cost
            })
            
        return preview
