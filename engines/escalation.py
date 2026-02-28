"""
Time-Based Escalation Engine for WanderX.

Upgrades alert severity based on:
1. Time elapsed since alert creation (age-based)
2. Proximity to threshold (approaching deadline/event)
3. Compound signal convergence (multiple sources agree)
"""
import logging
from datetime import datetime, timedelta

from engines.severity import Severity, SeverityLevel

logger = logging.getLogger("wanderx.escalation")


class EscalationRule:
    """Base class for escalation rules."""
    def __init__(self, name, description=""):
        self.name = name
        self.description = description

    def apply(self, alert, context=None):
        """
        Evaluate whether this alert should be escalated.
        Returns: (escalated: bool, new_severity: SeverityLevel, reason: str)
        """
        raise NotImplementedError


class TimeEscalation(EscalationRule):
    """
    Age-based escalation: if an alert has been active longer than its
    escalation window, bump it up one level.
    """
    def __init__(self):
        super().__init__("time_escalation", "Escalates alerts based on how long they've been active.")

    def apply(self, alert, context=None):
        created_at = alert.get("created_at")
        if not created_at:
            return False, None, ""

        severity = alert.get("_severity_obj")
        if not severity or not isinstance(severity, SeverityLevel):
            severity = Severity.from_string(alert.get("type", "info"))

        # Check if this severity level has an escalation window
        if severity.escalates_after_min is None:
            return False, None, ""

        now = context.get("now", datetime.now()) if context else datetime.now()
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                return False, None, ""

        age_minutes = (now - created_at).total_seconds() / 60

        if age_minutes >= severity.escalates_after_min:
            new_severity = Severity.escalate(severity)
            return True, new_severity, f"Alert active for {int(age_minutes)}min — escalated from {severity.name} to {new_severity.name}"

        return False, None, ""


class ProximityEscalation(EscalationRule):
    """
    Proximity-based escalation: when a condition is approaching a critical
    threshold, escalate preemptively.
    
    Examples:
    - Daylight running out → escalate outdoor warnings
    - Rain approaching → escalate weather warnings
    - Temperature rising toward extreme → preemptive heat alert
    """
    def __init__(self):
        super().__init__("proximity_escalation", "Escalates based on approaching thresholds.")

    def apply(self, alert, context=None):
        if not context:
            return False, None, ""

        category = alert.get("title", "")
        current_severity = Severity.from_string(alert.get("type", "info"))

        # Daylight proximity: if < 30 min of daylight and there are outdoor warnings
        daylight = context.get("daylight_remaining")
        if daylight is not None and daylight < 0.5:
            if category in ("Daylight", "Weather", "Visibility"):
                if current_severity < Severity.HIGH:
                    return True, Severity.HIGH, f"Only {daylight:.1f}h daylight left — urgency increased"

        # Temperature proximity: feels like approaching extremes
        temp = context.get("temperature_c", 25)
        if temp > 43 and category == "High Heat" and current_severity < Severity.CRITICAL:
            return True, Severity.CRITICAL, f"Temperature at {temp}°C — extreme danger"
        
        if temp < -10 and category == "Cold Snap" and current_severity < Severity.CRITICAL:
            return True, Severity.CRITICAL, f"Temperature at {temp}°C — extreme cold danger"

        # Crowd surge: if crowd score keeps rising
        crowd_score = context.get("crowd_score", 0)
        if crowd_score >= 9 and category == "Crowd" and current_severity < Severity.HIGH:
            return True, Severity.HIGH, f"Crowd score at {crowd_score}/10 — extreme crowding"

        return False, None, ""


class CompoundEscalation(EscalationRule):
    """
    Compound escalation: when multiple risk sources all report concerning
    signals simultaneously, escalate the overall alert level.
    """
    def __init__(self):
        super().__init__("compound_escalation", "Escalates when multiple risk sources converge.")

    def apply(self, alert, context=None):
        if not context:
            return False, None, ""

        # Count active risk signals
        risk_signals = 0
        signal_sources = []

        weather_data = context.get("weather_data", {})
        rain = weather_data.get("rain_probability", 0)
        if rain > 0.5:
            risk_signals += 1
            signal_sources.append("weather")

        news = context.get("news_intel", {})
        if news and news.get("safety_risks"):
            risk_signals += len(news["safety_risks"])
            signal_sources.append("news")

        crowd_score = context.get("crowd_score", 0)
        if crowd_score >= 7:
            risk_signals += 1
            signal_sources.append("crowd")

        health = context.get("health_intel", {})
        seasonal = (health.get("seasonal_risks") or "").lower() if health else ""
        if any(kw in seasonal for kw in ["outbreak", "dengue", "cholera"]):
            risk_signals += 1
            signal_sources.append("health")

        # If 3+ risk sources converge, escalate
        if risk_signals >= 3:
            current = Severity.from_string(alert.get("type", "info"))
            if current < Severity.HIGH:
                return True, Severity.HIGH, f"Multiple risk sources active ({', '.join(signal_sources)}) — compound escalation"

        return False, None, ""


