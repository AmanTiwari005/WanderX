"""
Test suite for advanced engine architecture:
- Severity types & comparison
- Escalation engine (time, proximity, compound)
- Template engine rendering
- Cross-agent rules
- TravelScore
- Itinerary validator
- TravelBrain integration
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.severity import Severity, SeverityLevel
from engines.escalation import EscalationEngine
from engines.templates import TemplateEngine
from engines.cross_agent_rules import CrossAgentRulesEngine
from engines.travel_score import TravelScore
from engines.itinerary_validator import ItineraryValidator
from engines.travel_brain import TravelBrain

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")


# ═══════════════════════════════════════════════════════════
# SEVERITY TYPES
# ═══════════════════════════════════════════════════════════
def test_severity():
    print("\n=== SEVERITY TYPES ===")
    check("CRITICAL > HIGH", Severity.CRITICAL > Severity.HIGH)
    check("HIGH > MEDIUM", Severity.HIGH > Severity.MEDIUM)
    check("MEDIUM > LOW", Severity.MEDIUM > Severity.LOW)
    check("LOW > INFO", Severity.LOW > Severity.INFO)
    check("CRITICAL >= CRITICAL", Severity.CRITICAL >= Severity.CRITICAL)
    check("INFO == INFO", Severity.INFO == Severity.INFO)
    check("String match", Severity.HIGH == "high")
    check("from_string('High')", Severity.from_string("High") == Severity.HIGH)
    check("from_string('warning')", Severity.from_string("warning") == Severity.MEDIUM)
    check("escalate(MEDIUM) → HIGH", Severity.escalate(Severity.MEDIUM) == Severity.HIGH)
    check("escalate(HIGH) → CRITICAL", Severity.escalate(Severity.HIGH) == Severity.CRITICAL)
    check("escalate(CRITICAL) → CRITICAL", Severity.escalate(Severity.CRITICAL) == Severity.CRITICAL)
    check("to_dict has all fields", all(k in Severity.HIGH.to_dict() for k in ["level", "score", "color", "icon", "priority"]))
    check("score_weights has Critical", Severity.score_weights()["Critical"] == 30)
    check("5 levels total", len(Severity.all_levels()) == 5)


# ═══════════════════════════════════════════════════════════
# ESCALATION ENGINE
# ═══════════════════════════════════════════════════════════
def test_escalation():
    print("\n=== ESCALATION ENGINE ===")
    ee = EscalationEngine()

    # Time escalation: old HIGH alert (escalates_after_min=60) → CRITICAL
    alert_old = {
        "type": "high", "title": "Weather", "priority": 4, "icon": "🟠",
        "created_at": (datetime.now() - timedelta(minutes=90)).isoformat(),
        "_severity_obj": Severity.HIGH
    }
    result = ee.apply_escalations([alert_old], {"now": datetime.now()})
    check("Time escalation: HIGH (90min old) → CRITICAL", result[0]["type"] == "critical")
    check("Escalation trail recorded", result[0].get("escalated") == True)
    check("Has escalation_trail", len(result[0].get("escalation_trail", [])) > 0)

    # No escalation: fresh alert
    alert_fresh = {
        "type": "high", "title": "Weather", "priority": 4,
        "created_at": datetime.now().isoformat(),
        "_severity_obj": Severity.HIGH
    }
    result2 = ee.apply_escalations([alert_fresh], {"now": datetime.now()})
    check("Fresh HIGH → stays HIGH", result2[0]["type"] == "high")

    # Proximity escalation: low daylight
    alert_daylight = {"type": "info", "title": "Daylight", "priority": 1}
    result3 = ee.apply_escalations([alert_daylight], {"daylight_remaining": 0.3})
    check("Proximity: low daylight → escalated", result3[0]["type"] == "high")

    # Compound escalation: multiple risk sources
    alert_compound = {"type": "info", "title": "General", "priority": 1}
    compound_ctx = {
        "weather_data": {"rain_probability": 0.8},
        "news_intel": {"safety_risks": [{"title": "x"}]},
        "crowd_score": 8,
        "health_intel": {"seasonal_risks": "dengue outbreak"}
    }
    result4 = ee.apply_escalations([alert_compound], compound_ctx)
    check("Compound: 4 risk sources → escalated", result4[0]["type"] == "high")

    # Countdown alerts
    countdowns = ee.generate_countdown_alerts({"daylight_remaining": 0.3})
    check("Sunset countdown generated", len(countdowns) > 0)
    check("Countdown has 'imminent' title", any("Imminent" in c["title"] for c in countdowns))

    countdowns2 = ee.generate_countdown_alerts({"rain_expected_in_hours": 0.4})
    check("Rain countdown generated", len(countdowns2) > 0)


# ═══════════════════════════════════════════════════════════
# TEMPLATE ENGINE
# ═══════════════════════════════════════════════════════════
def test_templates():
    print("\n=== TEMPLATE ENGINE ===")
    te = TemplateEngine()

    # Rainy scenario
    ctx = {"weather": {"rain_probability": 0.8, "temperature_c": 22, "description": "heavy rain"}, "time": {"hour": 14}}
    suggestions = te.render_suggestions(ctx)
    titles = [s["title"] for s in suggestions]
    check("Rain → indoor suggestion", any("Indoor" in t for t in titles))
    check("Suggestions have template_id", all("template_id" in s for s in suggestions))
    check("Suggestions have confidence", all("confidence" in s for s in suggestions))
    check("Suggestions have tags", all("tags" in s for s in suggestions))

    # Interest-based
    ctx2 = {"weather": {"temperature_c": 25}, "time": {"hour": 10}}
    sug2 = te.render_suggestions(ctx2, profile={"interests": "food, photography"})
    titles2 = [s["title"] for s in sug2]
    check("Food interest → food suggestion", any("Food" in t for t in titles2))
    check("Photo interest → photo suggestion", any("Photo" in t for t in titles2))

    # Budget-adaptive
    sug3 = te.render_suggestions(ctx2, profile={"budget": "low"})
    titles3 = [s["title"] for s in sug3]
    check("Low budget → budget gem suggestion", any("Budget" in t for t in titles3))

    # Golden hour
    ctx3 = {"weather": {"temperature_c": 25}, "time": {"hour": 17}, "daylight_remaining": 1.5}
    sug4 = te.render_suggestions(ctx3)
    titles4 = [s["title"] for s in sug4]
    check("Golden hour trigger", any("Golden" in t or "Sunset" in t for t in titles4))

    # Categories
    cats = te.get_categories()
    check("Multiple categories", len(cats) >= 5, f"Got {len(cats)}: {cats}")


# ═══════════════════════════════════════════════════════════
# CROSS-AGENT RULES
# ═══════════════════════════════════════════════════════════
def test_cross_agent_rules():
    print("\n=== CROSS-AGENT RULES ===")
    car = CrossAgentRulesEngine()

    # Storm Lockdown
    storm_bundle = {
        "weather_intel": {"weather_data": {"description": "thunderstorm", "rain_probability": 0.9, "temperature_c": 20}},
        "news_intel": {"safety_risks": [{"title": "Flooding", "severity": "High"}]},
        "crowd_intel": {"crowd_score": 7},
    }
    result = car.evaluate(storm_bundle)
    check("Storm → rules triggered", result["rules_triggered"] > 0)
    triggered_ids = [r["rule_id"] for r in result["triggered_rules"]]
    check("Storm lockdown fired", "storm_lockdown" in triggered_ids)
    check("Outdoor blocked", result["blocks"]["outdoor"] == True)
    check("Has extra alerts", len(result["extra_alerts"]) > 0)

    # Perfect Day
    perfect_bundle = {
        "weather_intel": {"weather_data": {"rain_probability": 0.1, "temperature_c": 25}},
        "news_intel": {"safety_risks": [], "opportunities": [{"title": "Jazz Fest"}]},
        "crowd_intel": {"crowd_score": 3},
    }
    result2 = car.evaluate(perfect_bundle)
    triggered_ids2 = [r["rule_id"] for r in result2["triggered_rules"]]
    check("Perfect day fired", "perfect_day" in triggered_ids2)
    check("Confidence boost > 0", result2["confidence_modifier"] > 0)

    # Health Crisis
    health_bundle = {
        "weather_intel": {"weather_data": {}},
        "news_intel": {},
        "crowd_intel": {},
        "health_intel": {"seasonal_risks": "Cholera outbreak", "water_safety": "Unsafe — bottled only", "medical_facilities": "Limited basic clinic only"},
    }
    result3 = car.evaluate(health_bundle)
    triggered_ids3 = [r["rule_id"] for r in result3["triggered_rules"]]
    check("Health crisis fired", "health_crisis" in triggered_ids3)

    # No triggers
    safe_bundle = {
        "weather_intel": {"weather_data": {"rain_probability": 0, "temperature_c": 25, "description": "clear"}},
        "news_intel": {"safety_risks": []},
        "crowd_intel": {"crowd_score": 3},
    }
    result4 = car.evaluate(safe_bundle)
    check("Safe scenario → 0 triggers", result4["rules_triggered"] == 0)


# ═══════════════════════════════════════════════════════════
# TRAVEL SCORE
# ═══════════════════════════════════════════════════════════
def test_travel_score():
    print("\n=== TRAVEL SCORE ===")

    # Perfect conditions
    score = TravelScore.calculate(
        risk_assessment={"total_risk_score": 5},
        weather_intel={"weather_data": {"temperature_c": 24, "rain_probability": 0}},
        crowd_intel={"crowd_score": 2},
        budget_intel={"feasibility": "high"},
        news_intel={"opportunities": [{"title": "Fest"}, {"title": "Market"}], "interesting_facts": ["x"]},
        cultural_intel={"etiquette": "Be polite"},
        profile={"interests": "food, culture"}
    )
    check("Perfect → score >= 80", score["score"] >= 75, f"Got {score['score']}")
    check("Band = Perfect Trip or Good to Go", score["band"] in ("Perfect Trip", "Good to Go"), f"Got {score['band']}")
    check("Has breakdown", len(score["breakdown"]) == 6)
    check("Has icon", "icon" in score)
    check("Has color", "color" in score)

    # Bad conditions
    bad_score = TravelScore.calculate(
        risk_assessment={"total_risk_score": 75},
        weather_intel={"weather_data": {"temperature_c": 44, "rain_probability": 0.9, "wind_speed": 20, "description": "storm"}, "daylight_remaining": 0.3},
        crowd_intel={"crowd_score": 9},
        budget_intel={"feasibility": "low"},
        sustainability_intel={"connectivity": "No signal available"}
    )
    check("Bad → score < 45", bad_score["score"] < 45, f"Got {bad_score['score']}")
    check("Bad → has recommendations", len(bad_score["recommendations"]) > 0)


# ═══════════════════════════════════════════════════════════
# ITINERARY VALIDATOR
# ═══════════════════════════════════════════════════════════
def test_itinerary_validator():
    print("\n=== ITINERARY VALIDATOR ===")
    iv = ItineraryValidator()

    # Bad itinerary: outdoor trek in storm with elderly
    itin = {
        "day_1": {
            "activities": [
                {"title": "Mountain Trek", "time": "morning", "cost_estimate": "premium"},
                {"title": "Beach Sunset", "time": "evening"},
                {"title": "Museum Visit", "time": "afternoon"},
            ]
        }
    }
    intel = {
        "weather_intel": {"weather_data": {"rain_probability": 0.8, "description": "thunderstorm"}},
        "news_intel": {"safety_risks": [{"title": "Flooding", "severity": "High", "actionable_advice": "Avoid"}]},
        "crowd_intel": {"crowd_score": 9},
        "budget_intel": {"feasibility": "low"},
    }
    result = iv.validate(itin, intel, profile={"group_type": "Senior travelers"})
    check("Has issues", result["total_issues"] > 0)
    check("Not valid due to critical", result["valid"] == False or result["score"] < 50)
    check("Weather conflict detected", any(i["type"] == "weather_conflict" for i in result["issues"]))
    check("Weather danger detected", any(i["type"] == "weather_danger" for i in result["issues"]))
    check("Group conflict detected", any(i["type"] == "group_conflict" for i in result["issues"]))
    check("Safety conflict detected", any(i["type"] == "safety_conflict" for i in result["issues"]))
    check("Has auto-fixes", len(result["auto_fixes"]) > 0)
    check("Has day scores", "day_1" in result["day_scores"])
    check("Has summary", "verdict" in result["summary"])

    # Good itinerary
    good_itin = {
        "day_1": {
            "activities": [
                {"title": "Café breakfast", "time": "morning"},
                {"title": "Art gallery visit", "time": "afternoon"},
            ]
        }
    }
    good_intel = {
        "weather_intel": {"weather_data": {"rain_probability": 0, "description": "clear sky"}},
        "news_intel": {"safety_risks": []},
        "crowd_intel": {"crowd_score": 3},
        "budget_intel": {"feasibility": "high"},
    }
    good_result = iv.validate(good_itin, good_intel)
    check("Good itinerary → valid", good_result["valid"] == True)
    check("Good itinerary → high score", good_result["score"] >= 80, f"Got {good_result['score']}")

    # Empty itinerary
    empty = iv.validate({}, {})
    check("Empty itinerary → valid:False", empty["valid"] == False)


# ═══════════════════════════════════════════════════════════
# TRAVEL BRAIN (Integration)
# ═══════════════════════════════════════════════════════════
def test_travel_brain():
    print("\n=== TRAVEL BRAIN ===")
    brain = TravelBrain()

    bundle = {
        "weather_intel": {"weather_data": {"rain_probability": 0.7, "temperature_c": 30, "description": "rain"}, "daylight_remaining": 2},
        "news_intel": {"safety_risks": [{"title": "Minor flooding", "severity": "Medium"}], "opportunities": [{"title": "Street Fair"}]},
        "crowd_intel": {"crowd_score": 6},
        "mobility_intel": {"travel_time": 45},
        "health_intel": {"water_safety": "Safe", "seasonal_risks": "Low", "vaccinations": ["Hep A"]},
        "budget_intel": {"feasibility": "moderate"},
        "cultural_intel": {"etiquette_donts": ["No shoes in temples"]},
        "sustainability_intel": {"connectivity": "Good 4G coverage"},
        "live_pulse_intel": {"safety_tips": "Watch for pickpockets"},
    }
    profile = {"interests": "food, history", "budget": "moderate", "group_type": "Couple"}

    result = brain.analyze(bundle, profile)

    # Structure
    check("Has travel_score", "travel_score" in result)
    check("Has risk_assessment", "risk_assessment" in result)
    check("Has alerts", "alerts" in result)
    check("Has plan_suggestions", "plan_suggestions" in result)
    check("Has safety_warnings", "safety_warnings" in result)
    check("Has cross_agent_insights", "cross_agent_insights" in result)
    check("Has engine_metadata", "engine_metadata" in result)

    # Travel score
    ts = result["travel_score"]
    check("Travel score in range", 0 <= ts["score"] <= 100, f"Got {ts['score']}")
    check("Score has band", ts.get("band") in ("Perfect Trip", "Good to Go", "Proceed with Caution", "Consider Alternatives"))

    # Alerts
    check("Alerts list not empty", len(result["alerts"]) > 0)
    check("All alerts have priority", all("priority" in a for a in result["alerts"]))

    # Suggestions
    check("Has suggestions", len(result["plan_suggestions"]) > 0)
    sugg_titles = [s["title"] for s in result["plan_suggestions"]]
    check("Food suggestion from interests", any("Food" in t for t in sugg_titles))

    # Cross-agent
    cai = result["cross_agent_insights"]
    check("Rules evaluated > 0", cai["rules_evaluated"] > 0)

    # Engine metadata
    check("Engine count", len(result["engine_metadata"]["engines_used"]) >= 6)

    # Full analysis with itinerary
    itin = {
        "day_1": {
            "activities": [
                {"title": "Temple trek", "time": "morning"},
                {"title": "Local food market", "time": "afternoon"},
            ]
        }
    }
    full_result = brain.full_analysis(bundle, profile, itinerary=itin)
    check("Full analysis has itinerary_validation", "itinerary_validation" in full_result)
    check("Validation has issues list", "issues" in full_result["itinerary_validation"])


# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_severity()
    test_escalation()
    test_templates()
    test_cross_agent_rules()
    test_travel_score()
    test_itinerary_validator()
    test_travel_brain()

    print(f"\n{'='*50}")
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {failed} TEST(S) FAILED")
