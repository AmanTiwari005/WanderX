"""
Cross-Agent Rules Engine for WanderX.

Compound rules that combine signals from multiple intelligence sources
to detect complex scenarios that no single agent could identify alone.
"""
import logging
from engines.severity import Severity

logger = logging.getLogger("wanderx.cross_agent_rules")


class CrossAgentRule:
    """
    A compound rule combining signals from multiple intelligence sources.
    """
    def __init__(self, rule_id, name, description, condition_fn, action_fn, severity=None):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.condition_fn = condition_fn
        self.action_fn = action_fn
        self.severity = severity or Severity.HIGH

    def evaluate(self, intel_bundle):
        """
        Check if this rule's condition is met.
        
        Args:
            intel_bundle: Dict with all intel sources
            
        Returns:
            (triggered: bool, result: dict or None)
        """
        try:
            if self.condition_fn(intel_bundle):
                result = self.action_fn(intel_bundle)
                result["rule_id"] = self.rule_id
                result["rule_name"] = self.name
                result["severity"] = self.severity.to_dict()
                return True, result
        except Exception as e:
            logger.warning(f"CrossAgentRule '{self.name}' error: {e}")
        return False, None


# ═══════════════════════════════════════════════════════════════
# HELPER EXTRACTORS
# ═══════════════════════════════════════════════════════════════

def _weather(b):
    return (b.get("weather_intel") or {}).get("weather_data", {})

def _news(b):
    return b.get("news_intel") or {}

def _crowd(b):
    return b.get("crowd_intel") or {}

def _health(b):
    return b.get("health_intel") or {}

def _budget(b):
    return b.get("budget_intel") or {}

def _cultural(b):
    return b.get("cultural_intel") or {}

def _sustain(b):
    return b.get("sustainability_intel") or {}

def _profile(b):
    return b.get("profile") or {}


# ═══════════════════════════════════════════════════════════════
# RULE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

