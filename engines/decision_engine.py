import datetime
import logging

logger = logging.getLogger("wanderx.decision_engine")


class DecisionEngine:
    def __init__(self):
        # Interest → activity type mapping for smart suggestions
        self.interest_activities = {
            "food": [
                {"title": "Local Food Tour", "reason": "Explore authentic local cuisine and street food.", "confidence": "High"},
                {"title": "Cooking Class Experience", "reason": "Learn to make regional dishes from local chefs.", "confidence": "Medium"},
            ],
            "history": [
                {"title": "Heritage Walking Tour", "reason": "Explore historical landmarks with cultural context.", "confidence": "High"},
                {"title": "Museum & Monument Deep-Dive", "reason": "Dig into local history through curated exhibits.", "confidence": "High"},
            ],
            "adventure": [
                {"title": "Outdoor Adventure Activity", "reason": "Conditions are good for adrenaline activities.", "confidence": "High"},
                {"title": "Nature Trail Expedition", "reason": "Explore trails and wildlife in the area.", "confidence": "Medium"},
            ],
            "beach": [
                {"title": "Beach & Water Sports", "reason": "Great day for sun, sand, and water activities.", "confidence": "High"},
                {"title": "Sunset Coastal Walk", "reason": "Scenic seaside experience during golden hour.", "confidence": "High"},
            ],
            "culture": [
                {"title": "Local Art & Craft Exploration", "reason": "Discover regional artisans, galleries, and workshops.", "confidence": "Medium"},
                {"title": "Temple & Spiritual Walk", "reason": "Immerse in the spiritual and cultural heritage.", "confidence": "High"},
            ],
            "nature": [
                {"title": "Scenic Nature Walk", "reason": "Ideal weather for enjoying natural landscapes.", "confidence": "High"},
                {"title": "Wildlife & Bird Watching", "reason": "Explore the local biodiversity at the right hours.", "confidence": "Medium"},
            ],
            "shopping": [
                {"title": "Local Market & Bazaar", "reason": "Browse authentic handicrafts, spices, and souvenirs.", "confidence": "Medium"},
            ],
            "photography": [
                {"title": "Golden Hour Photo Walk", "reason": "Best light for stunning travel photography.", "confidence": "High"},
            ],
            "wellness": [
                {"title": "Spa & Wellness Retreat", "reason": "Recharge with local wellness traditions.", "confidence": "High"},
            ],
        }

    # ─────────────────────────────────────────────────────────────────
    # FEASIBILITY ASSESSMENT
    # ─────────────────────────────────────────────────────────────────
    def assess_feasibility(self, plan_type, context, profile=None):
        """
        Determines if a plan is realistic given weather, time, health, budget,
        group capabilities, terrain, and environmental conditions.
        """
        weather = context.get("weather", {})
        time_ctx = context.get("time", {})
        profile = profile or {}
        group_type = (profile.get("group_type") or "").lower()
        budget_tier = (profile.get("budget") or "moderate").lower()

        reasons = []
        is_feasible = True
        confidence = "High"

        current_hour = time_ctx.get("hour", 12)
        temp_c = weather.get("temperature_c", 25)
        rain_prob = weather.get("rain_probability", 0)
        wind_speed = weather.get("wind_speed", 0)  # m/s
        feels_like = weather.get("feels_like_c", temp_c)

        is_outdoor = plan_type in ("outdoor", "outdoor_adventure", "beach", "trek", "nature")
        is_adventure = plan_type in ("outdoor_adventure", "trek", "adventure")
        is_water = plan_type in ("beach", "water_sports", "kayak", "rafting")

        # ── Weather Checks ────────────────────────────────────────
        # Rain
        if rain_prob > 0.5 and is_outdoor:
            is_feasible = False
            reasons.append("High probability of rain makes outdoor activities risky.")

        # Extreme Heat (midday)
        if temp_c > 38 and is_outdoor and 11 <= current_hour <= 16:
            is_feasible = False
            reasons.append("Extreme heat during midday. Heat stroke risk for outdoor plans.")
        elif temp_c > 35 and is_outdoor and 11 <= current_hour <= 16:
            reasons.append("High temperatures during midday. Consider rescheduling to early morning or evening.")
            confidence = "Medium"

        # Cold check
        if temp_c < 0 and is_outdoor:
            is_feasible = False
            reasons.append(f"Sub-zero temperature ({temp_c}°C). Frostbite risk for extended outdoor exposure.")
        elif temp_c < 5 and is_outdoor:
            reasons.append(f"Cold conditions ({temp_c}°C). Ensure warm clothing and reduce outdoor duration.")
            confidence = "Medium"

        # Wind chill factor
        if wind_speed > 10 and temp_c < 10:
            wind_chill = 13.12 + 0.6215 * temp_c - 11.37 * ((wind_speed * 3.6) ** 0.16) + 0.3965 * temp_c * ((wind_speed * 3.6) ** 0.16)
            if wind_chill < -10:
                is_feasible = False
                reasons.append(f"Wind chill factor makes it feel like {round(wind_chill)}°C. Dangerous for outdoor plans.")
            elif wind_chill < 0:
                reasons.append(f"Wind chill brings effective temperature to {round(wind_chill)}°C. Bundle up.")
                confidence = "Medium"

        # Humidity + Heat → Heat index
        humidity = weather.get("humidity", 50)
        if humidity > 80 and temp_c > 32 and is_outdoor:
            reasons.append("High humidity + heat creates heat stroke risk. Take frequent breaks, stay hydrated.")
            confidence = "Medium"

        # High wind
        if wind_speed > 15 and is_outdoor:
            is_feasible = False
            reasons.append(f"Strong winds ({round(wind_speed * 3.6)} km/h) make outdoor activities unsafe.")
        elif wind_speed > 10 and is_water:
            is_feasible = False
            reasons.append(f"Winds too strong ({round(wind_speed * 3.6)} km/h) for water activities.")

        # UV exposure
        uv_index = weather.get("uv_index", 0)
        if uv_index > 10 and is_outdoor:
            reasons.append(f"Extreme UV index ({uv_index}). Apply SPF 50+ sunscreen and wear hat/sunglasses.")
            confidence = "Medium"
        elif uv_index > 7 and is_outdoor:
            reasons.append(f"High UV ({uv_index}). Sun protection strongly recommended.")

        # ── Time Checks ───────────────────────────────────────────
        if current_hour > 20 and is_adventure:
            is_feasible = False
            reasons.append("Too late for adventure activities. Safety risk in darkness.")

        if current_hour > 22 and is_outdoor:
            is_feasible = False
            reasons.append("Very late for any outdoor activity. Stick to indoor/well-lit dining.")

        # Daylight remaining
        daylight = context.get("daylight_remaining")
        if daylight is not None and daylight < 1 and is_outdoor:
            reasons.append(f"Only {daylight:.1f}h of daylight left. Outdoor feasibility limited.")
            confidence = "Medium"

        # ── Terrain / Altitude ────────────────────────────────────
        altitude = context.get("altitude", 0)
        if altitude > 3500 and is_adventure:
            is_feasible = False
            reasons.append(f"Altitude of {altitude}m requires acclimatization. Adventure activities dangerous on arrival day.")
        elif altitude > 2500:
            reasons.append(f"Altitude of {altitude}m — take it easy, hydrate, watch for AMS symptoms.")
            confidence = "Medium"

        if rain_prob > 0.3 and plan_type in ("trek", "outdoor_adventure") and altitude > 1500:
            is_feasible = False
            reasons.append("Rain + mountain terrain = landslide/mudslide risk. Trek is unsafe.")

        # ── Budget Check ──────────────────────────────────────────
        if budget_tier in ("low", "budget", "backpacker") and plan_type in ("luxury", "premium", "fine_dining"):
            is_feasible = False
            reasons.append("Activity exceeds your budget tier. Consider an affordable alternative.")

        # ── Group Capability ──────────────────────────────────────
        if ("famil" in group_type or "child" in group_type or "kid" in group_type):
            if is_adventure:
                reasons.append("Adventure activity may not be suitable for children. Check age restrictions.")
                confidence = "Medium"

        if ("elder" in group_type or "senior" in group_type):
            if plan_type in ("trek", "outdoor_adventure"):
                is_feasible = False
                reasons.append("Strenuous activity is risky for elderly travelers.")
            if altitude > 2500:
                reasons.append("High altitude with elderly travelers requires extra caution and medical readiness.")
                confidence = "Low"

        return {
            "feasible": is_feasible,
            "confidence": confidence,
            "reasons": reasons
        }

    # ─────────────────────────────────────────────────────────────────
    # SAFETY WARNINGS
    # ─────────────────────────────────────────────────────────────────
    def get_safety_warnings(self, context, profile=None):
        """
        Returns context-aware safety warnings from weather, crowd, news,
        health, altitude, and air quality.
        """
        warnings = []
        weather = context.get("weather", {})
        time_ctx = context.get("time", {})
        daylight = context.get("daylight_remaining")
        crowd = context.get("crowd", {})
        news_intel = context.get("news", {})
        health = context.get("health", {})
        profile = profile or {}

        current_hour = time_ctx.get("hour", 12)
        rain_prob = weather.get("rain_probability", 0)
        temp_c = weather.get("temperature_c", 25)

        # Rain warning
        if rain_prob > 0.7:
            warnings.append("⚠️ Heavy Rain Alert: Avoid landslide zones, waterfalls, and slippery trails.")
        elif rain_prob > 0.4:
            warnings.append("🌧️ Moderate Rain: Carry an umbrella and waterproof gear.")

        # Late night
        if current_hour and (current_hour < 6 or current_hour > 22):
            warnings.append("🌙 Late Night Warning: Stick to well-lit, populated areas.")

        # Daylight alerts
        if daylight is not None and daylight < 2:
            warnings.append(f"🌅 Sunset Alert: Only {daylight:.1f} hours of daylight left. Plan indoor activities soon.")

        if daylight is not None and daylight < 0.5:
            warnings.append("⚠️ Critical: Nearly dark. Outdoor activities not recommended.")

        # Crowd density
        if crowd and "warnings" in crowd:
            warnings.extend(crowd["warnings"])

        # High temperature
        if temp_c > 40:
            warnings.append(f"🌡️ Extreme Heat ({temp_c}°C): Heat exhaustion risk. Drink water every 15 min.")
        elif temp_c > 35:
            warnings.append(f"🌡️ High Heat ({temp_c}°C): Stay hydrated, seek shade during midday.")

        # Cold
        if temp_c < 0:
            warnings.append(f"🥶 Freezing Conditions ({temp_c}°C): Risk of frostbite. Cover all exposed skin.")

        # AQI / Air quality from weather description
        desc = (weather.get("description") or "").lower()
        if any(kw in desc for kw in ["smoke", "haze", "dust"]):
            warnings.append("🫁 Air Quality Warning: Wear a mask outdoors, especially if you have respiratory conditions.")

        # Altitude
        altitude = context.get("altitude", 0)
        if altitude > 3000:
            warnings.append(f"⛰️ High Altitude ({altitude}m): Risk of AMS. Ascend gradually, hydrate, avoid alcohol.")

        # News-based safety risks
        if news_intel and "safety_risks" in news_intel:
            for risk in news_intel["safety_risks"]:
                warnings.append(f"🚨 NEWS ALERT: {risk.get('title')} — {risk.get('summary')}")

        # Health-based warnings
        if health and not health.get("error"):
            seasonal = (health.get("seasonal_risks") or "").lower()
            if any(kw in seasonal for kw in ["dengue", "malaria", "zika"]):
                warnings.append(f"🦠 Health Warning: {health.get('seasonal_risks', '')} — use insect repellent.")

        return warnings

    # ─────────────────────────────────────────────────────────────────
    # PLAN SUGGESTIONS
    # ─────────────────────────────────────────────────────────────────
    def generate_plan_suggestions(self, context, profile=None):
        """
        Returns smart, context-adaptive plan suggestions using 8+ logic blocks:
        weather, time, crowd, news, interests, budget, cultural events, sustainability.
        """
        suggestions = []
        weather = context.get("weather", {})
        time_ctx = context.get("time", {})
        crowd = context.get("crowd", {})
        news_intel = context.get("news", {})
        cultural = context.get("cultural", {})
        sustainability = context.get("sustainability", {})
        profile = profile or {}
        interests = (profile.get("interests") or "").lower()
        budget_tier = (profile.get("budget") or "moderate").lower()
        daylight = context.get("daylight_remaining")

        is_raining = weather.get("rain_probability", 0) > 0.5
        is_night = time_ctx.get("hour", 12) > 19
        temp_c = weather.get("temperature_c", 25)

        # ── Logic 1: Weather Adaptive ──────────────────────────────
        if is_raining:
            suggestions.append({
                "title": "Indoor Cultural Dive",
                "reason": "It's raining outside. Perfect time for museums, galleries, or cozy cafés.",
                "confidence": "High",
                "tags": ["weather-adaptive", "indoor"]
            })
        elif not is_night and temp_c < 35:
            suggestions.append({
                "title": "Scenic Nature Walk",
                "reason": "Weather is pleasant and daylight is good.",
                "confidence": "High",
                "tags": ["weather-adaptive", "outdoor"]
            })

        if temp_c > 35 and not is_night:
            suggestions.append({
                "title": "Pool, Spa, or Indoor Retreat",
                "reason": f"It's {temp_c}°C outside. Beat the heat with a refreshing indoor experience.",
                "confidence": "High",
                "tags": ["weather-adaptive", "indoor"]
            })

        # ── Logic 2: Time Adaptive ─────────────────────────────────
        if is_night:
            suggestions.append({
                "title": "Safe Featured Dining",
                "reason": "Late hours are best for relaxed, well-lit dining experiences.",
                "confidence": "Medium",
                "tags": ["time-adaptive", "dining"]
            })

        # Golden Hour suggestion
        if daylight is not None and 1 < daylight < 2.5 and not is_raining:
            suggestions.append({
                "title": "Golden Hour Viewpoint",
                "reason": f"Sunset in ~{daylight:.0f}h! Head to a scenic viewpoint for stunning photos.",
                "confidence": "High",
                "tags": ["time-adaptive", "photography"]
            })

        # Early morning
        hour = time_ctx.get("hour", 12)
        if 5 <= hour <= 7 and not is_raining:
            suggestions.append({
                "title": "Sunrise & Morning Walk",
                "reason": "Best time for peaceful walks, sunrise views, and avoiding crowds.",
                "confidence": "High",
                "tags": ["time-adaptive", "outdoor"]
            })

        # ── Logic 3: Crowd Adaptive ────────────────────────────────
        if crowd and crowd.get("crowd_score", 0) >= 7:
            if "alternatives" in crowd:
                for alt in crowd["alternatives"][:2]:
                    suggestions.append({
                        "title": "Crowd-Free Alternative",
                        "reason": alt,
                        "confidence": "Medium",
                        "tags": ["crowd-adaptive"]
                    })
            else:
                suggestions.append({
                    "title": "Off-Peak Visit Strategy",
                    "reason": "Crowds are high. Visit attractions early morning or during lunch hours.",
                    "confidence": "Medium",
                    "tags": ["crowd-adaptive"]
                })

        # ── Logic 4: News-Based Opportunities ──────────────────────
        if news_intel and "opportunities" in news_intel:
            for op in news_intel["opportunities"][:2]:
                suggestions.append({
                    "title": f"🎉 Event: {op.get('title')}",
                    "reason": f"Happening now: {op.get('summary')}",
                    "confidence": "High",
                    "tags": ["event", "news-based"]
                })

        # ── Logic 5: Interest-Based ────────────────────────────────
        matched_any = False
        for interest_key, activities in self.interest_activities.items():
            if interest_key in interests:
                matched_any = True
                for activity in activities[:1]:  # Top 1 per interest
                    # Skip outdoor suggestions if raining
                    if is_raining and any(kw in activity["title"].lower() for kw in ["outdoor", "trail", "beach", "nature", "walk"]):
                        continue
                    suggestions.append({
                        **activity,
                        "tags": ["interest-based", interest_key]
                    })
        
        if not matched_any and interests:
            suggestions.append({
                "title": "Explore Your Way",
                "reason": f"Based on your interest in '{interests}', explore curated local experiences.",
                "confidence": "Medium",
                "tags": ["interest-based"]
            })

        # ── Logic 6: Budget Adaptive ───────────────────────────────
        if budget_tier in ("low", "budget", "backpacker"):
            suggestions.append({
                "title": "Budget-Friendly Local Gems",
                "reason": "Explore free attractions, street food, and walking tours to maximize your budget.",
                "confidence": "High",
                "tags": ["budget-adaptive"]
            })
        elif budget_tier in ("luxury", "premium", "high"):
            suggestions.append({
                "title": "Premium Experience",
                "reason": "Indulge in exclusive dining, private tours, or luxury wellness experiences.",
                "confidence": "Medium",
                "tags": ["budget-adaptive"]
            })

        # ── Logic 7: Cultural Events ───────────────────────────────
        if cultural and not cultural.get("error"):
            festivals = cultural.get("local_festivals", [])
            if festivals:
                fest = festivals[0] if isinstance(festivals[0], str) else festivals[0].get("name", "Local Festival")
                suggestions.append({
                    "title": f"🎭 Cultural: {fest}",
                    "reason": "Immerse in local culture through this traditional event.",
                    "confidence": "Medium",
                    "tags": ["cultural"]
                })

        # ── Logic 8: Sustainability ────────────────────────────────
        if sustainability and not sustainability.get("error"):
            eco_tips = sustainability.get("eco_activities", sustainability.get("responsible_tips", []))
            if eco_tips and len(eco_tips) > 0:
                tip = eco_tips[0] if isinstance(eco_tips[0], str) else str(eco_tips[0])
                suggestions.append({
                    "title": "🌱 Eco-Friendly Option",
                    "reason": f"Sustainable travel: {tip[:100]}",
                    "confidence": "Medium",
                    "tags": ["sustainability"]
                })

        # Remove duplicates (by title)
        seen = set()
        unique = []
        for s in suggestions:
            if s["title"] not in seen:
                seen.add(s["title"])
                unique.append(s)

        return unique

    # ─────────────────────────────────────────────────────────────────
    # SEASONAL RECOMMENDATIONS
    # ─────────────────────────────────────────────────────────────────
    def get_seasonal_recommendations(self, month=None):
        """
        Returns curated destination ideas based on the season.
        """
        recommendations = {
            "❄️ Snowy Peaks": ["Manali", "Auli", "Gulmarg", "Spiti Valley", "Tawang", "Leh-Ladakh"],
            "🏖️ Winter Sun": ["Goa", "Varkala", "Pondicherry", "Andaman", "Gokarna", "Lakshadweep"],
            "🏰 Royal History": ["Udaipur", "Jaipur", "Hampi", "Mysore", "Jodhpur", "Khajuraho"],
            "🌿 Nature & Chill": ["Munnar", "Coorg", "Meghalaya", "Wayanad", "Darjeeling", "Ziro Valley"],
            "🌏 International Gems": ["Thailand", "Vietnam", "Dubai", "Sri Lanka", "Bali", "Singapore"],
            "🧗 Adventure Capital": ["Rishikesh", "Bir Billing", "Meghalaya (Caving)", "Andaman (Scuba)", "Dandeli"],
            "🧘 Spiritual Journeys": ["Varanasi", "Bodh Gaya", "Rishikesh", "Amritsar", "Tirupati", "Haridwar"],
            "🌌 Stargazing & Solitude": ["Spiti Valley", "Hanle", "Rann of Kutch", "Nubra Valley", "Jaisalmer"],
            "🍜 Foodie Paradise": ["Hyderabad", "Lucknow", "Amritsar", "Kolkata", "Delhi (Old)", "Mumbai"]
        }

        return recommendations

    # ─────────────────────────────────────────────────────────────────
    # REACHABILITY SCORE
    # ─────────────────────────────────────────────────────────────────
    def calculate_reachability_score(self, distance_km, travel_time_hours, daylight_remaining,
                                     current_hour, terrain="flat", traffic_factor=1.0):
        """
        Calculates a reachability score (0–100) factoring distance, time, daylight,
        terrain difficulty, and traffic conditions.
        """
        score = 100
        reasons = []

        # Distance penalty (exponential after 100km)
        if distance_km > 200:
            penalty = min(50, (distance_km - 100) / 4)
            score -= penalty
            reasons.append(f"Long distance: {distance_km}km")
        elif distance_km > 100:
            penalty = min(30, (distance_km - 100) / 5)
            score -= penalty
            reasons.append(f"Moderate distance: {distance_km}km")

        # Travel time vs daylight
        if daylight_remaining and travel_time_hours > daylight_remaining * 0.7:
            score -= 30
            reasons.append(f"Limited daylight for activity after {travel_time_hours:.1f}h travel")

        # Late hour penalty
        if current_hour > 18:
            score -= 20
            reasons.append("Late start time reduces feasibility")
        elif current_hour > 16:
            score -= 10
            reasons.append("Afternoon start — limited time at destination")

        # Terrain penalty
        terrain_penalties = {
            "mountain": 15,
            "hilly": 10,
            "desert": 8,
            "forest": 5,
            "flat": 0
        }
        terrain_p = terrain_penalties.get(terrain.lower(), 0)
        if terrain_p > 0:
            score -= terrain_p
            reasons.append(f"Terrain ({terrain}) adds travel difficulty")

        # Traffic multiplier (1.0 = normal, 2.0 = double time)
        if traffic_factor > 1.5:
            score -= 15
            reasons.append(f"Heavy traffic (×{traffic_factor:.1f}) delays expected")
        elif traffic_factor > 1.2:
            score -= 8
            reasons.append(f"Moderate traffic (×{traffic_factor:.1f}) may cause delays")

        score = max(0, score)

        if score >= 70:
            verdict = "Highly Reachable"
        elif score >= 40:
            verdict = "Moderately Reachable"
        else:
            verdict = "Challenging"

        return {
            "score": round(score),
            "verdict": verdict,
            "reasons": reasons
        }
