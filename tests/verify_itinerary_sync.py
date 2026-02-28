import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.recommendation_agent import RecommendationAgent

def test_preview_generation():
    print("Testing Itinerary Preview Generation...")
    
    # Mock Itinerary Data
    mock_itinerary = {
        "day_1": {
            "title": "Day 1: Arrival & Culture",
            "morning": {"activity": "Visit Senso-ji Temple", "location": "Asakusa"},
            "afternoon": {"activity": "River Cruise", "location": "Sumida River"},
            "evening": {"activity": "Dinner at Izakaya", "location": "Shinjuku"},
            "estimated_cost": "~¥10,000"
        },
        "day_2": {
            "title": "Day 2: Modern Tokyo",
            "morning": {"activity": "TeamLab Planets", "location": "Toyosu"},
            "afternoon": {"activity": "Shopping in Ginza", "location": "Ginza"},
            "evening": {"activity": "Robot Restaurant", "location": "Shinjuku"},
            "estimated_cost": "~¥15,000"
        }
    }
    
    # Instantiate Agent (Mock client not needed for this internal method test)
    agent = RecommendationAgent(None)
    
    # Generate Preview
    preview = agent._generate_preview_from_itinerary(mock_itinerary)
    
    # Verify
    expected_desc_1 = "**Morning:** Visit Senso-ji Temple\n\n**Afternoon:** River Cruise\n\n**Evening:** Dinner at Izakaya"
    
    print(f"\n[Day 1] Expected: {repr(expected_desc_1)}")
    print(f"[Day 1] Actual:   {repr(preview[0]['description'])}")
    
    if preview[0]['description'] == expected_desc_1:
        print("[PASS] Day 1 Match Success!")
    else:
        print("[FAIL] Day 1 Mismatch!")
        
    expected_desc_2 = "**Morning:** TeamLab Planets\n\n**Afternoon:** Shopping in Ginza\n\n**Evening:** Robot Restaurant"
    
    if preview[1]['description'] == expected_desc_2:
         print("[PASS] Day 2 Match Success!")
    else:
         print("[FAIL] Day 2 Mismatch!")

    print("\nTest Complete.")

if __name__ == "__main__":
    test_preview_generation()
