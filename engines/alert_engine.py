import logging

logger = logging.getLogger("wanderx.alert_engine")

# Priority: higher = more urgent
SEVERITY_PRIORITY = {"critical": 3, "warning": 2, "info": 1}

# Icon mapping per alert category
ALERT_ICONS = {
    "Weather": "🌧️",
    "High Heat": "🌡️",
    "Cold Snap": "🥶",
    "Wind": "🌬️",
    "UV Index": "☀️",
    "Air Quality": "🫁",
    "Visibility": "🌫️",
    "Crowd": "👥",
    "Safety Advisory": "🚨",
    "Event": "🎉",
    "Health Outbreak": "🦠",
    "Vaccination": "💉",
    "Water Safety": "💧",
    "Budget Stress": "💸",
    "Cultural": "🕌",
    "Connectivity": "📶",
    "Altitude": "⛰️",
    "Daylight": "🌅",
}


class AlertEngine:
    def generate_alerts(self, context, profile=None):
        """
        Analyzes multi-source intelligence to generate proactive, prioritized alerts.

        Args:
            context (dict): Contains weather_intel, news_intel, crowd_intel, 
                            health_intel, budget_intel, cultural_intel,
                            sustainability_intel, live_pulse_intel, mobility_intel.
            profile (dict): User profile with interests, group_type, travelers, etc.

        Returns:
            list: Sorted list of alert dicts with type, title, message, icon, action, priority.
        """
        alerts = []
        profile = profile or {}
        group_type = (profile.get("group_type") or "").lower()
        has_kids = "famil" in group_type or "child" in group_type or "kid" in group_type
        has_elderly = "elder" in group_type or "senior" in group_type

        # ── 1. Weather Alerts ──────────────────────────────────────────
        weather_data = context.get("weather_intel", {}).get("weather_data", {})
        if weather_data and not weather_data.get("error"):
            desc = (weather_data.get("description") or "").lower()
            temp_c = weather_data.get("temperature_c", 20)
            feels_like = weather_data.get("feels_like_c", temp_c)
            rain_mm = weather_data.get("rain_probability", 0)

            # Rain / Storm / Snow
            if any(kw in desc for kw in ["rain", "storm", "drizzle", "shower", "thunder"]):
                alerts.append(self._alert(
                    "warning", "Weather",
                    f"Expect {desc}. Outdoor plans may be disrupted.",
                    "Carry rain gear and have indoor backup plans ready."
                ))
            if "snow" in desc or "blizzard" in desc:
                alerts.append(self._alert(
                    "warning", "Weather",
                    f"{desc.capitalize()} expected. Roads may be slippery.",
                    "Wear layers, waterproof boots, and check road status before departing."
                ))

            # Extreme Heat (stricter for kids/elderly)
            heat_threshold = 32 if (has_kids or has_elderly) else 38
            if temp_c > heat_threshold:
                alerts.append(self._alert(
                    "warning", "High Heat",
                    f"Temperature is {temp_c}°C (feels like {feels_like}°C). Heat stroke risk.",
                    "Stay hydrated, avoid midday sun (11 AM–4 PM), seek air-conditioned places."
                ))

            # Cold Snap
            cold_threshold = 8 if (has_kids or has_elderly) else 3
            if temp_c < cold_threshold:
                alerts.append(self._alert(
                    "warning", "Cold Snap",
                    f"Temperature is {temp_c}°C. Hypothermia risk for prolonged outdoor exposure.",
                    "Dress in thermal layers, carry hand warmers, limit outdoor exposure."
                ))

            # High Wind
            # OpenWeatherMap returns wind in m/s in `wind.speed`; we check if available
            wind_speed = weather_data.get("wind_speed", 0)  # m/s
            if wind_speed > 15:  # ~54 km/h
                alerts.append(self._alert(
                    "warning", "Wind",
                    f"Strong winds at {round(wind_speed * 3.6)} km/h. Outdoor activities challenging.",
                    "Avoid exposed hilltops, secure loose items, postpone water sports."
                ))

            # Visibility (fog, haze, mist, smoke)
            if any(kw in desc for kw in ["fog", "haze", "mist", "smoke"]):
                alerts.append(self._alert(
                    "info", "Visibility",
                    f"Low visibility due to {desc}. Driving may be hazardous.",
                    "Use foglights, reduce speed on highways, allow extra travel time."
                ))

        # ── 2. Daylight Alert ─────────────────────────────────────────
        daylight = context.get("weather_intel", {}).get("daylight_remaining", None)
        if daylight is not None and daylight < 1.5:
            alerts.append(self._alert(
                "info", "Daylight",
                f"Only {daylight:.1f}h of daylight left. Sunset approaching.",
                "Wrap up outdoor sightseeing; switch to evening-friendly activities."
            ))

        # ── 3. Crowd Alerts ───────────────────────────────────────────
        crowd = context.get("crowd_intel", {})
        crowd_score = crowd.get("crowd_score", 0)
        if crowd_score >= 8:
            alerts.append(self._alert(
                "warning", "Crowd",
                "Extreme crowds expected. Wait times and pickpocket risk increase.",
                "Visit attractions early morning or late afternoon; keep valuables secure."
            ))
        elif crowd.get("crowd_level") == "high" or crowd_score >= 6:
            alerts.append(self._alert(
                "info", "Crowd",
                "Popular spots are moderately crowded today.",
                "Consider visiting during off-peak hours or exploring lesser-known alternatives."
            ))

        # ── 4. News / Safety Alerts ───────────────────────────────────
        news = context.get("news_intel", {})
        if news.get("safety_risks"):
            for risk in news["safety_risks"]:
                severity = risk.get("severity", "Medium")
                alert_type = "critical" if severity == "High" else "warning"
                alerts.append(self._alert(
                    alert_type, "Safety Advisory",
                    risk.get("title", "Travel advisory in effect"),
                    risk.get("actionable_advice", "Monitor local news and stay alert.")
                ))

        # Positive: Events & Festivals
        if news.get("opportunities"):
            for opp in news["opportunities"][:2]:
                alerts.append(self._alert(
                    "info", "Event",
                    f"{opp.get('title', 'Local Event')} — {opp.get('summary', '')}",
                    "Check timings and book tickets in advance if available."
                ))

        # ── 5. Health Alerts ──────────────────────────────────────────
        health = context.get("health_intel", {})
        if health and not health.get("error"):
            # Seasonal risks / outbreaks
            seasonal = (health.get("seasonal_risks") or "").lower()
            if any(kw in seasonal for kw in ["dengue", "malaria", "cholera", "outbreak", "epidemic"]):
                alerts.append(self._alert(
                    "critical", "Health Outbreak",
                    f"Active health concern: {health.get('seasonal_risks', '')}",
                    "Use insect repellent, wear long sleeves; consult a travel clinic before departure."
                ))

            # Vaccinations
            vaccinations = health.get("vaccinations", [])
            if len(vaccinations) >= 3:
                alerts.append(self._alert(
                    "info", "Vaccination",
                    f"{len(vaccinations)} vaccinations recommended for this destination.",
                    "Visit a travel clinic 4–6 weeks before departure."
                ))

            # Water Safety
            water = (health.get("water_safety") or "").lower()
            if any(kw in water for kw in ["unsafe", "not safe", "avoid", "boil", "bottled"]):
                alerts.append(self._alert(
                    "warning", "Water Safety",
                    "Tap water may be unsafe for drinking.",
                    "Use bottled water for drinking and brushing teeth; avoid ice in street drinks."
                ))

        # ── 6. Budget Alert ───────────────────────────────────────────
        budget = context.get("budget_intel", {})
        if budget and not budget.get("error"):
            feasibility = (budget.get("feasibility") or "").lower()
            if feasibility == "low":
                alerts.append(self._alert(
                    "info", "Budget Stress",
                    "Your budget may be tight for this destination at current prices.",
                    "Eat where locals eat, use public transport, avoid peak-pricing tourist restaurants."
                ))

        # ── 7. Cultural Alerts ────────────────────────────────────────
        cultural = context.get("cultural_intel", {})
        if cultural and not cultural.get("error"):
            etiquette = cultural.get("etiquette_dos", [])
            dress_code = cultural.get("dress_code", "")
            if dress_code:
                alerts.append(self._alert(
                    "info", "Cultural",
                    f"Dress code advisory: {dress_code[:120]}",
                    "Pack modest clothing if visiting religious or traditional areas."
                ))
            elif etiquette and len(etiquette) > 0:
                alerts.append(self._alert(
                    "info", "Cultural",
                    f"Cultural tip: {etiquette[0][:120]}",
                    "Respect local customs for a smoother, more welcoming experience."
                ))

        # ── 8. Sustainability / Connectivity Alerts ───────────────────
        sustainability = context.get("sustainability_intel", {})
        if sustainability and not sustainability.get("error"):
            connectivity = (sustainability.get("connectivity") or "").lower()
            if any(kw in connectivity for kw in ["limited", "poor", "no signal", "remote"]):
                alerts.append(self._alert(
                    "info", "Connectivity",
                    "Limited mobile/internet connectivity at this destination.",
                    "Download offline maps and important docs before you leave."
                ))

        # ── 9. Altitude Alert (from live pulse or destination context) ─
        live_pulse = context.get("live_pulse_intel", {})
        if live_pulse and not live_pulse.get("error"):
            altitude_info = (live_pulse.get("altitude") or "")
            if altitude_info:
                try:
                    alt_m = int("".join(filter(str.isdigit, str(altitude_info)[:6])))
                    if alt_m > 2500:
                        alerts.append(self._alert(
                            "warning", "Altitude",
                            f"Destination is at ~{alt_m}m elevation. Altitude sickness possible.",
                            "Acclimatize gradually, stay hydrated, avoid strenuous activity on Day 1."
                        ))
                except (ValueError, TypeError):
                    pass

        # ── Sort by priority (critical first) ─────────────────────────
        alerts.sort(key=lambda a: SEVERITY_PRIORITY.get(a.get("type", "info"), 0), reverse=True)

        return alerts

    def _alert(self, alert_type, category, message, action):
        """Helper to build a consistent alert dict."""
        return {
            "type": alert_type,
            "title": category,
            "icon": ALERT_ICONS.get(category, "ℹ️"),
            "message": message,
            "action": action,
            "priority": SEVERITY_PRIORITY.get(alert_type, 0)
        }
