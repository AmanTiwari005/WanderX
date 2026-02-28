"""
Global Travel Score for WanderX.

A single 0–100 composite score answering "How good is this trip right now?"
across 6 weighted dimensions: Safety, Weather, Crowd, Budget, Experience, Logistics.
"""
import logging

logger = logging.getLogger("wanderx.travel_score")


class TravelScore:
    """
    Computes a unified 0–100 TravelScore across 6 dimensions.
    """

    # Dimension weights (must sum to 1.0)
    WEIGHTS = {
        "safety": 0.30,
        "weather": 0.20,
        "crowd_comfort": 0.10,
        "budget_health": 0.15,
        "experience_potential": 0.15,
        "logistics": 0.10,
    }

    BANDS = [
        (80, 100, "Perfect Trip", "🌟", "#00E676"),
        (60, 79,  "Good to Go",   "✅", "#66BB6A"),
        (40, 59,  "Proceed with Caution", "⚠️", "#FFC400"),
        (0,  39,  "Consider Alternatives", "🔴", "#FF1744"),
    ]

    @classmethod
    def calculate(cls, risk_assessment=None, weather_intel=None, crowd_intel=None,
                  budget_intel=None, news_intel=None, cultural_intel=None,
                  sustainability_intel=None, live_pulse_intel=None, profile=None):
        """
        Calculate the composite TravelScore.
        
        Returns:
            dict: {score, band, label, icon, color, breakdown, recommendations}
        """
        dimensions = {}
        recommendations = []

        # 1. SAFETY (30%) — inverse of risk score
        risk_score = 0
        if risk_assessment:
            risk_score = risk_assessment.get("total_risk_score", 0)
        safety_score = max(0, 100 - risk_score)
        dimensions["safety"] = safety_score
        if safety_score < 40:
            recommendations.append("Safety concerns detected — review risk assessment before proceeding.")

        # 2. WEATHER (20%) — temperature comfort + precipitation
        weather_score = 70  # default
        if weather_intel and not weather_intel.get("error"):
            weather_data = weather_intel.get("weather_data", {})
            temp_c = weather_data.get("temperature_c", 25)
            rain_prob = weather_data.get("rain_probability", 0)
            wind = weather_data.get("wind_speed", 0)
            desc = (weather_data.get("description") or "").lower()

            # Temperature comfort (ideal 18–28°C)
            if 18 <= temp_c <= 28:
                temp_comfort = 100
            elif 10 <= temp_c <= 35:
                temp_comfort = 70
            elif 5 <= temp_c <= 40:
                temp_comfort = 40
            else:
                temp_comfort = 15

            # Rain penalty
            rain_penalty = min(40, rain_prob * 50) if rain_prob > 0.3 else 0

            # Wind penalty
            wind_penalty = min(20, max(0, (wind - 8) * 3)) if wind > 8 else 0

            # Storm penalty
            storm_penalty = 30 if any(kw in desc for kw in ["storm", "thunder", "cyclone"]) else 0

            weather_score = max(0, temp_comfort - rain_penalty - wind_penalty - storm_penalty)
            if weather_score < 50:
                recommendations.append("Weather conditions are challenging — consider indoor alternatives.")

        dimensions["weather"] = weather_score

        # 3. CROWD COMFORT (10%) — inverse of crowd density
        crowd_score = 70  # default
        if crowd_intel and not crowd_intel.get("error"):
            cs = crowd_intel.get("crowd_score", 5)
            crowd_score = max(0, 100 - (cs * 10))
            if cs >= 8:
                recommendations.append("Extreme crowds expected — visit early or explore alternatives.")
        dimensions["crowd_comfort"] = crowd_score

        # 4. BUDGET HEALTH (15%)
        budget_score = 70  # default
        if budget_intel and not budget_intel.get("error"):
            feasibility = (budget_intel.get("feasibility") or "").lower()
            if feasibility == "high":
                budget_score = 95
            elif feasibility in ("moderate", "medium"):
                budget_score = 70
            elif feasibility == "low":
                budget_score = 30
                recommendations.append("Budget is tight — look for free activities and local eateries.")
            else:
                budget_score = 60
        dimensions["budget_health"] = budget_score

        # 5. EXPERIENCE POTENTIAL (15%) — events, interests match, culture
        experience_score = 50  # default
        exp_factors = 0

        if news_intel and not news_intel.get("error"):
            opportunities = news_intel.get("opportunities", [])
            if len(opportunities) >= 2:
                exp_factors += 30
            elif len(opportunities) == 1:
                exp_factors += 15

            facts = news_intel.get("interesting_facts", [])
            if facts:
                exp_factors += 10

        if cultural_intel and not cultural_intel.get("error"):
            exp_factors += 15

        if profile and profile.get("interests"):
            exp_factors += 10  # Having interests = better matching

        experience_score = min(100, 40 + exp_factors)
        dimensions["experience_potential"] = experience_score

        # 6. LOGISTICS (10%) — connectivity, daylight, reachability
        logistics_score = 70  # default
        logi_penalties = 0

        if weather_intel:
            daylight = weather_intel.get("daylight_remaining")
            if daylight is not None and daylight < 2:
                logi_penalties += 20
            if daylight is not None and daylight < 0.5:
                logi_penalties += 20

        if sustainability_intel and not sustainability_intel.get("error"):
            connectivity = (sustainability_intel.get("connectivity") or "").lower()
            if any(kw in connectivity for kw in ["poor", "no signal", "limited"]):
                logi_penalties += 15
                recommendations.append("Limited connectivity — download offline maps and key info.")

        logistics_score = max(0, 90 - logi_penalties)
        dimensions["logistics"] = logistics_score

        # ── COMPOSITE SCORE ───────────────────────────────────
        composite = sum(
            dimensions[dim] * cls.WEIGHTS[dim]
            for dim in cls.WEIGHTS
        )
        composite = round(max(0, min(100, composite)))

        # Determine band
        band_label = "Unknown"
        band_icon = "❓"
        band_color = "#999"
        for low, high, label, icon, color in cls.BANDS:
            if low <= composite <= high:
                band_label = label
                band_icon = icon
                band_color = color
                break

        return {
            "score": composite,
            "band": band_label,
            "icon": band_icon,
            "color": band_color,
            "breakdown": {k: round(v) for k, v in dimensions.items()},
            "weights": cls.WEIGHTS,
            "recommendations": recommendations
        }
