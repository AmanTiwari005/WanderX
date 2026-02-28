"""
Itinerary Validation Layer for WanderX.

Post-generation validator that checks each itinerary slot against
live conditions (weather, time, budget, safety, crowd, group, travel time).
"""
import logging
from engines.severity import Severity

logger = logging.getLogger("wanderx.itinerary_validator")


class ItineraryValidator:
    """
    Validates generated itineraries against real-time intelligence.
    """

    # Activity keywords → type classification
    OUTDOOR_KEYWORDS = [
        "trek", "hike", "walk", "beach", "waterfall", "viewpoint", "safari",
        "cycling", "rafting", "kayak", "paragliding", "zip", "climb",
        "garden", "park", "lake", "river", "outdoor", "sunrise", "sunset",
        "snorkeling", "diving", "surfing", "camping", "picnic", "trail"
    ]
    ADVENTURE_KEYWORDS = [
        "trek", "hike", "climb", "rafting", "paragliding", "zip", "bungee",
        "safari", "caving", "rappelling", "mountaineering", "diving", "surfing"
    ]
    NIGHT_SENSITIVE = [
        "sunrise", "viewpoint", "garden", "park", "outdoor", "trek", "hike",
        "beach", "cycling", "nature", "wildlife", "bird watching"
    ]

    def validate(self, itinerary, intel_bundle, profile=None):
        """
        Validate an itinerary against current intelligence.
        
        Args:
            itinerary: Dict with day_1, day_2, ... keys, each containing activity slots
            intel_bundle: Dict with weather_intel, news_intel, crowd_intel, etc.
            profile: User profile dict
            
        Returns:
            dict: {
                valid: bool,
                score: 0-100,
                total_issues: int,
                issues: [...],
                day_scores: {day_1: score, ...},
                auto_fixes: [...]
            }
        """
        if not itinerary or itinerary.get("error"):
            return {"valid": False, "score": 0, "total_issues": 0,
                    "issues": [{"type": "error", "message": "No valid itinerary to validate"}],
                    "day_scores": {}, "auto_fixes": []}

        profile = profile or {}
        weather_intel = intel_bundle.get("weather_intel", {})
        news_intel = intel_bundle.get("news_intel", {})
        crowd_intel = intel_bundle.get("crowd_intel", {})
        budget_intel = intel_bundle.get("budget_intel", {})
        health_intel = intel_bundle.get("health_intel", {})
        risk_assessment = intel_bundle.get("risk_assessment", {})

        weather_data = weather_intel.get("weather_data", {}) if weather_intel else {}
        group_type = (profile.get("group_type") or "").lower()

        all_issues = []
        day_scores = {}
        auto_fixes = []

        day_keys = sorted([k for k in itinerary.keys() if k.startswith("day_")])

        for day_key in day_keys:
            day_data = itinerary[day_key]
            day_issues = []
            day_penalty = 0

            # Get activities for this day
            activities = day_data.get("activities", day_data.get("slots", []))
            if isinstance(activities, dict):
                # Handle {morning: ..., afternoon: ..., evening: ...} format
                slot_list = []
                for time_slot, activity in activities.items():
                    if isinstance(activity, dict):
                        activity["_time_slot"] = time_slot
                        slot_list.append(activity)
                    elif isinstance(activity, str):
                        slot_list.append({"title": activity, "_time_slot": time_slot})
                activities = slot_list

            if not isinstance(activities, list):
                activities = []

            for slot in activities:
                title = (slot.get("title") or slot.get("activity") or "").lower()
                time_slot = (slot.get("time") or slot.get("_time_slot") or "").lower()
                is_outdoor = any(kw in title for kw in self.OUTDOOR_KEYWORDS)
                is_adventure = any(kw in title for kw in self.ADVENTURE_KEYWORDS)
                is_night_sensitive = any(kw in title for kw in self.NIGHT_SENSITIVE)

                # ── CHECK 1: Weather compatibility ──────────────
                rain_prob = weather_data.get("rain_probability", 0)
                if is_outdoor and rain_prob > 0.6:
                    issue = {
                        "day": day_key,
                        "slot": time_slot,
                        "activity": slot.get("title", title),
                        "type": "weather_conflict",
                        "severity": "high",
                        "message": f"Outdoor activity during likely rain ({rain_prob:.0%} chance).",
                        "suggestion": "Consider indoor alternative or reschedule."
                    }
                    day_issues.append(issue)
                    day_penalty += 15
                    auto_fixes.append({
                        "day": day_key, "slot": time_slot,
                        "original": slot.get("title", ""),
                        "fix_type": "weather_swap",
                        "suggestion": "Indoor cultural experience or museum visit"
                    })

                desc = (weather_data.get("description") or "").lower()
                if is_outdoor and any(kw in desc for kw in ["storm", "thunder", "cyclone"]):
                    day_issues.append({
                        "day": day_key, "slot": time_slot,
                        "activity": slot.get("title", title),
                        "type": "weather_danger",
                        "severity": "critical",
                        "message": f"Outdoor activity during severe weather ({desc}). Unsafe!",
                        "suggestion": "Cancel outdoor plans. Move everything indoors."
                    })
                    day_penalty += 25

                # ── CHECK 2: Time logic ─────────────────────────
                if is_night_sensitive and time_slot in ("evening", "night"):
                    day_issues.append({
                        "day": day_key, "slot": time_slot,
                        "activity": slot.get("title", title),
                        "type": "time_conflict",
                        "severity": "medium",
                        "message": "Activity needs daylight but scheduled for evening.",
                        "suggestion": "Move to morning slot or swap with an evening-friendly activity."
                    })
                    day_penalty += 10

                # ── CHECK 3: Budget alignment ───────────────────
                cost_str = slot.get("cost_estimate", slot.get("cost", ""))
                if cost_str and budget_intel and not budget_intel.get("error"):
                    feasibility = (budget_intel.get("feasibility") or "").lower()
                    if feasibility == "low" and any(kw in str(cost_str).lower() for kw in ["premium", "luxury", "expensive"]):
                        day_issues.append({
                            "day": day_key, "slot": time_slot,
                            "activity": slot.get("title", title),
                            "type": "budget_conflict",
                            "severity": "medium",
                            "message": "Activity may exceed your budget.",
                            "suggestion": "Look for a budget-friendly alternative."
                        })
                        day_penalty += 8

                # ── CHECK 4: Safety conflicts ───────────────────
                if news_intel and news_intel.get("safety_risks"):
                    for risk in news_intel["safety_risks"]:
                        risk_sev = risk.get("severity", "Medium")
                        if risk_sev in ("High", "Critical"):
                            if is_outdoor:
                                day_issues.append({
                                    "day": day_key, "slot": time_slot,
                                    "activity": slot.get("title", title),
                                    "type": "safety_conflict",
                                    "severity": "high",
                                    "message": f"Activity in area with safety risk: {risk.get('title', 'Unknown')}",
                                    "suggestion": risk.get("actionable_advice", "Reconsider this activity.")
                                })
                                day_penalty += 15
                            break  # Only flag once per slot

                # ── CHECK 5: Crowd feasibility ──────────────────
                crowd_score = crowd_intel.get("crowd_score", 0) if crowd_intel else 0
                if crowd_score >= 8 and time_slot in ("morning", "afternoon"):
                    if any(kw in title for kw in ["temple", "monument", "fort", "palace", "museum", "market"]):
                        day_issues.append({
                            "day": day_key, "slot": time_slot,
                            "activity": slot.get("title", title),
                            "type": "crowd_conflict",
                            "severity": "low",
                            "message": "Popular attraction on a high-crowd day.",
                            "suggestion": "Arrive early (before 8 AM) or visit during lunch hours for smaller crowds."
                        })
                        day_penalty += 5

                # ── CHECK 6: Group suitability ──────────────────
                if is_adventure:
                    if any(kw in group_type for kw in ["elder", "senior"]):
                        day_issues.append({
                            "day": day_key, "slot": time_slot,
                            "activity": slot.get("title", title),
                            "type": "group_conflict",
                            "severity": "high",
                            "message": "Adventure activity not suitable for elderly travelers.",
                            "suggestion": "Replace with a gentler scenic option."
                        })
                        day_penalty += 15
                    elif any(kw in group_type for kw in ["famil", "child", "kid"]):
                        day_issues.append({
                            "day": day_key, "slot": time_slot,
                            "activity": slot.get("title", title),
                            "type": "group_conflict",
                            "severity": "medium",
                            "message": "Adventure activity — check age restrictions for children.",
                            "suggestion": "Verify age requirements or choose a family-friendly alternative."
                        })
                        day_penalty += 8

            all_issues.extend(day_issues)
            day_score = max(0, 100 - day_penalty)
            day_scores[day_key] = day_score

        # Overall score
        if day_scores:
            overall_score = round(sum(day_scores.values()) / len(day_scores))
        else:
            overall_score = 100

        return {
            "valid": overall_score >= 50 and not any(i["severity"] == "critical" for i in all_issues),
            "score": overall_score,
            "total_issues": len(all_issues),
            "issues": all_issues,
            "day_scores": day_scores,
            "auto_fixes": auto_fixes,
            "summary": self._generate_summary(overall_score, all_issues)
        }

    def _generate_summary(self, score, issues):
        """Generate a human-readable validation summary."""
        critical = sum(1 for i in issues if i["severity"] == "critical")
        high = sum(1 for i in issues if i["severity"] == "high")
        medium = sum(1 for i in issues if i["severity"] == "medium")
        low = sum(1 for i in issues if i["severity"] == "low")

        if score >= 85:
            verdict = "Itinerary looks great! Minor optimization possible."
        elif score >= 60:
            verdict = "Itinerary is workable but has some concerns."
        elif score >= 40:
            verdict = "Significant issues found — consider modifications."
        else:
            verdict = "Itinerary has critical problems — needs rework."

        return {
            "verdict": verdict,
            "score": score,
            "breakdown": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low
            }
        }
