import sys
import os
import json
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.itinerary_agent import ItineraryAgent

def test_constraint_injection():
    print("Testing Itinerary Constraints Injection...")
    
    agent = ItineraryAgent(None)
    # Mock the client to avoid actual calls, we just want to test logic inside generate_itinerary before the call
    # But generate_itinerary does a lot of work inside. We might need to subclass or inspect internal variables.
    # actually, since the prompt is constructed inside the method, we can't easily see it without
    # 1. Returning the prompt (refactor)
    # 2. Mocking self.client.chat.completions.create and inspecting arguments.
    
    agent.client = MagicMock()
    agent.client.chat.completions.create.return_value.choices[0].message.content = "{}"
    
    # Test Case 1: Rain & Relaxed Pace
    context_1 = {
        "weather_intel": {"condition": "Heavy Rain", "weather_data": {"condition": "Heavy Rain"}},
        "news_intel": {}
    }
    profile_1 = {"pace": "Relaxed", "duration": 3, "interests": "Art"}
    
    agent.generate_itinerary("London", 3, context_1, profile_1)
    
    # Inspect calls
    call_args_1 = agent.client.chat.completions.create.call_args
    prompt_1 = call_args_1[1]['messages'][1]['content']
    
    print("\n[Test 1] Rain & Relaxed Pace")
    if "PACING: RELAXED" in prompt_1:
        print("[PASS] Pacing Rule Detected")
    else:
        print("[FAIL] Pacing Rule Missing")
        
    if "WEATHER ALERT: Precipitation predicted" in prompt_1:
         print("[PASS] Rain Protocol Detected")
    else:
         print("[FAIL] Rain Protocol Missing")

    # Test Case 2: Live Event & Fast Pace
    context_2 = {
        "weather_intel": {"condition": "Sunny"},
        "news_intel": {
            "opportunities": [{"title": "Taylor Swift Concert", "summary": "Wembley Stadium"}]
        }
    }
    profile_2 = {"pace": "Fast", "duration": 3}
    
    agent.generate_itinerary("London", 3, context_2, profile_2)
    
    call_args_2 = agent.client.chat.completions.create.call_args
    prompt_2 = call_args_2[1]['messages'][1]['content']
    
    print("\n[Test 2] Live Event & Fast Pace")
    if "PACING: FAST" in prompt_2:
        print("[PASS] Fast Pace Rule Detected")
    else:
        print("[FAIL] Fast Pace Rule Missing")
        
    if "LIVE EVENT" in prompt_2 and "Taylor Swift" in prompt_2:
         print("[PASS] Live Event Injection Detected")
    else:
         print("[FAIL] Live Event Injection Missing")

    print("\nTest Complete.")

if __name__ == "__main__":
    test_constraint_injection()
