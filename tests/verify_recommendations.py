import sys
import os

# Adjust path to include project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.decision_engine import DecisionEngine

def verify_recommendations():
    de = DecisionEngine()
    recs = de.get_seasonal_recommendations()
    
    print("--- Verifying Seasonal Recommendations ---")
    
    expected_categories = [
        "🌏 International Gems",
        "🧗 Adventure Capital",
        "🧘 Spiritual Journeys",
        "🍜 Foodie Paradise"
    ]
    
    all_passed = True
    
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            clean_text = text.encode('ascii', 'ignore').decode('ascii')
            print(clean_text)

    for cat in expected_categories:
        if cat in recs:
            count = len(recs[cat])
            safe_print(f"[PASS] Category '{cat}' found with {count} items.")
            if count < 3:
                safe_print(f"  [WARN] Category '{cat}' has few items ({count}).")
        else:
            safe_print(f"[FAIL] Category '{cat}' MISSING.")
            all_passed = False
            
    # Print a sample to ensure strings look right
    safe_print("\nSample Data:")
    for cat, items in recs.items():
        try:
             print(f"  {cat}: {items[:3]}...")
        except:
             safe_print(f"  {cat}: {items[:3]}...")
        
    if all_passed:
        safe_print("\n[SUCCESS] Verification Successful: All new categories present.")
    else:
        safe_print("\n[FAIL] Verification Failed: Missing categories.")

if __name__ == "__main__":
    verify_recommendations()
