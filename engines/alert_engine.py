import logging
from datetime import datetime

logger = logging.getLogger("wanderx.alert_engine")

SEVERITY_PRIORITY = {
    "critical": 4,
    "high": 3,
    "warning": 2,
    "info": 1,
}

ALERT_ICONS = {
    "Weather": "🌦️",
    "Heat": "🌡️",
    "Cold": "🥶",
    "Wind": "🌬️",
    "Visibility": "🌫️",
    "Daylight": "🌅",
    "Crowd": "👥",
    "Safety": "🚨",
    "Health": "🩺",
    "Budget": "💸",
    "Mobility": "🛣️",
    "Connectivity": "📶",
    "Live Pulse": "📡",
}


class AlertEngine:
    """
    RTRIE Alert System
    - Real-time, signal-driven, non-generic alerts
    - Deduplicated and prioritized outputs
    - Includes automation hints for downstream channels (SMS/Push/Email/UI)
    """

    def generate_alerts(self, context, profile=None):
        profile = profile or {}
        now_iso = datetime.now().isoformat()

        weather_intel = context.get("weather_intel") or {}
        news_intel = context.get("news_intel") or {}
        crowd_intel = context.get("crowd_intel") or {}
        health_intel = context.get("health_intel") or {}
        budget_intel = context.get("budget_intel") or {}
        sustainability_intel = context.get("sustainability_intel") or {}
        mobility_intel = context.get("mobility_intel") or {}
        live_pulse_intel = context.get("live_pulse_intel") or {}

        weather = weather_intel.get("weather_data") or {}
        alerts = []

        def add_alert(level, category, message, action, risk_score, source="engine"):
            alerts.append(self._build_alert(
                level=level,
                category=category,
                message=message,
                action=action,
                risk_score=risk_score,
                source=source,
                created_at=now_iso,
            ))

        # 1) Weather + environmental alerts
        if weather and not weather.get("error"):
            temp = weather.get("temperature_c", 25)
            feels_like = weather.get("feels_like_c", temp)
            rain_prob = weather.get("rain_probability", 0)
            wind_ms = weather.get("wind_speed", 0)
            visibility_km = weather.get("visibility_km", 10)
            humidity = weather.get("humidity", 50)
            heat_index = weather.get("heat_index_c")
            wind_chill = weather.get("wind_chill_c")
            desc = (weather.get("description") or "").lower()

            if rain_prob >= 0.85:
                add_alert(
                    "high",
                    "Weather",
                    f"Heavy precipitation signal ({int(rain_prob * 100)}%) with '{desc}'.",
                    "Auto-switch outdoor blocks to indoor backup and move commute 30-60 min earlier.",
                    76,
                    "weather",
                )
            elif rain_prob >= 0.60:
                add_alert(
                    "warning",
                    "Weather",
                    f"Rain risk is elevated ({int(rain_prob * 100)}%).",
                    "Keep waterproof gear ready and protect transit-dependent activities.",
                    52,
                    "weather",
                )

            if heat_index is not None and heat_index >= 40:
                add_alert(
                    "critical",
                    "Heat",
                    f"Dangerous heat stress: air {temp}°C, feels like {feels_like}°C, heat index {heat_index}°C.",
                    "Stop midday outdoor blocks; enforce hydration every 20 min and shade-only routing.",
                    90,
                    "weather",
                )
            elif temp >= 37 or (heat_index is not None and heat_index >= 36):
                add_alert(
                    "high",
                    "Heat",
                    f"High heat detected: {temp}°C (humidity {humidity}%).",
                    "Move high-exertion activities to morning/evening windows.",
                    70,
                    "weather",
                )

            if wind_chill is not None and wind_chill <= -10:
                add_alert(
                    "critical",
                    "Cold",
                    f"Severe cold stress: temp {temp}°C, wind chill {wind_chill}°C.",
                    "Limit exposure to <20 min windows and prioritize heated indoor transitions.",
                    88,
                    "weather",
                )
            elif temp <= 3:
                add_alert(
                    "warning",
                    "Cold",
                    f"Cold condition: {temp}°C (wind {round(wind_ms * 3.6)} km/h).",
                    "Use layered clothing and shorten static waiting times.",
                    48,
                    "weather",
                )

            if wind_ms >= 15:
                add_alert(
                    "high",
                    "Wind",
                    f"Strong wind event: {round(wind_ms * 3.6)} km/h gust risk.",
                    "Avoid exposed viewpoints, rooftop venues, and open-water activities.",
                    68,
                    "weather",
                )

            if visibility_km <= 1.2 or any(k in desc for k in ["fog", "smoke", "haze", "dust"]):
                add_alert(
                    "warning",
                    "Visibility",
                    f"Reduced visibility detected ({visibility_km} km).",
                    "Increase transfer buffers by 20-30 minutes and prefer major roads/transit hubs.",
                    45,
                    "weather",
                )

        # 2) Daylight urgency
        daylight = weather_intel.get("daylight_remaining")
        if daylight is not None:
            if daylight <= 0.5:
                add_alert(
                    "high",
                    "Daylight",
                    f"Only {int(daylight * 60)} minutes of daylight left.",
                    "Trigger safe-return flow to accommodation and freeze new outdoor starts.",
                    74,
                    "time",
                )
            elif daylight <= 1.5:
                add_alert(
                    "warning",
                    "Daylight",
                    f"Low daylight remaining: {daylight:.1f}h.",
                    "Wrap outdoor sequence and switch to indoor/evening-safe itinerary.",
                    40,
                    "time",
                )

        # 3) Crowd density
        crowd_score = crowd_intel.get("crowd_score", 0)
        if crowd_score >= 8:
            add_alert(
                "high",
                "Crowd",
                f"Crowd surge index is {crowd_score}/10.",
                "Activate anti-crowd routing and reservation-first sequencing.",
                66,
                "crowd",
            )
        elif crowd_score >= 6:
            add_alert(
                "warning",
                "Crowd",
                f"Crowd pressure is moderate-high ({crowd_score}/10).",
                "Shift top attractions to off-peak windows.",
                42,
                "crowd",
            )

        # 4) News-based safety advisories
        for risk in (news_intel.get("safety_risks") or [])[:4]:
            sev = (risk.get("severity") or "Medium").lower()
            level = "critical" if sev == "high" else "high" if sev == "medium" else "warning"
            msg = risk.get("title") or "Active travel advisory"
            advice = risk.get("actionable_advice") or "Monitor official local channels before moving."
            score = 88 if level == "critical" else 70 if level == "high" else 50
            add_alert(level, "Safety", msg, advice, score, "news")

        # 5) Health + water risk
        if health_intel and not health_intel.get("error"):
            seasonal = (health_intel.get("seasonal_risks") or "").lower()
            water = (health_intel.get("water_safety") or "").lower()
            if any(k in seasonal for k in ["outbreak", "dengue", "cholera", "malaria", "epidemic"]):
                add_alert(
                    "critical",
                    "Health",
                    f"Health threat detected: {health_intel.get('seasonal_risks', 'outbreak pattern')}",
                    "Use prevention protocol (repellent, long sleeves, hygiene barriers) and carry meds.",
                    92,
                    "health",
                )
            if any(k in water for k in ["unsafe", "avoid", "not safe", "bottled"]):
                add_alert(
                    "high",
                    "Health",
                    "Water safety warning: local tap-water intake risk.",
                    "Use sealed bottled water for drinking and oral care.",
                    67,
                    "health",
                )

        # 6) Budget volatility
        if budget_intel and not budget_intel.get("error"):
            feasibility = (budget_intel.get("feasibility") or "").lower()
            trend = (budget_intel.get("price_trend") or "").lower()
            if feasibility == "low" or any(k in trend for k in ["surge", "spike", "peak"]):
                add_alert(
                    "warning",
                    "Budget",
                    "Spend-risk increased due to tight feasibility or surge pricing.",
                    "Switch transport/meals to local-value options and pre-book fixed-cost segments.",
                    44,
                    "budget",
                )

        # 7) Mobility and connectivity
        travel_time = mobility_intel.get("travel_time")
        if isinstance(travel_time, (int, float)) and travel_time >= 2.5:
            add_alert(
                "warning",
                "Mobility",
                f"Long transit window detected ({travel_time:.1f}h).",
                "Re-sequence itinerary to reduce cross-city hops and time fragmentation.",
                43,
                "mobility",
            )

        if sustainability_intel and not sustainability_intel.get("error"):
            conn = (sustainability_intel.get("connectivity") or "").lower()
            if any(k in conn for k in ["poor", "limited", "no signal", "remote"]):
                add_alert(
                    "warning",
                    "Connectivity",
                    "Connectivity reliability is low in planned zones.",
                    "Pre-cache maps/tickets and share offline meeting checkpoints.",
                    40,
                    "sustainability",
                )

        # 8) Live pulse chaos detection (real-time disruptions)
        chaos = live_pulse_intel.get("chaos") or live_pulse_intel.get("disruptions") or {}
        chaos_status = (chaos.get("status") or "").lower()
        chaos_alerts = chaos.get("alerts") or []

        if chaos_status in ("danger", "warning"):
            for disruption in chaos_alerts[:3]:
                sev = (disruption.get("severity") or "medium").lower()
                level = "critical" if sev == "high" or chaos_status == "danger" else "high"
                add_alert(
                    level,
                    "Live Pulse",
                    disruption.get("title") or disruption.get("details") or "Live disruption detected",
                    "Follow verified local authority guidance and avoid impacted corridors.",
                    85 if level == "critical" else 64,
                    "live_pulse",
                )

        # Deduplicate and prioritize
        deduped = self._dedupe_alerts(alerts)
        deduped.sort(
            key=lambda a: (SEVERITY_PRIORITY.get(a.get("type", "info"), 0), a.get("risk_score", 0)),
            reverse=True,
        )
        return deduped

    def _build_alert(self, level, category, message, action, risk_score, source, created_at):
        icon = ALERT_ICONS.get(category, "ℹ️")
        ttl_min = 20 if level in ("critical", "high") else 45 if level == "warning" else 90

        return {
            "type": level,
            "title": category,
            "icon": icon,
            "message": message,
            "action": action,
            "priority": SEVERITY_PRIORITY.get(level, 1),
            "risk_score": int(risk_score),
            "source": source,
            "created_at": created_at,
            "ttl_minutes": ttl_min,
            "channel_payload": {
                "sms": f"{icon} {category}: {message}",
                "push": f"{category} alert · {message}",
                "email_subject": f"WanderX {category} Alert ({level.upper()})",
            },
        }

    def _dedupe_alerts(self, alerts):
        seen = set()
        unique = []
        for alert in alerts:
            key = (
                (alert.get("title") or "").strip().lower(),
                (alert.get("message") or "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(alert)
        return unique
