"""
Comprehensive engine verification — tests all 3 engines with mock data.
No API keys required. Validates structure, scoring, and edge cases.
"""
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.alert_engine import AlertEngine
from engines.decision_engine import DecisionEngine
from engines.risk_fusion_engine import RiskFusionEngine

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


# ─────────────────────────────────────────────────────────────
# ALERT ENGINE TESTS
# ─────────────────────────────────────────────────────────────
def test_alert_engine():
    print("\n=== ALERT ENGINE ===")
    ae = AlertEngine()

    # Scenario 1: Heavy rain + crowd + news safety
    ctx = {
        "weather_intel": {
            "weather_data": {"description": "heavy rain", "temperature_c": 28, "rain_probability": 5},
            "daylight_remaining": 1.0
        },
        "crowd_intel": {"crowd_score": 9, "crowd_level": "high"},
        "news_intel": {
            "safety_risks": [{"title": "Flooding in area", "severity": "High", "actionable_advice": "Avoid low-lying areas"}],
            "opportunities": [{"title": "Food Festival", "summary": "Annual food fest this week"}]
        },
        "health_intel": {"seasonal_risks": "Dengue outbreak reported", "vaccinations": ["Hep A", "Typhoid", "Tetanus"], "water_safety": "Unsafe — use bottled water"},
        "budget_intel": {"feasibility": "low"},
        "cultural_intel": {"dress_code": "Cover shoulders in temples"},
    }
    alerts = ae.generate_alerts(ctx, profile={"group_type": "Family with kids"})
    
    types = [a["type"] for a in alerts]
    titles = [a["title"] for a in alerts]
    
    check("Rain alert generated", any("Weather" in t for t in titles))
    check("Crowd alert generated", any("Crowd" in t for t in titles))
    check("Safety advisory generated", any("Safety" in t for t in titles))
    check("Health outbreak alert", any("Health" in t for t in titles))
    check("Water safety alert", any("Water" in t for t in titles))
    check("Budget alert", any("Budget" in t for t in titles))
    check("Cultural alert", any("Cultural" in t for t in titles))
    check("Event alert", any("Event" in t for t in titles))
    check("Daylight alert", any("Daylight" in t for t in titles))
    check("All alerts have icon", all("icon" in a for a in alerts))
    check("All alerts have action", all("action" in a for a in alerts))
    check("Priority sorted (first is critical)", alerts[0]["type"] == "critical" if alerts else False,
          f"Got {alerts[0]['type'] if alerts else 'empty'}")
    
    # Scenario 2: Empty context → no crash, empty alerts
    empty_alerts = ae.generate_alerts({})
    check("Empty context → no crash", isinstance(empty_alerts, list))

    # Scenario 3: Profile-aware thresholds (kids = lower heat threshold)
    hot_ctx = {
        "weather_intel": {"weather_data": {"description": "clear sky", "temperature_c": 34}},
    }
    kid_alerts = ae.generate_alerts(hot_ctx, profile={"group_type": "Family with kids"})
    adult_alerts = ae.generate_alerts(hot_ctx, profile={"group_type": "Couple"})
    check("Kids get heat alert at 34°C", any("Heat" in a["title"] for a in kid_alerts))
    check("Adults don't get heat alert at 34°C", not any("Heat" in a["title"] for a in adult_alerts))


# ─────────────────────────────────────────────────────────────
# DECISION ENGINE TESTS
# ─────────────────────────────────────────────────────────────
def test_decision_engine():
    print("\n=== DECISION ENGINE ===")
    de = DecisionEngine()

    # Scenario 1: Rain + outdoor → infeasible
    ctx = {"weather": {"rain_probability": 0.8, "temperature_c": 26}, "time": {"hour": 14}}
    result = de.assess_feasibility("outdoor", ctx)
    check("Rain outdoor → infeasible", result["feasible"] == False)
    check("Has reasons", len(result["reasons"]) > 0)

    # Scenario 2: Late night + adventure → infeasible
    ctx2 = {"weather": {"temperature_c": 22}, "time": {"hour": 21}}
    result2 = de.assess_feasibility("outdoor_adventure", ctx2)
    check("Night adventure → infeasible", result2["feasible"] == False)

    # Scenario 3: High altitude + trek → needs acclimatization
    ctx3 = {"weather": {"temperature_c": 8}, "time": {"hour": 10}, "altitude": 4000}
    result3 = de.assess_feasibility("outdoor_adventure", ctx3)
    check("High altitude adventure → infeasible", result3["feasible"] == False)

    # Scenario 4: Budget mismatch
    ctx4 = {"weather": {"temperature_c": 25}, "time": {"hour": 12}}
    result4 = de.assess_feasibility("luxury", ctx4, profile={"budget": "low"})
    check("Low budget + luxury → infeasible", result4["feasible"] == False)

    # Scenario 5: Elderly + trek
    ctx5 = {"weather": {"temperature_c": 20}, "time": {"hour": 10}}
    result5 = de.assess_feasibility("trek", ctx5, profile={"group_type": "Senior travelers"})
    check("Elderly + trek → infeasible", result5["feasible"] == False)

    # Scenario 6: Plan suggestions with interests
    ctx6 = {"weather": {"rain_probability": 0, "temperature_c": 28}, "time": {"hour": 10}}
    sugs = de.generate_plan_suggestions(ctx6, profile={"interests": "food, history", "budget": "low"})
    titles = [s["title"] for s in sugs]
    check("Interest-based food suggestion", any("Food" in t for t in titles))
    check("Interest-based history suggestion", any("Heritage" in t or "History" in t or "Museum" in t for t in titles))
    check("Budget-adaptive suggestion", any("Budget" in t for t in titles))

    # Scenario 7: Safety warnings with extreme conditions
    ctx7 = {
        "weather": {"rain_probability": 0.9, "temperature_c": 42, "description": "dust storm"},
        "time": {"hour": 23},
        "daylight_remaining": 0.3,
        "altitude": 3500
    }
    warnings = de.get_safety_warnings(ctx7)
    check("Heavy rain warning", any("Rain" in w for w in warnings))
    check("Late night warning", any("Night" in w for w in warnings))
    check("Heat warning", any("Heat" in w for w in warnings))
    check("Altitude warning", any("Altitude" in w for w in warnings))
    check("AQI warning", any("Air" in w or "dust" in w.lower() for w in warnings))

    # Scenario 8: Reachability with terrain & traffic
    reach = de.calculate_reachability_score(250, 5, 3, 17, terrain="mountain", traffic_factor=1.8)
    check("Long mountain distance → challenging", reach["verdict"] in ("Challenging", "Moderately Reachable"))
    check("Has traffic reason", any("traffic" in r.lower() for r in reach["reasons"]))
    check("Has terrain reason", any("terrain" in r.lower() for r in reach["reasons"]))


