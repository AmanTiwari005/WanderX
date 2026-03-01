import datetime
import logging
import random

logger = logging.getLogger("wanderx.decision_engine")


class DecisionEngine:
    """
    RTRIE Decision Layer
    - Converts risk/alert intelligence into actionable travel decisions
    - Produces automation actions usable by SMS/Push/Email/UI channels
    """

    def assess_feasibility(self, plan_type, context, profile=None):
        profile = profile or {}
        weather = context.get("weather", {})
        hour = (context.get("time") or {}).get("hour", datetime.datetime.now().hour)

        rain_prob = weather.get("rain_probability", 0)
        temp = weather.get("temperature_c", 25)
        wind = weather.get("wind_speed", 0)
        daylight = context.get("daylight_remaining")

        reasons = []
        feasible = True
        confidence = "High"

        is_outdoor = plan_type in ("outdoor", "outdoor_adventure", "beach", "trek", "nature", "hike")
        is_water = plan_type in ("beach", "water_sports", "kayak", "rafting")

        if is_outdoor and rain_prob >= 0.7:
            feasible = False
            reasons.append(f"Rain probability is {int(rain_prob * 100)}%, making outdoor execution unstable.")

        if is_outdoor and temp >= 38 and 11 <= hour <= 16:
            feasible = False
            reasons.append(f"Temperature is {temp}°C in midday risk window.")

        if is_outdoor and wind >= 15:
            feasible = False
            reasons.append(f"Wind speed is {round(wind * 3.6)} km/h, above safe threshold for open exposure.")

        if is_water and wind >= 10:
            feasible = False
            reasons.append(f"Wind at {round(wind * 3.6)} km/h is unsafe for water activities.")

        if is_outdoor and daylight is not None and daylight <= 1.0:
            reasons.append(f"Only {daylight:.1f}h daylight remains; schedule compression expected.")
            confidence = "Medium"

        group_type = (profile.get("group_type") or "").lower()
        if any(k in group_type for k in ["elder", "senior"]) and plan_type in ("trek", "outdoor_adventure"):
            feasible = False
            reasons.append("High-exertion activity conflicts with senior-safe planning constraints.")

        if any(k in group_type for k in ["family", "child", "kid"]) and plan_type in ("outdoor_adventure", "rafting"):
            reasons.append("Child-safe guardrails suggest milder alternatives for this activity.")
            confidence = "Medium"

        return {
            "feasible": feasible,
            "confidence": confidence,
            "reasons": reasons,
        }

    def get_safety_warnings(self, context, profile=None):
        profile = profile or {}
        warnings = []

        weather = context.get("weather", {})
        crowd = context.get("crowd", {})
        news = context.get("news", {})
        health = context.get("health", {})
        daylight = context.get("daylight_remaining")
        hour = (context.get("time") or {}).get("hour", datetime.datetime.now().hour)

        rain_prob = weather.get("rain_probability", 0)
        temp = weather.get("temperature_c", 25)
        wind = weather.get("wind_speed", 0)

        if rain_prob >= 0.8:
            warnings.append(f"⚠️ Severe rain risk ({int(rain_prob * 100)}%): avoid exposed routes and hillside roads.")
        elif rain_prob >= 0.6:
            warnings.append(f"🌧️ Elevated rain risk ({int(rain_prob * 100)}%): keep waterproof fallback ready.")

        if temp >= 40:
            warnings.append(f"🚨 Extreme heat ({temp}°C): suspend high-exertion outdoor activity in midday.")
        elif temp >= 36:
            warnings.append(f"🌡️ High heat ({temp}°C): hydrate frequently and use shade-first routing.")

        if temp <= 0:
            warnings.append(f"🥶 Freezing conditions ({temp}°C): limit exposure windows and protect extremities.")

        if wind >= 15:
            warnings.append(f"🌬️ Strong wind ({round(wind * 3.6)} km/h): avoid exposed viewpoints and open-water plans.")

        if daylight is not None and daylight <= 0.5:
            warnings.append("🌅 Critical daylight limit: return to well-lit safe zones now.")
        elif daylight is not None and daylight <= 1.5:
            warnings.append(f"🌅 Daylight low ({daylight:.1f}h): finalize outdoor sequence.")

        if hour < 6 or hour >= 22:
            warnings.append("🌙 Late-hour movement risk: stick to high-visibility, populated corridors.")

        cs = crowd.get("crowd_score", 0)
        if cs >= 8:
            warnings.append(f"👥 Crowd surge ({cs}/10): pickpocket and delay risks are elevated.")

        for risk in (news.get("safety_risks") or [])[:3]:
            warnings.append(f"📰 Advisory: {risk.get('title', 'Safety advisory')}.")

        seasonal = (health.get("seasonal_risks") or "").lower()
        if any(k in seasonal for k in ["dengue", "malaria", "cholera", "outbreak"]):
            warnings.append(f"🩺 Health watch: {health.get('seasonal_risks', 'seasonal health risk')}.")

        return warnings

    def generate_plan_suggestions(self, context, profile=None):
        profile = profile or {}
        suggestions = []

        weather = context.get("weather", {})
        crowd = context.get("crowd", {})
        news = context.get("news", {})
        sustainability = context.get("sustainability", {})

        hour = (context.get("time") or {}).get("hour", datetime.datetime.now().hour)
        daylight = context.get("daylight_remaining")

        rain_prob = weather.get("rain_probability", 0)
        temp = weather.get("temperature_c", 25)
        crowd_score = crowd.get("crowd_score", 0)

        # Weather-adaptive suggestions
        if rain_prob >= 0.6:
            suggestions.append({
                "title": "Weather-Protected Experience",
                "reason": f"Rain risk is {int(rain_prob * 100)}%; indoor and covered venues maximize continuity.",
                "confidence": "High",
                "tags": ["weather", "indoor", "resilient"]
            })
        else:
            suggestions.append({
                "title": "Open-Air Exploration Window",
                "reason": f"Current weather ({temp}°C) supports efficient outdoor exploration.",
                "confidence": "High" if 18 <= temp <= 32 else "Medium",
                "tags": ["weather", "outdoor"]
            })

        if temp >= 36 and 11 <= hour <= 16:
            suggestions.append({
                "title": "Heat-Aware Split Schedule",
                "reason": "Use morning/evening for movement and midday for indoor or rest blocks.",
                "confidence": "High",
                "tags": ["heat", "schedule"]
            })

        # Crowd-adaptive suggestions
        if crowd_score >= 8:
            suggestions.append({
                "title": "Anti-Crowd Route",
                "reason": f"Crowd index {crowd_score}/10 favors off-peak and secondary attractions.",
                "confidence": "High",
                "tags": ["crowd", "routing"]
            })
        elif crowd_score >= 6:
            suggestions.append({
                "title": "Staggered Attraction Timing",
                "reason": "Moderate crowd pressure detected; sequence top spots in low-density windows.",
                "confidence": "Medium",
                "tags": ["crowd", "timing"]
            })

        # Daylight suggestion
        if daylight is not None and 1.0 < daylight <= 2.5 and rain_prob < 0.5:
            suggestions.append({
                "title": "Golden-Hour Priority Slot",
                "reason": f"{daylight:.1f}h daylight left; strong window for scenic/photo value.",
                "confidence": "High",
                "tags": ["time", "photo", "outdoor"]
            })

        # News opportunities
        for op in (news.get("opportunities") or [])[:2]:
            suggestions.append({
                "title": f"Live Opportunity: {op.get('title', 'Event')}",
                "reason": op.get("summary", "Current local opportunity detected."),
                "confidence": "Medium",
                "tags": ["live", "event"]
            })

        # Connectivity-aware recommendation
        conn = (sustainability.get("connectivity") or "").lower()
        if any(k in conn for k in ["poor", "limited", "no signal", "remote"]):
            suggestions.append({
                "title": "Offline-Ready Plan",
                "reason": "Connectivity risk detected; preload maps/tickets and share fallback rendezvous points.",
                "confidence": "High",
                "tags": ["connectivity", "resilience"]
            })

        # Deduplicate titles
        seen = set()
        unique = []
        for s in suggestions:
            title = s.get("title", "")
            if title in seen:
                continue
            seen.add(title)
            unique.append(s)

        return unique

    def get_automated_decisions(self, risk_assessment, alerts, context, profile=None):
        profile = profile or {}
        risk_score = (risk_assessment or {}).get("total_risk_score", 0)
        verdict = (risk_assessment or {}).get("verdict", "Safe")

        critical_alerts = [a for a in (alerts or []) if (a.get("type") or "").lower() == "critical"]
        high_alerts = [a for a in (alerts or []) if (a.get("type") or "").lower() in ("high", "warning")]

        actions = []

        if risk_score >= 75 or verdict == "Critical":
            actions.append(self._automation("freeze_high_risk_blocks", "active", "Pause all high-exposure itinerary items immediately."))
            actions.append(self._automation("switch_to_safe_mode", "active", "Limit plan to essential transit and indoor safe zones."))
        elif risk_score >= 55:
            actions.append(self._automation("enable_guarded_mode", "active", "Require backup plan for every outdoor block."))
        else:
            actions.append(self._automation("normal_mode", "active", "Continue itinerary with live monitoring enabled."))

        if critical_alerts:
            actions.append(self._automation("priority_channel_dispatch", "active", "Dispatch critical alerts to push/email immediately."))

        if len(high_alerts) >= 3:
            actions.append(self._automation("auto_reorder_schedule", "active", "Re-sequence day plan to reduce compound risk overlap."))

        return {
            "risk_mode": "critical" if risk_score >= 75 else "guarded" if risk_score >= 55 else "normal",
            "automation_actions": actions,
        }

    def get_seasonal_recommendations(self, month=None):
        seasonal_map = {
            "❄️ Snowy Peaks": ["Manali", "Auli", "Gulmarg", "Spiti Valley", "Tawang", "Leh-Ladakh"],
            "🏖️ Winter Sun": ["Goa", "Varkala", "Pondicherry", "Andaman", "Gokarna", "Lakshadweep"],
            "🏰 Royal History": ["Udaipur", "Jaipur", "Hampi", "Mysore", "Jodhpur", "Khajuraho"],
            "🌿 Nature & Chill": ["Munnar", "Coorg", "Meghalaya", "Wayanad", "Darjeeling", "Ziro Valley"],
            "🌏 International Gems": ["Thailand", "Vietnam", "Dubai", "Sri Lanka", "Bali", "Singapore"],
            "🧗 Adventure Capital": ["Rishikesh", "Bir Billing", "Meghalaya", "Andaman", "Dandeli", "Kasol"],
            "🧘 Spiritual Journeys": ["Varanasi", "Bodh Gaya", "Rishikesh", "Amritsar", "Tirupati", "Haridwar"],
            "🌌 Stargazing & Solitude": ["Spiti Valley", "Hanle", "Rann of Kutch", "Nubra Valley", "Jaisalmer", "Tso Moriri"],
            "🍜 Foodie Paradise": ["Hyderabad", "Lucknow", "Amritsar", "Kolkata", "Old Delhi", "Mumbai"],
            "🏝️ Island Escape": ["Havelock", "Neil Island", "Lakshadweep", "Phuket", "Langkawi", "Bintan"],
            "🎉 City Energy": ["Tokyo", "Seoul", "Bangkok", "Mumbai", "Barcelona", "Istanbul"],
            "🌿 Remote Escapes": ["Ziro Valley", "Tirthan Valley", "Chopta", "Kalpa", "Kanha", "Binsar"],
        }

        if month is None:
            month = datetime.datetime.now().month

        # Mild month-aware prioritization while still returning broad variety
        if month in (11, 12, 1, 2):
            priority = ["❄️ Snowy Peaks", "🏖️ Winter Sun", "🌌 Stargazing & Solitude", "🍜 Foodie Paradise"]
        elif month in (3, 4, 5):
            priority = ["🌿 Nature & Chill", "🏰 Royal History", "🧗 Adventure Capital", "🌏 International Gems"]
        elif month in (6, 7, 8, 9):
            priority = ["🏝️ Island Escape", "🎉 City Energy", "🧘 Spiritual Journeys", "🌏 International Gems"]
        else:
            priority = ["🌿 Nature & Chill", "🏰 Royal History", "🍜 Foodie Paradise", "🌏 International Gems"]

        ordered = {key: seasonal_map[key] for key in priority if key in seasonal_map}
        for key, value in seasonal_map.items():
            if key not in ordered:
                ordered[key] = value

        return ordered

    def get_surprise_destinations(self, profile=None, count=6):
        """
        Returns curated 'Surprise Me' destination suggestions with reasons.
        """
        profile = profile or {}
        interests = (profile.get("interests") or "").lower()
        budget = (profile.get("budget") or "").lower()
        pace = (profile.get("pace") or "").lower()

        recommendation_map = self.get_seasonal_recommendations()
        all_destinations = []
        for theme, places in recommendation_map.items():
            for place in places:
                all_destinations.append({"name": place, "theme": theme})

        random.shuffle(all_destinations)

        def reason_for(place, theme):
            reason = f"Great fit from {theme.lower()} recommendations."
            if "food" in interests:
                reason = f"{place} is excellent for local food exploration and vibrant dining scenes."
            elif "adventure" in interests or "trek" in interests:
                reason = f"{place} offers strong adventure potential with dynamic outdoor experiences."
            elif "culture" in interests or "history" in interests:
                reason = f"{place} has rich culture and history with high sightseeing value."
            elif "beach" in interests or "island" in interests:
                reason = f"{place} is ideal for coastal vibes, sunsets, and relaxed exploration."

            if any(k in budget for k in ["low", "budget", "backpacker", "tight"]):
                reason += " Budget-friendly options are available with smart planning."
            elif any(k in budget for k in ["luxury", "premium", "high"]):
                reason += " Strong premium/luxury experience potential."

            if pace in ("fast", "energetic"):
                reason += " Good for high-activity itineraries."
            elif pace in ("relaxed", "chilled"):
                reason += " Works well for a relaxed pace."

            return reason

        picks = []
        used = set()
        for item in all_destinations:
            if item["name"] in used:
                continue
            used.add(item["name"])
            picks.append({
                "destination": item["name"],
                "theme": item["theme"],
                "reason": reason_for(item["name"], item["theme"]),
            })
            if len(picks) >= max(3, count):
                break

        return picks

    def calculate_reachability_score(self, distance_km, travel_time_hours, daylight_remaining, current_hour, terrain="flat", traffic_factor=1.0):
        score = 100
        reasons = []

        if distance_km > 200:
            score -= 35
            reasons.append(f"Distance load is high ({distance_km} km).")
        elif distance_km > 100:
            score -= 18
            reasons.append(f"Distance is moderate ({distance_km} km).")

        if daylight_remaining is not None and travel_time_hours > max(0.5, daylight_remaining * 0.7):
            score -= 28
            reasons.append("Travel duration consumes most remaining daylight.")

        if current_hour >= 19:
            score -= 18
            reasons.append("Late start time reduces reliable activity window.")

        terrain_penalty = {
            "mountain": 15,
            "hilly": 10,
            "desert": 8,
            "forest": 6,
            "flat": 0,
        }.get((terrain or "flat").lower(), 4)
        score -= terrain_penalty
        if terrain_penalty:
            reasons.append(f"Terrain complexity penalty applied ({terrain}).")

        if traffic_factor > 1.5:
            score -= 15
            reasons.append(f"Heavy traffic multiplier ({traffic_factor:.1f}x).")
        elif traffic_factor > 1.2:
            score -= 8
            reasons.append(f"Moderate traffic multiplier ({traffic_factor:.1f}x).")

        score = max(0, min(100, round(score)))
        verdict = "Highly Reachable" if score >= 70 else "Moderately Reachable" if score >= 45 else "Challenging"

        return {
            "score": score,
            "verdict": verdict,
            "reasons": reasons,
        }

    def _automation(self, action, status, reason):
        return {
            "action": action,
            "status": status,
            "reason": reason,
            "created_at": datetime.datetime.now().isoformat(),
        }
