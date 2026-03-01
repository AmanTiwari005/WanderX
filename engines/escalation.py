import logging
from datetime import datetime

from engines.severity import Severity

logger = logging.getLogger("wanderx.escalation")


class EscalationEngine:
    """
    RTRIE escalation layer
    - Time-aware escalation using created_at + ttl_minutes
    - Signal-aware escalation from current context
    - Countdown alerts for immediate operational transitions
    """

    def apply_escalations(self, alerts, context=None):
        context = context or {}
        now = context.get("now") or datetime.now()
        escalated = []

        for alert in alerts or []:
            current = dict(alert)
            trail = []

            if not current.get("created_at"):
                current["created_at"] = now.isoformat()

            # 1) TTL age-based escalation
            ttl = current.get("ttl_minutes")
            age = self._age_minutes(current.get("created_at"), now)
            if ttl and age is not None and age >= ttl:
                new_level = self._escalate_level(current.get("type", "info"))
                if new_level != current.get("type"):
                    current["type"] = new_level
                    current["priority"] = self._priority_for_level(new_level)
                    current["icon"] = self._icon_for_level(new_level, current.get("icon"))
                    trail.append({
                        "rule": "ttl_age",
                        "reason": f"Alert age {int(age)}m exceeded ttl {ttl}m",
                        "new_level": new_level,
                    })

            # 2) Context pressure escalation
            pressure = self._context_pressure_score(context)
            if pressure >= 80 and current.get("type") in ("info", "warning"):
                new_level = "high"
                current["type"] = new_level
                current["priority"] = self._priority_for_level(new_level)
                trail.append({
                    "rule": "context_pressure",
                    "reason": f"High multi-signal pressure ({pressure}/100)",
                    "new_level": new_level,
                })
            elif pressure >= 92 and current.get("type") in ("high", "warning"):
                new_level = "critical"
                current["type"] = new_level
                current["priority"] = self._priority_for_level(new_level)
                trail.append({
                    "rule": "context_pressure",
                    "reason": f"Critical pressure cluster ({pressure}/100)",
                    "new_level": new_level,
                })

            current["escalated"] = bool(trail)
            if trail:
                current["escalation_trail"] = trail

            escalated.append(current)

        escalated.sort(key=lambda a: (a.get("priority", 0), a.get("risk_score", 0)), reverse=True)
        return escalated

    def generate_countdown_alerts(self, context):
        now_iso = (context.get("now") or datetime.now()).isoformat()
        countdowns = []

        daylight = context.get("daylight_remaining")
        if daylight is not None:
            if daylight <= 0.5:
                countdowns.append({
                    "type": "critical",
                    "title": "Daylight Expiry",
                    "icon": "🌅",
                    "message": f"Only {int(daylight * 60)} minutes of daylight remain.",
                    "action": "Initiate return-to-safe-zone route immediately.",
                    "priority": self._priority_for_level("critical"),
                    "created_at": now_iso,
                    "ttl_minutes": 20,
                    "countdown_minutes": int(daylight * 60),
                    "escalated": True,
                })
            elif daylight <= 1.5:
                countdowns.append({
                    "type": "warning",
                    "title": "Daylight Buffer Low",
                    "icon": "🌅",
                    "message": f"Daylight buffer is down to {int(daylight * 60)} minutes.",
                    "action": "Stop adding new outdoor blocks and wrap active ones.",
                    "priority": self._priority_for_level("warning"),
                    "created_at": now_iso,
                    "ttl_minutes": 30,
                    "countdown_minutes": int(daylight * 60),
                    "escalated": False,
                })

        rain_in_hours = context.get("rain_expected_in_hours")
        if isinstance(rain_in_hours, (int, float)) and rain_in_hours <= 2:
            minutes = int(rain_in_hours * 60)
            level = "high" if minutes <= 30 else "warning"
            countdowns.append({
                "type": level,
                "title": "Rain Window Closing",
                "icon": "🌧️",
                "message": f"Rain likely in about {minutes} minutes.",
                "action": "Shift exposed movement to covered/indoor corridors.",
                "priority": self._priority_for_level(level),
                "created_at": now_iso,
                "ttl_minutes": 25,
                "countdown_minutes": minutes,
                "escalated": level == "high",
            })

        return countdowns

    def _age_minutes(self, created_at, now):
        if not created_at:
            return None
        try:
            created_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
            return (now - created_dt).total_seconds() / 60.0
        except Exception:
            return None

    def _context_pressure_score(self, context):
        score = 0

        temp = context.get("temperature_c")
        if isinstance(temp, (int, float)) and (temp >= 40 or temp <= -2):
            score += 28

        crowd = context.get("crowd_score", 0)
        if crowd >= 8:
            score += 18

        weather = context.get("weather_data") or {}
        rain_prob = weather.get("rain_probability", 0)
        if rain_prob >= 0.8:
            score += 22

        news = context.get("news_intel") or {}
        if len(news.get("safety_risks") or []) >= 2:
            score += 20

        health = context.get("health_intel") or {}
        seasonal = (health.get("seasonal_risks") or "").lower()
        if any(k in seasonal for k in ["outbreak", "dengue", "cholera", "epidemic"]):
            score += 20

        return min(100, score)

    def _escalate_level(self, level):
        chain = ["info", "warning", "high", "critical"]
        level = (level or "info").lower()
        if level not in chain:
            return "warning"
        idx = chain.index(level)
        return chain[min(len(chain) - 1, idx + 1)]

    def _priority_for_level(self, level):
        return {
            "critical": Severity.CRITICAL.priority,
            "high": Severity.HIGH.priority,
            "warning": Severity.MEDIUM.priority,
            "info": Severity.INFO.priority,
        }.get((level or "info").lower(), Severity.INFO.priority)

    def _icon_for_level(self, level, existing):
        fallback = {
            "critical": "🚨",
            "high": "⚠️",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        return existing or fallback.get((level or "info").lower(), "ℹ️")