# ─────────────────────────────────────────────────────────────
# RISK FUSION ENGINE TESTS
# ─────────────────────────────────────────────────────────────
def test_risk_fusion():
    print("\n=== RISK FUSION ENGINE ===")
    rf = RiskFusionEngine()

    # Scenario 1: Multi-source high risk
    result = rf.fuse_risks(
        weather_intel={"weather_data": {"rain_probability": 0.9, "temperature_c": 44, "description": "thunderstorm", "wind_speed": 20}, "daylight_remaining": 0.5},
        news_intel={"safety_risks": [{"title": "Flash flood warning", "severity": "Critical", "actionable_advice": "Evacuate low areas"}]},
        crowd_intel={"crowd_score": 9},
        mobility_intel={},
        health_intel={"water_safety": "Not safe", "seasonal_risks": "Dengue outbreak", "vaccinations": ["Hep A", "Typhoid", "JE", "Malaria"], "weather_health": "altitude sickness possible"},
        budget_intel={"feasibility": "low"},
        cultural_intel={"etiquette_donts": ["Don't touch heads", "No shoes in temples", "Cover knees"], "restricted_areas": "Military area near border"},
        sustainability_intel={"connectivity": "Limited — poor signal in valley"},
    )

    check("Total score > 0", result["total_risk_score"] > 0)
    check("Has risk factors", len(result["risk_factors"]) > 0)
    check("Has recommendations", len(result["actionable_recommendations"]) > 0)
    check("Verdict is Unsafe or Critical", result["verdict"] in ("Unsafe", "Critical"))
    check("Has trending field", "trending" in result)
    check("Breakdown has 9 categories", len(result["breakdown"]) == 9,
          f"Got {len(result['breakdown'])}: {list(result['breakdown'].keys())}")
    check("Weather score > 0", result["breakdown"]["weather"] > 0)
    check("News score > 0", result["breakdown"]["news"] > 0)
    check("Crowd score > 0", result["breakdown"]["crowd"] > 0)
    check("Health score > 0", result["breakdown"]["health"] > 0)
    check("Budget score > 0", result["breakdown"]["budget"] > 0)
    check("Infrastructure score > 0", result["breakdown"]["infrastructure"] > 0)
    check("Cultural score > 0", result["breakdown"]["cultural"] > 0)
    check("Confidence has score", 0 <= result["confidence"]["score"] <= 1)
    check("Risk factors have action", all("action" in r for r in result["risk_factors"]))

    # Scenario 2: Perfectly safe conditions
    safe = rf.fuse_risks(
        weather_intel={"weather_data": {"rain_probability": 0, "temperature_c": 24, "description": "clear sky"}, "daylight_remaining": 8},
        news_intel={"safety_risks": [], "opportunities": [{"title": "Jazz Fest"}]},
        crowd_intel={"crowd_score": 3},
        mobility_intel={"travel_time": 30},
        health_intel={"water_safety": "Safe to drink", "seasonal_risks": "Low risk", "vaccinations": []},
        budget_intel={"feasibility": "high"},
    )
    check("Safe scenario → 'Safe' verdict", safe["verdict"] == "Safe")
    check("Safe scenario → low score", safe["total_risk_score"] < 25)
    check("Safe trend → declining or stable", safe["trending"] in ("declining", "stable"))

    # Scenario 3: Empty inputs → graceful
    empty = rf.fuse_risks({}, {}, {}, {})
    check("Empty inputs → no crash", isinstance(empty, dict))
    check("Empty → has all keys", all(k in empty for k in ["total_risk_score", "verdict", "breakdown", "confidence"]))

    # Scenario 4: Group-type modifier (needs Caution-level risk to trigger)
    family = rf.fuse_risks(
        weather_intel={"weather_data": {"rain_probability": 0.8, "temperature_c": 36, "description": "heavy rain"}, "daylight_remaining": 1.5},
        news_intel={"safety_risks": [{"title": "Flooding", "severity": "Medium"}]},
        crowd_intel={"crowd_score": 7},
        mobility_intel={},
        profile={"group_type": "Family with children"}
    )
    check("Family modifier in verdict", "Extra Care" in family.get("verdict", "") or family["total_risk_score"] >= 25,
          f"Got verdict: {family.get('verdict')}, score: {family.get('total_risk_score')}")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_alert_engine()
    test_decision_engine()
    test_risk_fusion()

    print(f"\n{'='*50}")
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {failed} TEST(S) FAILED")
