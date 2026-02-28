import logging

logger = logging.getLogger("wanderx.risk_fusion")


class RiskFusionEngine:
    def __init__(self):
        # Severity weights for different risk levels
        self.severity_weights = {
            "Critical": 30,
            "High": 22,
            "Medium": 12,
            "Low": 6
        }

    # ─────────────────────────────────────────────────────────────
    # CONFIDENCE SCORING
    # ─────────────────────────────────────────────────────────────
    def _calculate_confidence(self, weather_intel, news_intel, crowd_intel, mobility_intel,
                              health_intel=None, budget_intel=None, cultural_intel=None,
                              sustainability_intel=None, live_pulse_intel=None):
        """
        Calculate confidence score based on data quality and completeness.
        Returns: (confidence_score: float 0-1, level, reasoning, factors)
        """
        confidence = 1.0
        factors = []

        # Weather data quality (20% weight)
        if not weather_intel or not weather_intel.get("weather_data") or weather_intel.get("error"):
            confidence -= 0.20
            factors.append("❌ No weather data")
        else:
            age = weather_intel.get("data_age_minutes", 0)
            if age > 120:
                confidence -= 0.05
                factors.append("⚠️ Weather data may be stale (>2h old)")
            else:
                factors.append("✅ Live weather data")

        # News intelligence (18% weight)
        if not news_intel or news_intel.get("error"):
            confidence -= 0.15
            factors.append("⚠️ Limited news intelligence")
        elif news_intel.get("safety_risks"):
            factors.append("✅ Safety risks analyzed")
        else:
            factors.append("✅ No safety threats detected")

        # Crowd data (12% weight)
        if not crowd_intel or "crowd_score" not in crowd_intel or crowd_intel.get("error"):
            confidence -= 0.10
            factors.append("⚠️ Estimated crowd levels")
        else:
            factors.append("✅ Crowd analysis available")

        # Mobility data (8% weight)
        if mobility_intel and mobility_intel.get("travel_time"):
            factors.append("✅ Route data available")
        else:
            confidence -= 0.05
            factors.append("⚠️ No route data")

        # Health data (8% weight)
        if health_intel and not health_intel.get("error"):
            factors.append("✅ Health advisory available")
        else:
            confidence -= 0.08
            factors.append("⚠️ No health data")

        # Budget data (6% weight)
        if budget_intel and not budget_intel.get("error"):
            factors.append("✅ Budget analysis available")
        else:
            confidence -= 0.06
            factors.append("⚠️ No budget analysis")

        # Cultural data (5% weight)
        if cultural_intel and not cultural_intel.get("error"):
            factors.append("✅ Cultural intel available")
        else:
            confidence -= 0.05
            factors.append("⚠️ No cultural data")

        # Sustainability data (3% weight)
        if sustainability_intel and not sustainability_intel.get("error"):
            factors.append("✅ Sustainability data available")
        else:
            confidence -= 0.03
            factors.append("⚠️ No sustainability data")

        # Live pulse (5% weight)
        if live_pulse_intel and not live_pulse_intel.get("error"):
            factors.append("✅ Live web intelligence available")
        else:
            confidence -= 0.05
            factors.append("⚠️ No live web intelligence")

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.85:
            level = "High"
            reasoning = "All critical data sources available with live updates"
        elif confidence >= 0.65:
            level = "Medium"
            reasoning = "Most data sources available, some estimates used"
        elif confidence >= 0.45:
            level = "Low"
            reasoning = "Limited data availability, recommendations based on estimates"
        else:
            level = "Very Low"
            reasoning = "Minimal data available — exercise extra caution"

        return confidence, level, reasoning, factors

    # ─────────────────────────────────────────────────────────────
    # RISK TREND DETECTION
    # ─────────────────────────────────────────────────────────────
    def _detect_risk_trend(self, weather_intel, news_intel, crowd_intel):
        """
        Detects if overall risk is rising, stable, or declining based on signals.
        """
        trend_signals = 0  # positive = rising, negative = declining

        # Weather: active rain or storm → rising
        weather_desc = (weather_intel.get("weather_data", {}).get("description") or "").lower()
        if any(kw in weather_desc for kw in ["storm", "thunder", "heavy rain", "blizzard"]):
            trend_signals += 2
        elif any(kw in weather_desc for kw in ["clear", "sunny", "few clouds"]):
            trend_signals -= 1

        # News: safety risks → rising
        if news_intel and news_intel.get("safety_risks"):
            trend_signals += len(news_intel["safety_risks"])
        if news_intel and news_intel.get("opportunities"):
            trend_signals -= 1

        # Crowd: high → rising
        crowd_score = crowd_intel.get("crowd_score", 5) if crowd_intel else 5
        if crowd_score >= 8:
            trend_signals += 1
        elif crowd_score <= 3:
            trend_signals -= 1

        if trend_signals >= 2:
            return "rising"
        elif trend_signals <= -1:
            return "declining"
        return "stable"

    # ─────────────────────────────────────────────────────────────
    # MAIN RISK FUSION
    # ─────────────────────────────────────────────────────────────
    def fuse_risks(self, weather_intel, news_intel, crowd_intel, mobility_intel,
                   health_intel=None, budget_intel=None, cultural_intel=None,
                   sustainability_intel=None, live_pulse_intel=None, profile=None):
        """
        Aggregates risks from 9 categories into a balanced assessment.
        Total: 100 points across Weather(30), News(25), Crowd(10), Health(10),
        Budget(5), Environment(10), Infrastructure(5), Cultural(3), Temporal(2).
        """
        risks = []
        recommendations = []
        profile = profile or {}
        group_type = (profile.get("group_type") or "").lower()

        # Category scores
        weather_score = 0
        news_score = 0
        crowd_score_pts = 0
        health_score = 0
        budget_score = 0
        environment_score = 0
        infrastructure_score = 0
        cultural_score = 0
        temporal_score = 0

        weather_data = weather_intel.get("weather_data", {}) if weather_intel else {}

        # ═══════════════════════════════════════════════════════════
        # 1. WEATHER RISKS (max 30 points)
        # ═══════════════════════════════════════════════════════════
        rain_prob = weather_data.get("rain_probability", 0)
        temp_c = weather_data.get("temperature_c", 25)
        wind_speed = weather_data.get("wind_speed", 0)
        desc = (weather_data.get("description") or "").lower()

        # Rain
        if rain_prob > 0.7:
            risks.append(self._risk("Weather", "High", "Heavy rain expected — outdoor activities risky.",
                                     "Move activities indoors; pack heavy rain gear."))
            weather_score += 18
        elif rain_prob > 0.4:
            risks.append(self._risk("Weather", "Medium", "Moderate rain chance — carry umbrella.",
                                     "Keep waterproof gear handy; have indoor backup plans."))
            weather_score += 8

        # Extreme temperature
        if temp_c > 42:
            risks.append(self._risk("Weather", "High", f"Extreme heat ({temp_c}°C). Heat stroke risk.",
                                     "Avoid outdoor exposure 11 AM–4 PM; drink water every 15 min."))
            weather_score += 12
        elif temp_c > 35:
            risks.append(self._risk("Weather", "Medium", f"High temperature ({temp_c}°C).",
                                     "Stay hydrated, seek shade, schedule outdoor activities early/late."))
            weather_score += 6

        if temp_c < -5:
            risks.append(self._risk("Weather", "High", f"Extreme cold ({temp_c}°C). Frostbite risk.",
                                     "Wear thermal layers, cover extremities, limit exposure."))
            weather_score += 10
        elif temp_c < 3:
            risks.append(self._risk("Weather", "Medium", f"Cold conditions ({temp_c}°C).",
                                     "Dress warmly in layers; carry hand warmers."))
            weather_score += 4

        # Wind
        if wind_speed > 15:
            risks.append(self._risk("Weather", "Medium", f"Strong winds ({round(wind_speed * 3.6)} km/h).",
                                     "Avoid exposed areas; postpone water sports."))
            weather_score += 5

        # Visibility
        if any(kw in desc for kw in ["fog", "haze", "smoke", "dust"]):
            risks.append(self._risk("Weather", "Low", f"Reduced visibility ({desc}).",
                                     "Use caution while driving; allow extra travel time."))
            weather_score += 3

        # Daylight
        daylight = weather_intel.get("daylight_remaining", 10) if weather_intel else 10
        if daylight < 1:
            risks.append(self._risk("Environment", "High", "Very low daylight remaining.",
                                     "Prioritize well-lit venues; avoid remote travel."))
            weather_score += 10
        elif daylight < 2:
            risks.append(self._risk("Environment", "Medium", "Limited daylight remaining.",
                                     "Wrap up outdoor sightseeing; plan evening activities."))
            weather_score += 4

        weather_score = min(weather_score, 30)

        # ═══════════════════════════════════════════════════════════
        # 2. NEWS / SAFETY RISKS (max 25 points)
        # ═══════════════════════════════════════════════════════════
        if news_intel and "safety_risks" in news_intel:
            for risk in news_intel["safety_risks"]:
                severity = risk.get("severity", "Medium")
                advice = risk.get("actionable_advice", "Monitor local news and stay alert.")
                weight = self.severity_weights.get(severity, 12)
                risks.append(self._risk("News", severity, risk.get("title", "Travel advisory"), advice))
                news_score += weight

        # Scam / crime signals from live pulse
        if live_pulse_intel and not live_pulse_intel.get("error"):
            scam_info = live_pulse_intel.get("scam_alerts", live_pulse_intel.get("safety_tips", ""))
            if scam_info and isinstance(scam_info, str) and len(scam_info) > 10:
                risks.append(self._risk("News", "Low", "Tourist scam reports for this area.",
                                         "Stay alert at tourist hotspots; verify prices beforehand."))
                news_score += 5

        news_score = min(news_score, 25)

        # ═══════════════════════════════════════════════════════════
        # 3. CROWD RISKS (max 10 points)
        # ═══════════════════════════════════════════════════════════
        crowd_level = crowd_intel.get("crowd_score", 0) if crowd_intel else 0
        if crowd_level > 8:
            risks.append(self._risk("Crowd", "High", "Extreme overcrowding expected.",
                                     "Book tickets in advance; arrive at attractions right when they open."))
            crowd_score_pts += 8
        elif crowd_level > 6:
            risks.append(self._risk("Crowd", "Medium", "Moderate to high crowds expected.",
                                     "Expect delays at major attractions; visit alternate spots."))
            crowd_score_pts += 4
        elif crowd_level > 4:
            risks.append(self._risk("Crowd", "Low", "Average crowd levels.",
                                     "Minor wait times possible at popular spots."))
            crowd_score_pts += 2

        crowd_score_pts = min(crowd_score_pts, 10)

        # ═══════════════════════════════════════════════════════════
        # 4. HEALTH RISKS (max 10 points)
        # ═══════════════════════════════════════════════════════════
        if health_intel and not health_intel.get("error"):
            # Water safety
            water_safety = (health_intel.get("water_safety") or "").lower()
            if any(kw in water_safety for kw in ["unsafe", "not safe", "avoid", "bottled only"]):
                risks.append(self._risk("Health", "Medium", "Tap water may be unsafe.",
                                         "Use bottled water for drinking and brushing teeth."))
                health_score += 4

            # Seasonal health risks
            seasonal = (health_intel.get("seasonal_risks") or "").lower()
            if any(kw in seasonal for kw in ["dengue", "malaria", "cholera", "typhoid", "outbreak"]):
                risks.append(self._risk("Health", "High", f"Seasonal health risk: {health_intel.get('seasonal_risks', '')}",
                                         "Use insect repellent, wear long sleeves; consult travel clinic."))
                health_score += 6
            elif any(kw in seasonal for kw in ["flu", "cold", "allergy"]):
                risks.append(self._risk("Health", "Low", f"Minor health concern: {health_intel.get('seasonal_risks', '')}",
                                         "Carry basic medication; wash hands frequently."))
                health_score += 2

            # Vaccinations
            vaccinations = health_intel.get("vaccinations", [])
            if len(vaccinations) >= 4:
                risks.append(self._risk("Health", "Medium", f"Multiple vaccinations recommended ({len(vaccinations)}).",
                                         "Visit travel clinic 4–6 weeks before departure."))
                health_score += 3
            elif len(vaccinations) >= 2:
                health_score += 1

            # Altitude-related health (if present)
            altitude_mention = (health_intel.get("weather_health") or "").lower()
            if "altitude" in altitude_mention or "ams" in altitude_mention:
                risks.append(self._risk("Health", "Medium", "Altitude sickness risk at this destination.",
                                         "Ascend gradually; stay hydrated; avoid heavy exertion on Day 1."))
                health_score += 3

        health_score = min(health_score, 10)

        # ═══════════════════════════════════════════════════════════
        # 5. BUDGET STRESS (max 5 points)
        # ═══════════════════════════════════════════════════════════
        if budget_intel and not budget_intel.get("error"):
            feasibility = (budget_intel.get("feasibility") or "").lower()
            if feasibility == "low":
                risks.append(self._risk("Budget", "Medium", "Budget may be tight for this destination.",
                                         "Eat away from tourist centers; use public transit."))
                budget_score += 4
            elif feasibility == "moderate":
                budget_score += 1

            # Price surge detection
            price_trend = (budget_intel.get("price_trend") or "").lower()
            if "surge" in price_trend or "peak" in price_trend or "high season" in price_trend:
                risks.append(self._risk("Budget", "Low", "Peak pricing detected for this period.",
                                         "Book accommodation and transport in advance for better rates."))
                budget_score += 2

        budget_score = min(budget_score, 5)

        # ═══════════════════════════════════════════════════════════
        # 6. ENVIRONMENT RISKS (max 10 points) — NEW
        # ═══════════════════════════════════════════════════════════
        # Natural disaster season
        if any(kw in desc for kw in ["storm", "cyclone", "hurricane", "tornado"]):
            risks.append(self._risk("Environment", "Critical", f"Severe weather event: {desc}.",
                                     "Seek shelter immediately. Follow local emergency instructions."))
            environment_score += 10

        # AQI / air quality from description
        if any(kw in desc for kw in ["smoke", "dust"]):
            risks.append(self._risk("Environment", "Medium", "Poor air quality detected.",
                                     "Wear N95 mask outdoors; limit strenuous outdoor activity."))
            environment_score += 5

        # Terrain hazards (monsoon + mountain)
        if sustainability_intel and not sustainability_intel.get("error"):
            terrain_info = (sustainability_intel.get("terrain") or sustainability_intel.get("geography") or "").lower()
            if rain_prob > 0.5 and any(kw in terrain_info for kw in ["mountain", "hill", "slope"]):
                risks.append(self._risk("Environment", "High", "Rain + mountain terrain = landslide risk.",
                                         "Avoid hillside roads; check local disaster bulletins."))
                environment_score += 7

        environment_score = min(environment_score, 10)

        # ═══════════════════════════════════════════════════════════
        # 7. INFRASTRUCTURE RISKS (max 5 points) — NEW
        # ═══════════════════════════════════════════════════════════
        if health_intel and not health_intel.get("error"):
            medical = (health_intel.get("medical_facilities") or "").lower()
            if any(kw in medical for kw in ["limited", "no hospital", "far", "basic", "remote"]):
                risks.append(self._risk("Infrastructure", "Medium", "Limited medical facilities at destination.",
                                         "Carry a first-aid kit and note the nearest city hospital."))
                infrastructure_score += 3

        if sustainability_intel and not sustainability_intel.get("error"):
            connectivity = (sustainability_intel.get("connectivity") or "").lower()
            if any(kw in connectivity for kw in ["poor", "no signal", "limited", "remote"]):
                risks.append(self._risk("Infrastructure", "Low", "Limited connectivity (mobile/internet).",
                                         "Download offline maps and emergency contacts before departure."))
                infrastructure_score += 2

        infrastructure_score = min(infrastructure_score, 5)

        # ═══════════════════════════════════════════════════════════
        # 8. CULTURAL RISKS (max 3 points) — NEW
        # ═══════════════════════════════════════════════════════════
        if cultural_intel and not cultural_intel.get("error"):
            etiquette = cultural_intel.get("etiquette_donts", cultural_intel.get("taboos", []))
            if etiquette and len(etiquette) >= 3:
                risks.append(self._risk("Cultural", "Low", "Several cultural sensitivities to be aware of.",
                                         "Review local customs — dress modestly near religious sites."))
                cultural_score += 2

            restricted = cultural_intel.get("restricted_areas", "")
            if restricted:
                risks.append(self._risk("Cultural", "Low", "Some areas may have access restrictions.",
                                         "Check local rules for photography, entry permits, and dress codes."))
                cultural_score += 1

        cultural_score = min(cultural_score, 3)

        # ═══════════════════════════════════════════════════════════
        # 9. TEMPORAL RISKS (max 2 points) — NEW
        # ═══════════════════════════════════════════════════════════
        # Penalize if data sources are stale or off-season
        if weather_intel and weather_intel.get("data_age_minutes", 0) > 180:
            temporal_score += 1
            risks.append(self._risk("Temporal", "Low", "Weather data is over 3 hours old.",
                                     "Refresh data before making outdoor plans."))

        if not live_pulse_intel or live_pulse_intel.get("error"):
            temporal_score += 1

        temporal_score = min(temporal_score, 2)

        # ═══════════════════════════════════════════════════════════
        # TOTAL SCORE & VERDICT
        # ═══════════════════════════════════════════════════════════
        total_score = (weather_score + news_score + crowd_score_pts + health_score +
                       budget_score + environment_score + infrastructure_score +
                       cultural_score + temporal_score)
        total_score = min(total_score, 100)

        if total_score >= 70:
            verdict = "Critical"
        elif total_score >= 50:
            verdict = "Unsafe"
        elif total_score >= 25:
            verdict = "Caution"
        else:
            verdict = "Safe"

        # Group-type adjustment
        if ("famil" in group_type or "child" in group_type or "elder" in group_type):
            if verdict == "Caution":
                verdict = "Caution (Extra Care)"

        # Trend detection
        trend = self._detect_risk_trend(weather_intel or {}, news_intel or {}, crowd_intel or {})

        # Confidence
        confidence, conf_level, conf_reasoning, conf_factors = self._calculate_confidence(
            weather_intel, news_intel, crowd_intel, mobility_intel,
            health_intel, budget_intel, cultural_intel,
            sustainability_intel, live_pulse_intel
        )

        # Deduplicate recommendations
        unique_recs = list(dict.fromkeys(r.get("action", "") for r in risks if r.get("action")))

        return {
            "total_risk_score": total_score,
            "risk_factors": risks,
            "actionable_recommendations": unique_recs,
            "verdict": verdict,
            "trending": trend,
            "breakdown": {
                "weather": weather_score,
                "news": news_score,
                "crowd": crowd_score_pts,
                "health": health_score,
                "budget": budget_score,
                "environment": environment_score,
                "infrastructure": infrastructure_score,
                "cultural": cultural_score,
                "temporal": temporal_score
            },
            "confidence": {
                "score": round(confidence, 2),
                "level": conf_level,
                "reasoning": conf_reasoning,
                "factors": conf_factors
            }
        }

    def _risk(self, source, level, message, action=""):
        """Helper to build a consistent risk dict."""
        return {
            "source": source,
            "level": level,
            "message": message,
            "action": action
        }
