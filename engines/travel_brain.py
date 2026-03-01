import logging
from datetime import datetime

from engines.alert_engine import AlertEngine
from engines.cross_agent_rules import CrossAgentRulesEngine
from engines.decision_engine import DecisionEngine
from engines.escalation import EscalationEngine
from engines.itinerary_validator import ItineraryValidator
from engines.risk_fusion_engine import RiskFusionEngine
from engines.templates import TemplateEngine
from engines.travel_score import TravelScore

logger = logging.getLogger("wanderx.travel_brain")


class TravelBrain:
    """
    RTRIE Meta-Orchestrator
    Pipeline:
    Data Signals -> Risk Fusion -> Alerts -> Escalation -> Cross-Agent Rules -> Decisions -> Score
    """

    def __init__(self):
        self.risk_engine = RiskFusionEngine()
        self.alert_engine = AlertEngine()
        self.decision_engine = DecisionEngine()
        self.escalation_engine = EscalationEngine()
        self.cross_agent_engine = CrossAgentRulesEngine()
        self.template_engine = TemplateEngine()
        self.itinerary_validator = ItineraryValidator()

    def analyze(self, intel_bundle, profile=None):
        profile = profile or {}
        now = datetime.now()

        weather_intel = intel_bundle.get("weather_intel") or {}
        news_intel = intel_bundle.get("news_intel") or {}
        crowd_intel = intel_bundle.get("crowd_intel") or {}
        mobility_intel = intel_bundle.get("mobility_intel") or {}
        health_intel = intel_bundle.get("health_intel") or {}
        budget_intel = intel_bundle.get("budget_intel") or {}
        cultural_intel = intel_bundle.get("cultural_intel") or {}
        sustainability_intel = intel_bundle.get("sustainability_intel") or {}
        live_pulse_intel = intel_bundle.get("live_pulse_intel") or {}

        # 1) Risk Fusion
        risk_assessment = self.risk_engine.fuse_risks(
            weather_intel,
            news_intel,
            crowd_intel,
            mobility_intel,
            health_intel=health_intel,
            budget_intel=budget_intel,
            cultural_intel=cultural_intel,
            sustainability_intel=sustainability_intel,
            live_pulse_intel=live_pulse_intel,
            profile=profile,
        )

        # 2) Raw Alerts
        alert_context = {
            "weather_intel": weather_intel,
            "news_intel": news_intel,
            "crowd_intel": crowd_intel,
            "mobility_intel": mobility_intel,
            "health_intel": health_intel,
            "budget_intel": budget_intel,
            "cultural_intel": cultural_intel,
            "sustainability_intel": sustainability_intel,
            "live_pulse_intel": live_pulse_intel,
        }
        raw_alerts = self.alert_engine.generate_alerts(alert_context, profile=profile)

        # 3) Escalation
        escalation_context = {
            "now": now,
            "daylight_remaining": weather_intel.get("daylight_remaining"),
            "temperature_c": (weather_intel.get("weather_data") or {}).get("temperature_c", 25),
            "crowd_score": crowd_intel.get("crowd_score", 0),
            "weather_data": weather_intel.get("weather_data") or {},
            "news_intel": news_intel,
            "health_intel": health_intel,
        }
        escalated_alerts = self.escalation_engine.apply_escalations(raw_alerts, escalation_context)
        countdown_alerts = self.escalation_engine.generate_countdown_alerts(escalation_context)
        all_alerts = escalated_alerts + countdown_alerts

        # 4) Cross-agent rules
        cross_bundle = {**intel_bundle, "profile": profile}
        cross_agent_results = self.cross_agent_engine.evaluate(cross_bundle)

        if cross_agent_results.get("extra_alerts"):
            all_alerts = cross_agent_results["extra_alerts"] + all_alerts

        # Deduplicate alerts by title+message
        seen = set()
        deduped_alerts = []
        for alert in all_alerts:
            key = ((alert.get("title") or "").lower(), (alert.get("message") or "").lower())
            if key in seen:
                continue
            seen.add(key)
            deduped_alerts.append(alert)
        deduped_alerts.sort(key=lambda a: (a.get("priority", 0), a.get("risk_score", 0)), reverse=True)

        # 5) Decision suggestions + warnings
        decision_context = {
            "weather": weather_intel.get("weather_data") or {},
            "time": {"hour": now.hour},
            "crowd": crowd_intel,
            "news": news_intel,
            "health": health_intel,
            "cultural": cultural_intel,
            "sustainability": sustainability_intel,
            "daylight_remaining": weather_intel.get("daylight_remaining"),
        }
        decision_suggestions = self.decision_engine.generate_plan_suggestions(decision_context, profile=profile)
        safety_warnings = self.decision_engine.get_safety_warnings(decision_context, profile=profile)
        automation = self.decision_engine.get_automated_decisions(
            risk_assessment=risk_assessment,
            alerts=deduped_alerts,
            context=decision_context,
            profile=profile,
        )

        # 6) Template suggestions (additive)
        template_suggestions = self.template_engine.render_suggestions(decision_context, profile=profile)
        merged_suggestions = list(decision_suggestions)
        existing_titles = {s.get("title") for s in merged_suggestions}
        for item in template_suggestions:
            if item.get("title") not in existing_titles:
                merged_suggestions.append(item)
                existing_titles.add(item.get("title"))

        # 7) Block filtering
        blocks = cross_agent_results.get("blocks", {})
        if blocks.get("outdoor") or blocks.get("treks"):
            merged_suggestions = [
                s for s in merged_suggestions
                if not any(
                    kw in (s.get("title", "") + " " + " ".join(s.get("tags", []))).lower()
                    for kw in ["outdoor", "trek", "hike", "nature", "beach"]
                )
            ]

        # 8) Travel score
        travel_score = TravelScore.calculate(
            risk_assessment=risk_assessment,
            weather_intel=weather_intel,
            crowd_intel=crowd_intel,
            budget_intel=budget_intel,
            news_intel=news_intel,
            cultural_intel=cultural_intel,
            sustainability_intel=sustainability_intel,
            live_pulse_intel=live_pulse_intel,
            profile=profile,
        )

        conf_mod = cross_agent_results.get("confidence_modifier", 0)
        if conf_mod:
            adjusted = travel_score["score"] + int(conf_mod * 100)
            travel_score["score"] = max(0, min(100, adjusted))

        return {
            "travel_score": travel_score,
            "risk_assessment": risk_assessment,
            "alerts": deduped_alerts,
            "plan_suggestions": merged_suggestions,
            "safety_warnings": safety_warnings,
            "decision_automation": automation,
            "cross_agent_insights": {
                "triggered_rules": cross_agent_results.get("triggered_rules", []),
                "rules_evaluated": cross_agent_results.get("rules_evaluated", 0),
                "rules_triggered": cross_agent_results.get("rules_triggered", 0),
                "blocks": blocks,
                "extra_recommendations": cross_agent_results.get("recommendations", []),
            },
            "engine_metadata": {
                "engines_used": [
                    "RiskFusionEngine",
                    "AlertEngine",
                    "EscalationEngine",
                    "CrossAgentRulesEngine",
                    "DecisionEngine",
                    "TemplateEngine",
                    "TravelScore",
                ],
                "alerts_escalated": sum(1 for a in deduped_alerts if a.get("escalated")),
                "templates_matched": len(template_suggestions),
                "timestamp": now.isoformat(),
                "rtrie_pipeline": "live_signals>risk_fusion>decision>alert_delivery",
            },
        }

    def validate_itinerary(self, itinerary, intel_bundle, profile=None):
        return self.itinerary_validator.validate(itinerary, intel_bundle, profile)

    def full_analysis(self, intel_bundle, profile=None, itinerary=None):
        result = self.analyze(intel_bundle, profile)

        if itinerary:
            validation = self.validate_itinerary(itinerary, intel_bundle, profile)
            result["itinerary_validation"] = validation
            if validation.get("score", 100) < 50:
                penalty = int((100 - validation.get("score", 100)) * 0.1)
                result["travel_score"]["score"] = max(0, result["travel_score"]["score"] - penalty)

        return result