class EscalationEngine:
    """
    Applies all escalation rules to a list of alerts.
    """
    def __init__(self):
        self.rules = [
            TimeEscalation(),
            ProximityEscalation(),
            CompoundEscalation(),
        ]

    def apply_escalations(self, alerts, context=None):
        """
        Process a list of alerts through all escalation rules.
        
        Args:
            alerts: List of alert dicts from AlertEngine
            context: Dict with current conditions (daylight, temp, crowd, etc.)
            
        Returns:
            list: Updated alerts with escalated severities and escalation trail
        """
        context = context or {}
        escalated_alerts = []

        for alert in alerts:
            escalated = dict(alert)  # Copy
            escalation_trail = []

            for rule in self.rules:
                did_escalate, new_severity, reason = rule.apply(escalated, context)
                if did_escalate and new_severity:
                    escalated["type"] = new_severity.name
                    escalated["priority"] = new_severity.priority
                    escalated["icon"] = new_severity.icon
                    escalated["_severity_obj"] = new_severity
                    escalation_trail.append({
                        "rule": rule.name,
                        "new_level": new_severity.name,
                        "reason": reason
                    })

            if escalation_trail:
                escalated["escalated"] = True
                escalated["escalation_trail"] = escalation_trail
            else:
                escalated["escalated"] = False

            escalated_alerts.append(escalated)

        # Re-sort by priority after escalations
        escalated_alerts.sort(
            key=lambda a: a.get("priority", 0),
            reverse=True
        )

        return escalated_alerts

    def generate_countdown_alerts(self, context):
        """
        Generate time-sensitive countdown alerts for approaching conditions.
        
        Args:
            context: Current conditions dict
            
        Returns:
            list: Countdown alert dicts
        """
        countdowns = []

        # Daylight countdown
        daylight = context.get("daylight_remaining")
        if daylight is not None:
            if daylight < 0.5:
                countdowns.append({
                    "type": "critical",
                    "title": "Sunset Imminent",
                    "icon": "🌅",
                    "message": f"Only {int(daylight * 60)} minutes of daylight left!",
                    "action": "Head to your accommodation or a well-lit area now.",
                    "priority": Severity.CRITICAL.priority,
                    "countdown_minutes": int(daylight * 60),
                    "escalated": True
                })
            elif daylight < 1.5:
                countdowns.append({
                    "type": "warning",
                    "title": "Sunset Approaching",
                    "icon": "🌅",
                    "message": f"About {int(daylight * 60)} minutes of daylight remaining.",
                    "action": "Start wrapping up outdoor activities.",
                    "priority": Severity.MEDIUM.priority,
                    "countdown_minutes": int(daylight * 60),
                    "escalated": False
                })

        # Rain approaching (if forecast data available)
        rain_in_hours = context.get("rain_expected_in_hours")
        if rain_in_hours is not None and rain_in_hours < 2:
            minutes = int(rain_in_hours * 60)
            if minutes < 30:
                countdowns.append({
                    "type": "warning",
                    "title": "Rain Imminent",
                    "icon": "🌧️",
                    "message": f"Rain expected in ~{minutes} minutes.",
                    "action": "Seek shelter or move activities indoors immediately.",
                    "priority": Severity.HIGH.priority,
                    "countdown_minutes": minutes,
                    "escalated": True
                })
            else:
                countdowns.append({
                    "type": "info",
                    "title": "Rain Expected",
                    "icon": "🌧️",
                    "message": f"Rain forecasted in about {minutes} minutes.",
                    "action": "Have indoor backup plans ready.",
                    "priority": Severity.LOW.priority,
                    "countdown_minutes": minutes,
                    "escalated": False
                })

        return countdowns
