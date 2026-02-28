"""
Quick verification of Decision Engine logic.
Updated to import from engines/ (not utils/).
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from engines.decision_engine import DecisionEngine
import json

def test_decision_logic():
    de = DecisionEngine()

    # SCENARIO 1: Heavy Rain
    print("--- SCENARIO 1: HEAVY RAIN ---")
    ctx = {
        "weather": {"description": "heavy intensity rain", "temperature_c": 26, "rain_probability": 3.5},
        "time": {"hour": 14}
    }
    warnings = de.get_safety_warnings(ctx)
    suggestions = de.generate_plan_suggestions(ctx)

    print("Warnings:", [w.encode('ascii', 'ignore').decode() for w in warnings])
    print("Suggestions:", [s["title"] for s in suggestions])

    warning_check = any("Rain" in w for w in warnings)
    suggestion_check = any("Indoor" in s["title"] for s in suggestions)

    if warning_check and suggestion_check:
        print("[PASS] Rain Scenario Passed")
    else:
        print("[FAIL] Rain Scenario Failed")

    # SCENARIO 2: Late Night
    print("\n--- SCENARIO 2: LATE NIGHT ---")
    ctx["time"]["hour"] = 23
    warnings = de.get_safety_warnings(ctx)
    suggestions = de.generate_plan_suggestions(ctx)

    print("Warnings:", [w.encode('ascii', 'ignore').decode() for w in warnings])

    night_warning = any("Night" in w for w in warnings)
    if night_warning:
        print("[PASS] Night Scenario Passed")
    else:
        print("[FAIL] Night Scenario Failed")

    # SCENARIO 3: High Altitude Trek
    print("\n--- SCENARIO 3: HIGH ALTITUDE TREK ---")
    ctx3 = {
        "weather": {"temperature_c": 5, "rain_probability": 0.6},
        "time": {"hour": 10},
        "altitude": 4200
    }
    result = de.assess_feasibility("trek", ctx3)
    print(f"Feasible: {result['feasible']}, Reasons: {result['reasons']}")
    if not result["feasible"]:
        print("[PASS] Altitude Scenario Passed")
    else:
        print("[FAIL] Altitude Scenario Failed")

    # SCENARIO 4: Low Budget + Luxury
    print("\n--- SCENARIO 4: BUDGET MISMATCH ---")
    ctx4 = {"weather": {"temperature_c": 25}, "time": {"hour": 12}}
    result = de.assess_feasibility("luxury", ctx4, profile={"budget": "low"})
    print(f"Feasible: {result['feasible']}, Reasons: {result['reasons']}")
    if not result["feasible"]:
        print("[PASS] Budget Scenario Passed")
    else:
        print("[FAIL] Budget Scenario Failed")

if __name__ == "__main__":
    test_decision_logic()
