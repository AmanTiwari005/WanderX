import logging
from datetime import datetime

logger = logging.getLogger("wanderx.risk_fusion")


class RiskFusionEngine:
    """
    RTRIE Risk Intelligence Engine
    - Fuses multi-source real-time signals
    - Produces probability-like risk score (0-100)
    - Returns confidence, trend, and automated recommendations
    """

    DIMENSION_WEIGHTS = {
        "weather": 0.24,
        "news": 0.22,
        "crowd": 0.10,
        "health": 0.14,
        "mobility": 0.08,
        "budget": 0.05,
        "infrastructure": 0.07,
        "live_pulse": 0.10,
    }

    def fuse_risks(
        self,
        weather_intel,
        news_intel,
        crowd_intel,
        mobility_intel,
        health_intel=None,
        budget_intel=None,
        cultural_intel=None,
        sustainability_intel=None,
        live_pulse_intel=None,
        profile=None,
    ):
        profile = profile or {}
        weather_intel = weather_intel or {}
        news_intel = news_intel or {}
        crowd_intel = crowd_intel or {}
        mobility_intel = mobility_intel or {}
        health_intel = health_intel or {}
        budget_intel = budget_intel or {}
        sustainability_intel = sustainability_intel or {}
        live_pulse_intel = live_pulse_intel or {}

        weather = weather_intel.get("weather_data") or {}

        factors = []
        recommendations = []
        breakdown = {k: 0 for k in self.DIMENSION_WEIGHTS}

        # 1) WEATHER
        weather_score = 0
        rain_prob = weather.get("rain_probability", 0)
        temp = weather.get("temperature_c", 25)
        wind = weather.get("wind_speed", 0)
        vis = weather.get("visibility_km", 10)
        desc = (weather.get("description") or "").lower()

        if rain_prob >= 0.85:
            weather_score += 35
            factors.append(self._risk("Weather", "High", f"Severe precipitation risk ({int(rain_prob * 100)}%).", "weather"))
            recommendations.append("Shift outdoor blocks to indoor alternatives for this time window.")
        elif rain_prob >= 0.60:
            weather_score += 18
            factors.append(self._risk("Weather", "Medium", f"Elevated rain probability ({int(rain_prob * 100)}%).", "weather"))

        if temp >= 40:
            weather_score += 35
            factors.append(self._risk("Weather", "Critical", f"Extreme heat at {temp}°C.", "weather"))
            recommendations.append("Avoid midday outdoor movement; enforce hydration cadence.")
        elif temp >= 36:
            weather_score += 18
            factors.append(self._risk("Weather", "High", f"High heat at {temp}°C.", "weather"))

        if temp <= -2:
            weather_score += 28
            factors.append(self._risk("Weather", "High", f"Freezing exposure risk at {temp}°C.", "weather"))
        elif temp <= 4:
            weather_score += 12
            factors.append(self._risk("Weather", "Medium", f"Cold weather pressure at {temp}°C.", "weather"))

        if wind >= 15:
            weather_score += 16
            factors.append(self._risk("Weather", "High", f"Strong winds {round(wind * 3.6)} km/h.", "weather"))

        if vis <= 1.2 or any(k in desc for k in ["fog", "smoke", "haze", "dust"]):
            weather_score += 12
            factors.append(self._risk("Weather", "Medium", f"Low visibility ({vis} km).", "weather"))

        daylight = weather_intel.get("daylight_remaining")
        if daylight is not None and daylight <= 0.5:
            weather_score += 16
            factors.append(self._risk("Temporal", "High", "Daylight nearly exhausted.", "weather"))
        elif daylight is not None and daylight <= 1.5:
            weather_score += 8
            factors.append(self._risk("Temporal", "Medium", "Low daylight buffer.", "weather"))

        breakdown["weather"] = min(weather_score, 100)

        # 2) NEWS / SAFETY
        news_score = 0
        critical_override = False
        for risk in (news_intel.get("safety_risks") or [])[:5]:
            sev = (risk.get("severity") or "Medium").lower()
            if sev == "critical":
                news_score += 100
                level = "Critical"
                critical_override = True
            elif sev == "high":
                news_score += 65
                level = "High"
                if "attack" in str(risk).lower() or "bomb" in str(risk).lower() or "evacuat" in str(risk).lower():
                    critical_override = True
                    news_score += 100
            elif sev == "medium":
                news_score += 25
                level = "Medium"
            else:
                news_score += 10
                level = "Low"
            factors.append(self._risk("News", level, risk.get("title", "Travel advisory"), "news"))
            advice = risk.get("actionable_advice")
            if advice:
                recommendations.append(advice)

        breakdown["news"] = min(news_score, 100)

        # 3) CROWD
        crowd_score_raw = crowd_intel.get("crowd_score", 0)
        crowd_score = int(min(100, max(0, crowd_score_raw * 11)))
        if crowd_score_raw >= 8:
            factors.append(self._risk("Crowd", "High", f"Crowd surge index {crowd_score_raw}/10.", "crowd"))
            recommendations.append("Reorder itinerary toward low-density zones or off-peak windows.")
        elif crowd_score_raw >= 6:
            factors.append(self._risk("Crowd", "Medium", f"Crowd pressure {crowd_score_raw}/10.", "crowd"))
        breakdown["crowd"] = crowd_score

        # 4) HEALTH
        health_score = 0
        if health_intel and not health_intel.get("error"):
            seasonal = (health_intel.get("seasonal_risks") or "").lower()
            water = (health_intel.get("water_safety") or "").lower()

            if any(k in seasonal for k in ["outbreak", "dengue", "cholera", "malaria", "epidemic"]):
                health_score += 55
                factors.append(self._risk("Health", "Critical", f"Seasonal health risk: {health_intel.get('seasonal_risks', '')}", "health"))
                recommendations.append("Apply prevention protocol and carry an active medical fallback plan.")
            elif seasonal:
                health_score += 20
                factors.append(self._risk("Health", "Medium", f"Health advisory: {health_intel.get('seasonal_risks', '')}", "health"))

            if any(k in water for k in ["unsafe", "avoid", "not safe", "bottled"]):
                health_score += 25
                factors.append(self._risk("Health", "High", "Water safety risk detected.", "health"))

            vacc = health_intel.get("vaccinations") or []
            if len(vacc) >= 4:
                health_score += 10

        breakdown["health"] = min(health_score, 100)

        # 5) MOBILITY
        mobility_score = 0
        travel_time = mobility_intel.get("travel_time")
        if isinstance(travel_time, (int, float)):
            if travel_time >= 4:
                mobility_score += 50
                factors.append(self._risk("Mobility", "High", f"Long transfer time ({travel_time:.1f}h).", "mobility"))
            elif travel_time >= 2:
                mobility_score += 28
                factors.append(self._risk("Mobility", "Medium", f"Moderate transfer time ({travel_time:.1f}h).", "mobility"))

        breakdown["mobility"] = min(mobility_score, 100)

        # 6) BUDGET
        budget_score = 0
        if budget_intel and not budget_intel.get("error"):
            feasibility = (budget_intel.get("feasibility") or "").lower()
            trend = (budget_intel.get("price_trend") or "").lower()
            if feasibility == "low":
                budget_score += 60
                factors.append(self._risk("Budget", "Medium", "Trip budget feasibility is low.", "budget"))
            elif feasibility in ("moderate", "medium"):
                budget_score += 25

            if any(k in trend for k in ["surge", "peak", "spike"]):
                budget_score += 20
                recommendations.append("Lock major bookings early to reduce volatility exposure.")

        breakdown["budget"] = min(budget_score, 100)

        # 7) INFRASTRUCTURE
        infra_score = 0
        conn = (sustainability_intel.get("connectivity") or "").lower()
        if any(k in conn for k in ["poor", "limited", "no signal", "remote"]):
            infra_score += 45
            factors.append(self._risk("Infrastructure", "Medium", "Low connectivity reliability.", "sustainability"))
            recommendations.append("Preload offline maps/tickets and establish offline rendezvous points.")

        medical = (health_intel.get("medical_facilities") or "").lower() if health_intel else ""
        if any(k in medical for k in ["limited", "remote", "basic", "far"]):
            infra_score += 35
            factors.append(self._risk("Infrastructure", "High", "Limited nearby medical facilities.", "health"))

        breakdown["infrastructure"] = min(infra_score, 100)

        # 8) LIVE PULSE / REAL-TIME DISRUPTIONS
        pulse_score = 0
        chaos = live_pulse_intel.get("chaos") or {}
        chaos_status = (chaos.get("status") or "").lower()
        chaos_alerts = chaos.get("alerts") or []

        if chaos_status == "danger":
            pulse_score += 100
            critical_override = True
            factors.append(self._risk("Live Pulse", "Critical", "Active disruption cluster detected.", "live_pulse"))
        elif chaos_status == "warning":
            pulse_score += 45
            factors.append(self._risk("Live Pulse", "High", "Emerging disruption signals detected.", "live_pulse"))

        for entry in chaos_alerts[:3]:
            sev = (entry.get("severity") or "medium").lower()
            pulse_score += 12 if sev == "high" else 7
            factors.append(self._risk("Live Pulse", "High" if sev == "high" else "Medium", entry.get("title") or entry.get("details") or "Live disruption", "live_pulse"))

        breakdown["live_pulse"] = min(pulse_score, 100)

        # Weighted aggregate risk probability
        total_score = 0.0
        for dim, weight in self.DIMENSION_WEIGHTS.items():
            total_score += breakdown[dim] * weight
            
        if critical_override:
            # Force severe risk escalation regardless of good weather
            total_score = max(total_score, 85)
            
        total_score = round(max(0, min(100, total_score)))

        # Profile-based tightening for vulnerable groups
        group_type = (profile.get("group_type") or "").lower()
        if any(k in group_type for k in ["elder", "senior", "family", "child", "kid"]):
            total_score = min(100, total_score + 5)

        verdict = self._verdict(total_score)
        trend = self._detect_trend(weather_intel, news_intel, crowd_intel, live_pulse_intel)
        confidence = self._confidence(weather_intel, news_intel, crowd_intel, mobility_intel, live_pulse_intel)

        dedup_recs = list(dict.fromkeys(r for r in recommendations if r and isinstance(r, str)))

        return {
            "total_risk_score": total_score,
            "verdict": verdict,
            "risk_probability": round(total_score / 100, 2),
            "risk_factors": factors,
            "actionable_recommendations": dedup_recs[:12],
            "trending": trend,
            "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
            "confidence": confidence,
            "generated_at": datetime.now().isoformat(),
        }

    def _risk(self, source, level, message, signal_source):
        return {
            "source": source,
            "level": level,
            "message": message,
            "signal_source": signal_source,
        }

    def _verdict(self, score):
        if score >= 75:
            return "Critical"
        if score >= 55:
            return "Unsafe"
        if score >= 35:
            return "Caution"
        return "Safe"

    def _detect_trend(self, weather_intel, news_intel, crowd_intel, live_pulse_intel):
        signals = 0

        rain_prob = (weather_intel.get("weather_data") or {}).get("rain_probability", 0)
        if rain_prob >= 0.75:
            signals += 1

        if len(news_intel.get("safety_risks") or []) >= 2:
            signals += 1

        if (crowd_intel.get("crowd_score") or 0) >= 8:
            signals += 1

        chaos_status = ((live_pulse_intel.get("chaos") or {}).get("status") or "").lower()
        if chaos_status in ("warning", "danger"):
            signals += 1

        if signals >= 3:
            return "rising"
        if signals == 0:
            return "declining"
        return "stable"

    def _confidence(self, weather_intel, news_intel, crowd_intel, mobility_intel, live_pulse_intel):
        score = 1.0
        factors = []

        if not weather_intel or weather_intel.get("error"):
            score -= 0.20
            factors.append("Missing weather feed")
        else:
            factors.append("Weather feed live")

        if not news_intel or news_intel.get("error"):
            score -= 0.15
            factors.append("Limited news feed")
        else:
            factors.append("News feed active")

        if "crowd_score" not in (crowd_intel or {}):
            score -= 0.10
            factors.append("Crowd score unavailable")
        else:
            factors.append("Crowd signal available")

        if not mobility_intel:
            score -= 0.07
            factors.append("Mobility signal unavailable")
        else:
            factors.append("Mobility signal available")

        if not live_pulse_intel or live_pulse_intel.get("error"):
            score -= 0.12
            factors.append("Live pulse limited")
        else:
            factors.append("Live pulse active")

        score = max(0.0, min(1.0, score))
        level = "High" if score >= 0.8 else "Medium" if score >= 0.6 else "Low"

        return {
            "score": round(score, 2),
            "level": level,
            "reasoning": "Real-time fusion confidence based on feed quality and completeness.",
            "factors": factors,
        }
