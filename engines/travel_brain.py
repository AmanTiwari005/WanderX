"""
TravelBrain — Meta-Orchestrator for WanderX.

The single intelligence layer that coordinates all engines:
  RiskFusion → Alerts → Escalation → CrossAgentRules → Templates → TravelScore → Validation

Usage:
    brain = TravelBrain()
    result = brain.analyze(intel_bundle, profile)
"""
import logging
from datetime import datetime

from engines.risk_fusion_engine import RiskFusionEngine
from engines.alert_engine import AlertEngine
from engines.decision_engine import DecisionEngine
from engines.escalation import EscalationEngine
from engines.cross_agent_rules import CrossAgentRulesEngine
from engines.templates import TemplateEngine
from engines.travel_score import TravelScore
from engines.itinerary_validator import ItineraryValidator

logger = logging.getLogger("wanderx.travel_brain")


class TravelBrain:
    """
    Unified intelligence layer that composes all engines 
    into a single analysis call with cross-engine coordination.
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
        """
        Run the full TravelBrain analysis pipeline.
        
        Args:
            intel_bundle: Dict with all intel sources:
                weather_intel, news_intel, crowd_intel, mobility_intel,
                health_intel, budget_intel, cultural_intel,
                sustainability_intel, live_pulse_intel
            profile: User profile dict (interests, budget, group_type, etc.)
            
        Returns:
            dict: Unified TravelBrainResult with all analysis outputs
        """
        profile = profile or {}
        weather_intel = intel_bundle.get("weather_intel") or {}
        news_intel = intel_bundle.get("news_intel") or {}
        crowd_intel = intel_bundle.get("crowd_intel") or {}
        mobility_intel = intel_bundle.get("mobility_intel") or {}
        health_intel = intel_bundle.get("health_intel") or {}
        budget_intel = intel_bundle.get("budget_intel") or {}
        cultural_intel = intel_bundle.get("cultural_intel") or {}
        sustainability_intel = intel_bundle.get("sustainability_intel") or {}
        live_pulse_intel = intel_bundle.get("live_pulse_intel") or {}

        # ── Step 1: Risk Fusion ───────────────────────────────
        risk_assessment = self.risk_engine.fuse_risks(
            weather_intel, news_intel, crowd_intel, mobility_intel,
            health_intel=health_intel,
            budget_intel=budget_intel,
            cultural_intel=cultural_intel,
            sustainability_intel=sustainability_intel,
            live_pulse_intel=live_pulse_intel,
            profile=profile
        )

        # ── Step 2: Raw Alerts ────────────────────────────────
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

        # ── Step 3: Escalation ────────────────────────────────
        escalation_context = {
            "now": datetime.now(),
            "daylight_remaining": weather_intel.get("daylight_remaining"),
            "temperature_c": weather_intel.get("weather_data", {}).get("temperature_c", 25) if weather_intel else 25,
            "crowd_score": crowd_intel.get("crowd_score", 0) if crowd_intel else 0,
            "weather_data": weather_intel.get("weather_data", {}) if weather_intel else {},
            "news_intel": news_intel,
            "health_intel": health_intel,
        }
        escalated_alerts = self.escalation_engine.apply_escalations(raw_alerts, escalation_context)

        # Add countdown alerts
        countdowns = self.escalation_engine.generate_countdown_alerts(escalation_context)
        escalated_alerts.extend(countdowns)

        # Re-sort all alerts together by priority
        escalated_alerts.sort(key=lambda a: a.get("priority", 0), reverse=True)

        # ── Step 4: Cross-Agent Rules ─────────────────────────
        rule_bundle = {**intel_bundle, "profile": profile}
        cross_agent_results = self.cross_agent_engine.evaluate(rule_bundle)

        # Merge cross-agent alerts
        if cross_agent_results.get("extra_alerts"):
            escalated_alerts = cross_agent_results["extra_alerts"] + escalated_alerts
            # Deduplicate by title
            seen = set()
            deduped = []
            for a in escalated_alerts:
                key = a.get("title", "")
                if key not in seen:
                    seen.add(key)
                    deduped.append(a)
            escalated_alerts = deduped

        # ── Step 5: Decision Engine Suggestions ───────────────
        decision_context = {
            "weather": weather_intel.get("weather_data", {}) if weather_intel else {},
            "time": {"hour": datetime.now().hour},
            "crowd": crowd_intel,
            "news": news_intel,
            "health": health_intel,
            "cultural": cultural_intel,
            "sustainability": sustainability_intel,
            "daylight_remaining": weather_intel.get("daylight_remaining") if weather_intel else None,
        }
        decision_suggestions = self.decision_engine.generate_plan_suggestions(decision_context, profile=profile)
        safety_warnings = self.decision_engine.get_safety_warnings(decision_context, profile=profile)

        # ── Step 6: Dynamic Template Suggestions ──────────────
        template_suggestions = self.template_engine.render_suggestions(decision_context, profile=profile)

        # Merge suggestions (templates extend, don't duplicate)
        merged_suggestions = list(decision_suggestions)
        seen_titles = {s["title"] for s in merged_suggestions}
        for ts in template_suggestions:
            if ts["title"] not in seen_titles:
                merged_suggestions.append(ts)
                seen_titles.add(ts["title"])

        # Apply cross-agent blocks
        blocks = cross_agent_results.get("blocks", {})
        if blocks.get("outdoor") or blocks.get("treks"):
            merged_suggestions = [
                s for s in merged_suggestions
                if not any(kw in (s.get("title", "") + " " + " ".join(s.get("tags", []))).lower()
                          for kw in ["outdoor", "trek", "hike", "nature walk", "beach"])
            ]

        # ── Step 7: Travel Score ──────────────────────────────
        travel_score = TravelScore.calculate(
            risk_assessment=risk_assessment,
            weather_intel=weather_intel,
            crowd_intel=crowd_intel,
            budget_intel=budget_intel,
            news_intel=news_intel,
            cultural_intel=cultural_intel,
            sustainability_intel=sustainability_intel,
            live_pulse_intel=live_pulse_intel,
            profile=profile
        )

        # Apply confidence modifier from cross-agent rules
        conf_mod = cross_agent_results.get("confidence_modifier", 0)
        if conf_mod != 0:
            adjusted = travel_score["score"] + int(conf_mod * 100)
            travel_score["score"] = max(0, min(100, adjusted))

        # ── Build Result ──────────────────────────────────────
        return {
            "travel_score": travel_score,
            "risk_assessment": risk_assessment,
            "alerts": escalated_alerts,
            "plan_suggestions": merged_suggestions,
            "safety_warnings": safety_warnings,
            "cross_agent_insights": {
                "triggered_rules": cross_agent_results.get("triggered_rules", []),
                "rules_evaluated": cross_agent_results.get("rules_evaluated", 0),
                "rules_triggered": cross_agent_results.get("rules_triggered", 0),
                "blocks": blocks,
                "extra_recommendations": cross_agent_results.get("recommendations", [])
            },
            "engine_metadata": {
                "engines_used": [
                    "RiskFusionEngine", "AlertEngine", "EscalationEngine",
                    "CrossAgentRulesEngine", "DecisionEngine", "TemplateEngine",
                    "TravelScore"
                ],
                "alerts_escalated": sum(1 for a in escalated_alerts if a.get("escalated")),
                "templates_matched": len(template_suggestions),
                "timestamp": datetime.now().isoformat()
            }
        }

    def validate_itinerary(self, itinerary, intel_bundle, profile=None):
        """
        Validate an itinerary against current intelligence.
        
        Args:
            itinerary: Generated itinerary dict
            intel_bundle: Current intel dict
            profile: User profile
            
        Returns:
            dict: Validation results with issues, scores, and auto-fixes
        """
        return self.itinerary_validator.validate(itinerary, intel_bundle, profile)

    def full_analysis(self, intel_bundle, profile=None, itinerary=None):
        """
        Run full analysis + itinerary validation in one call.
        
        Returns:
            dict: TravelBrainResult + itinerary_validation
        """
        result = self.analyze(intel_bundle, profile)

        if itinerary:
            validation = self.validate_itinerary(itinerary, intel_bundle, profile)
            result["itinerary_validation"] = validation

            # Adjust travel score if itinerary has issues
            if validation["score"] < 50:
                penalty = int((100 - validation["score"]) * 0.1)
                result["travel_score"]["score"] = max(0, result["travel_score"]["score"] - penalty)

        return result
