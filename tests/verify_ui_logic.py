import sys
import os
import random

# Adjust path to include project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.decision_engine import DecisionEngine

def verify_surprise_me_logic():
    print("--- Verifying 'Surprise Me' Logic ---")
    
    # 1. Verify Data Source
    try:
        de = DecisionEngine()
        recs = de.get_seasonal_recommendations()
        print(f"[PASS] DecisionEngine returned {len(recs)} categories.")
    except Exception as e:
        print(f"[FAIL] DecisionEngine failed: {e}")
        return

    # 2. Verify Flattening for 'Lucky Pick'
    all_places = [p for cat in recs.values() for p in cat]
    if all_places:
        print(f"[PASS] Found {len(all_places)} total destinations for Randomizer.")
        pick = random.choice(all_places)
        print(f"  [Info] Sample lucky pick: {pick}")
    else:
        print("[FAIL] No destinations found for Randomizer!")

    # 3. Simulate Key Uniqueness
    print("\n--- Simulating Streamlit Button Keys ---")
    generated_keys = set()
    duplicates_found = False
    
    # Logic copied from app.py refactor
    cat_order = ["🌏 International Gems", "🧗 Adventure Capital", "❄️ Snowy Peaks", "🏖️ Winter Sun", "🧘 Spiritual Journeys", "🍜 Foodie Paradise"]
    for k in recs.keys():
        if k not in cat_order:
            cat_order.append(k)
    final_tabs = [c for c in cat_order if c in recs]

    for category in final_tabs:
        places = recs[category]
        for place in places:
            # The key formula used in app.py
            key = f"btn_{category}_{place}" 
            
            if key in generated_keys:
                print(f"[FAIL] Duplicate key generated: {key}")
                duplicates_found = True
            else:
                generated_keys.add(key)
    
    if not duplicates_found:
        print(f"[PASS] All {len(generated_keys)} generated keys are unique.")
    else:
        print("[FAIL] Duplicate keys detected!")

if __name__ == "__main__":
    verify_surprise_me_logic()