CROSS_AGENT_RULES = [

    # ── RULE 1: Storm Lockdown ────────────────────────────────
    CrossAgentRule(
        rule_id="storm_lockdown",
        name="Storm Lockdown",
        description="Weather storm + high crowd + news safety risk → lock down outdoor plans",
        condition_fn=lambda b: (
            any(kw in (_weather(b).get("description") or "").lower()
                for kw in ["storm", "thunder", "cyclone", "hurricane", "blizzard"]) and
            _crowd(b).get("crowd_score", 0) >= 6 and
            len(_news(b).get("safety_risks", [])) > 0
        ),
        action_fn=lambda b: {
            "type": "lockdown",
            "alert": {
                "type": "critical",
                "title": "⛔ Storm Lockdown Active",
                "message": f"Severe weather ({_weather(b).get('description', 'storm')}) combined with high crowds and active safety risks. All outdoor activities suspended.",
                "action": "Stay indoors. Follow local emergency instructions. Monitor news updates.",
                "icon": "⛔",
                "priority": Severity.CRITICAL.priority
            },
            "block_outdoor": True,
            "recommendations": [
                "Move to hotel or secure indoor location",
                "Keep emergency numbers handy",
                "Charge devices and download offline maps"
            ]
        },
        severity=Severity.CRITICAL
    ),

    # ── RULE 2: Perfect Day ───────────────────────────────────
    CrossAgentRule(
        rule_id="perfect_day",
        name="Perfect Day",
        description="Clear weather + low crowd + no risks + events happening → boost confidence",
        condition_fn=lambda b: (
            _weather(b).get("rain_probability", 1) < 0.2 and
            20 <= _weather(b).get("temperature_c", 0) <= 32 and
            _crowd(b).get("crowd_score", 10) <= 4 and
            len(_news(b).get("safety_risks", [])) == 0 and
            len(_news(b).get("opportunities", [])) > 0
        ),
        action_fn=lambda b: {
            "type": "boost",
            "alert": {
                "type": "info",
                "title": "🌟 Perfect Day Detected",
                "message": f"Clear skies ({_weather(b).get('temperature_c', 25)}°C), low crowds, no risks, and local events happening. Ideal conditions!",
                "action": "Make the most of today — it's a great day to explore.",
                "icon": "🌟",
                "priority": Severity.INFO.priority
            },
            "confidence_boost": 0.15,
            "recommendations": [
                "Maximize outdoor time — conditions are excellent",
                f"Check out: {_news(b).get('opportunities', [{}])[0].get('title', 'local events')}"
            ]
        },
        severity=Severity.INFO
    ),

    # ── RULE 3: Health Crisis ─────────────────────────────────
    CrossAgentRule(
        rule_id="health_crisis",
        name="Health Crisis",
        description="Health outbreak + unsafe water + limited medical facility → critical health alert",
        condition_fn=lambda b: (
            any(kw in (_health(b).get("seasonal_risks") or "").lower()
                for kw in ["outbreak", "epidemic", "dengue", "cholera", "malaria"]) and
            any(kw in (_health(b).get("water_safety") or "").lower()
                for kw in ["unsafe", "not safe", "avoid", "bottled"]) and
            any(kw in (_health(b).get("medical_facilities") or "").lower()
                for kw in ["limited", "basic", "remote", "far"])
        ),
        action_fn=lambda b: {
            "type": "health_crisis",
            "alert": {
                "type": "critical",
                "title": "🏥 Health Crisis Protocol",
                "message": f"Active health risk ({_health(b).get('seasonal_risks', 'epidemic')}), unsafe water, and limited medical access.",
                "action": "Carry prescription meds, use only bottled water, know nearest city hospital location.",
                "icon": "🏥",
                "priority": Severity.CRITICAL.priority
            },
            "recommendations": [
                "Carry a medical emergency kit",
                "Use only sealed bottled water (including for teeth)",
                "Note the nearest major hospital before departing",
                "Consider travel health insurance upgrade"
            ]
        },
        severity=Severity.CRITICAL
    ),

    # ── RULE 4: Budget Crunch ─────────────────────────────────
    CrossAgentRule(
        rule_id="budget_crunch",
        name="Budget Crunch",
        description="Tight budget + peak pricing + high crowds → financial stress warning",
        condition_fn=lambda b: (
            (_budget(b).get("feasibility") or "").lower() in ("low",) and
            _crowd(b).get("crowd_score", 0) >= 6
        ),
        action_fn=lambda b: {
            "type": "budget_warning",
            "alert": {
                "type": "warning",
                "title": "💸 Budget Crunch Alert",
                "message": "Your budget is tight and crowds are driving up prices. Costs may exceed expectations.",
                "action": "Eat where locals eat, use public transport, avoid peak-hour tourist restaurants.",
                "icon": "💸",
                "priority": Severity.MEDIUM.priority
            },
            "recommendations": [
                "Eat at local eateries away from tourist centers",
                "Use public transport instead of taxis",
                "Visit free attractions and viewpoints",
                "Book accommodations with kitchen access"
            ]
        },
        severity=Severity.MEDIUM
    ),

    # ── RULE 5: Altitude Cascade ──────────────────────────────
    CrossAgentRule(
        rule_id="altitude_cascade",
        name="Altitude Cascade",
        description="High altitude + cold + limited medical + elderly → critical altitude risk",
        condition_fn=lambda b: (
            _weather(b).get("temperature_c", 25) < 5 and
            any(kw in (_health(b).get("medical_facilities") or "").lower()
                for kw in ["limited", "basic", "remote"]) and
            any(kw in (_profile(b).get("group_type") or "").lower()
                for kw in ["elder", "senior"])
        ),
        action_fn=lambda b: {
            "type": "altitude_crisis",
            "alert": {
                "type": "critical",
                "title": "⛰️ Altitude Cascade Risk",
                "message": f"Cold conditions ({_weather(b).get('temperature_c')}°C), limited medical access, and elderly travelers — high-altitude risk is critical.",
                "action": "Consider lower-altitude alternatives. Carry oxygen can and altitude medication.",
                "icon": "⛰️",
                "priority": Severity.CRITICAL.priority
            },
            "block_adventure": True,
            "recommendations": [
                "Descend to lower altitude if symptoms appear",
                "Carry portable oxygen and Diamox",
                "Stay near medical facilities",
                "Avoid physical exertion above 3000m"
            ]
        },
        severity=Severity.CRITICAL
    ),

    # ── RULE 6: Monsoon Chain ─────────────────────────────────
    CrossAgentRule(
        rule_id="monsoon_chain",
        name="Monsoon Chain",
        description="Rain + mountain terrain + limited connectivity → block treks",
        condition_fn=lambda b: (
            _weather(b).get("rain_probability", 0) > 0.5 and
            any(kw in (_sustain(b).get("connectivity") or _sustain(b).get("terrain") or _sustain(b).get("geography") or "").lower()
                for kw in ["mountain", "hill", "remote", "limited"]) and
            any(kw in (_sustain(b).get("connectivity") or "").lower()
                for kw in ["poor", "limited", "no signal", "remote"])
        ),
        action_fn=lambda b: {
            "type": "monsoon_block",
            "alert": {
                "type": "warning",
                "title": "🌧️ Monsoon Chain Alert",
                "message": "Rain + mountain terrain + poor connectivity = dangerous combination. Treks and remote activities blocked.",
                "action": "Stay in base town. Enjoy local culture, food, and indoor activities.",
                "icon": "🌧️",
                "priority": Severity.HIGH.priority
            },
            "block_treks": True,
            "recommendations": [
                "Stay in base town or lower elevations",
                "Download offline maps before losing signal",
                "Keep emergency contacts saved offline",
                "Enjoy local cafés, cuisine, and cultural sites"
            ]
        },
        severity=Severity.HIGH
    ),
]


class CrossAgentRulesEngine:
    """
    Evaluates all cross-agent rules against the current intel bundle.
    """
    def __init__(self, rules=None):
        self.rules = rules or CROSS_AGENT_RULES

    def evaluate(self, intel_bundle):
        """
        Run all rules against the intel bundle.
        
        Args:
            intel_bundle: Dict with all intel sources (weather_intel, news_intel, etc.)
            
        Returns:
            dict: {
                "triggered_rules": [...],
                "extra_alerts": [...],
                "recommendations": [...],
                "blocks": {"outdoor": bool, "adventure": bool, "treks": bool},
                "confidence_modifier": float
            }
        """
        triggered = []
        extra_alerts = []
        all_recommendations = []
        blocks = {"outdoor": False, "adventure": False, "treks": False}
        confidence_mod = 0.0

        for rule in self.rules:
            fired, result = rule.evaluate(intel_bundle)
            if fired and result:
                triggered.append(result)

                if "alert" in result:
                    extra_alerts.append(result["alert"])

                if "recommendations" in result:
                    all_recommendations.extend(result["recommendations"])

                if result.get("block_outdoor"):
                    blocks["outdoor"] = True
                if result.get("block_adventure"):
                    blocks["adventure"] = True
                if result.get("block_treks"):
                    blocks["treks"] = True

                confidence_mod += result.get("confidence_boost", 0)

        return {
            "triggered_rules": triggered,
            "extra_alerts": extra_alerts,
            "recommendations": list(dict.fromkeys(all_recommendations)),  # Deduplicate
            "blocks": blocks,
            "confidence_modifier": confidence_mod,
            "rules_evaluated": len(self.rules),
            "rules_triggered": len(triggered)
        }
