
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.recommendation_agent import RecommendationAgent

# Mock Itinerary Data
mock_itinerary = {
    "day_1": {
        "title": "Day 1: Arrival & Culture",
        "summary": "Arrive in the city and explore the old town.",
        "morning": {"activity": "Visit Museum", "location": "Old Town", "insider_tip": "Go early!"},
        "afternoon": {"activity": "Lunch at Cafe", "location": "City Center"},
        "evening": {"activity": "Dinner by river", "location": "Riverbank"},
        "estimated_cost": "$50"
    },
    "day_2": {
        "title": "Day 2: Adventure",
        "summary": "Hiking in the mountains.",
        "morning": {"activity": "Mountain Hike", "location": "National Park", "insider_tip": "Bring water"},
        "afternoon": {"activity": "Picnic", "location": "Summit"},
        "evening": {"activity": "Rest", "location": "Hotel"},
        "estimated_cost": "$20"
    },
    "day_3": {
         "title": "Day 3: Departure",
         # No summary to test fallback
         "morning": {"activity": "Shopping", "location": "Market", "insider_tip": "Bargain hard"},
         "afternoon": {"activity": "Airport", "location": "Outskirts"},
         "evening": {"activity": "Flight", "location": "Air"}, 
         "estimated_cost": "$100"
    }
}

def test_preview_generation():
    print("Initializing RecommendationAgent (mocking client)...")
    # We pass None for client as we won't make LLM calls in this specific test
    agent = RecommendationAgent(groq_client=None)
    
    print("Generating preview from mock itinerary...")
    preview = agent._generate_preview_from_itinerary(mock_itinerary)
    
    print(f"Generated {len(preview)} preview items.")
    
    # Assertions
    if len(preview) != 3:
        print(f"[FAILED] Expected 3 days, got {len(preview)}")
        return
        
    # Check Day 1
    d1 = preview[0]
    if d1["title"] != "Day 1: Arrival & Culture":
         print(f"[FAILED] Day 1 title mismatch. Got '{d1['title']}'")
         return
    if d1["highlight"] != "Go early!":
         print(f"[FAILED] Day 1 highlight mismatch. Got '{d1['highlight']}'")
         return

    # Check Day 3 (Fallback description) 
    d3 = preview[2]
    expected_desc_start = "Shopping"
    if not d3["description"].startswith(expected_desc_start):
         print(f"[FAILED] Day 3 description fallback failed. Got '{d3['description']}'")
         return
         
    print("[SUCCESS] Itinerary Preview generation logic is correct!")
    print("\nGenerated Preview Data:")
    import json
    print(json.dumps(preview, indent=2))

if __name__ == "__main__":
    test_preview_generation()
