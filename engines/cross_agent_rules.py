import logging

from engines.severity import Severity

logger = logging.getLogger("wanderx.cross_agent_rules")


class CrossAgentRulesEngine:
    """
    RTRIE compound rules:
    detect multi-source risk combinations and emit high-impact directives.
    """

    def evaluate(self, intel_bundle):
        weather = (intel_bundle.get("weather_intel") or {}).get("weather_data", {})
        crowd = intel_bundle.get("crowd_intel") or {}
        news = intel_bundle.get("news_intel") or {}
        health = intel_bundle.get("health_intel") or {}
        sustainability = intel_bundle.get("sustainability_intel") or {}
        live_pulse = intel_bundle.get("live_pulse_intel") or {}
        profile = intel_bundle.get("profile") or {}

        triggered = []
        extra_alerts = []
        recommendations = []
        blocks = {"outdoor": False, "adventure": False, "treks": False}
        confidence_mod = 0.0

        def fire(rule_id, name, severity, message, action, recs=None, block_outdoor=False, block_adventure=False, block_treks=False, conf=0.0):
            alert = {
                "type": severity.name,
                "title": name,
                "message": message,
                "action": action,
                "icon": severity.icon,
                "priority": severity.priority,
            }
            result = {
                "rule_id": rule_id,
                "rule_name": name,
                "severity": severity.to_dict(),
                "alert": alert,
                "recommendations": recs or [],
            }
            triggered.append(result)
            extra_alerts.append(alert)
            recommendations.extend(recs or [])
            if block_outdoor:
                blocks["outdoor"] = True
            if block_adventure:
                blocks["adventure"] = True
            if block_treks:
                blocks["treks"] = True
            nonlocal_conf[0] += conf

        nonlocal_conf = [0.0]

        # Rule 1: Severe weather + crowd + news risk => lockdown
        rain_prob = weather.get("rain_probability", 0)
        desc = (weather.get("description") or "").lower()
        if (
            (rain_prob >= 0.85 or any(k in desc for k in ["storm", "thunder", "cyclone", "hurricane", "blizzard"]))
            and (crowd.get("crowd_score", 0) >= 7)
            and len(news.get("safety_risks") or []) > 0
        ):
            fire(
                "compound_lockdown",
                "Compound Lockdown",
                Severity.CRITICAL,
                "Severe weather overlaps with high crowd pressure and active safety advisories.",
                "Suspend exposed outdoor activities and move to protected zones.",
                recs=[
                    "Switch to indoor-safe itinerary blocks only",
                    "Avoid transport chokepoints until advisory softens",
                    "Track local authority channels every 30 minutes",
                ],
                block_outdoor=True,
                block_treks=True,
                conf=-0.08,
            )

        # Rule 2: Health outbreak + unsafe water + weak medical access => health protocol
        seasonal = (health.get("seasonal_risks") or "").lower()
        water = (health.get("water_safety") or "").lower()
        medical = (health.get("medical_facilities") or "").lower()
        if (
            any(k in seasonal for k in ["outbreak", "dengue", "cholera", "malaria", "epidemic"])
            and any(k in water for k in ["unsafe", "avoid", "not safe", "bottled"])
            and any(k in medical for k in ["limited", "basic", "remote", "far"])
        ):
            fire(
                "health_protocol",
                "Health Protocol",
                Severity.CRITICAL,
                "Outbreak + unsafe water + weak medical coverage creates elevated health exposure.",
                "Activate health-safe protocol for food, water, and route planning.",
                recs=[
                    "Use sealed bottled water exclusively",
                    "Carry critical meds and backup prescription copy",
                    "Stay within quick-access distance to major medical center",
                ],
                conf=-0.06,
            )

        # Rule 3: Live chaos + mobility strain => reroute
        chaos = live_pulse.get("chaos") or {}
        chaos_status = (chaos.get("status") or "").lower()
        travel_time = (intel_bundle.get("mobility_intel") or {}).get("travel_time")
        if chaos_status in ("warning", "danger") and isinstance(travel_time, (int, float)) and travel_time >= 2.5:
            fire(
                "reroute_now",
                "Live Reroute",
                Severity.HIGH,
                "Live disruption signals overlap with long transfer windows.",
                "Reroute through stable corridors and reduce cross-city hops.",
                recs=[
                    "Prioritize one-zone itinerary cluster for next 4-6 hours",
                    "Delay non-essential transfer legs",
                ],
                block_adventure=True,
                conf=-0.04,
            )

        # Rule 4: Good conditions boost
        opportunities = news.get("opportunities") or []
        if (
            rain_prob < 0.2
            and 19 <= weather.get("temperature_c", 26) <= 31
            and (crowd.get("crowd_score", 10) <= 4)
            and len(news.get("safety_risks") or []) == 0
            and len(opportunities) > 0
            and chaos_status not in ("warning", "danger")
        ):
            fire(
                "opportunity_window",
                "Opportunity Window",
                Severity.INFO,
                "Stable conditions with low crowd and active local opportunities.",
                "Increase high-value exploration density while conditions are favorable.",
                recs=[
                    f"Prioritize: {opportunities[0].get('title', 'current event')}",
                    "Reserve top outdoor slots in the next daylight block",
                ],
                conf=0.10,
            )

        # Rule 5: Vulnerable group + high heat / altitude-like strain
        group = (profile.get("group_type") or "").lower()
        if any(k in group for k in ["elder", "senior", "family", "child", "kid"]) and weather.get("temperature_c", 25) >= 36:
            fire(
                "vulnerable_heat_guard",
                "Vulnerable Traveler Guard",
                Severity.HIGH,
                "Vulnerable group profile combined with heat-stress conditions.",
                "Use conservative pacing and climate-controlled transition points.",
                recs=[
                    "Avoid midday exertion windows",
                    "Schedule hydration/rest checkpoints every 60-90 minutes",
                ],
                block_adventure=True,
                conf=-0.03,
            )

        dedup_recs = list(dict.fromkeys(recommendations))

        return {
            "triggered_rules": triggered,
            "extra_alerts": extra_alerts,
            "recommendations": dedup_recs,
            "blocks": blocks,
            "confidence_modifier": nonlocal_conf[0],
            "rules_evaluated": 5,
            "rules_triggered": len(triggered),
        }
