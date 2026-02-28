
import os
import sys
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.packing_agent import PackingAgent
from agents.cultural_agent import CulturalAgent

load_dotenv()

def test_packing_agent():
    print("Testing PackingAgent...")
    agent = PackingAgent()
    profile = {"gender": "Female", "trip_type": "Business"}
    res = agent.generate_packing_list("London", 5, "Rainy, 10-15C", profile)
    
    if "error" in res:
        print(f"FAILED: {res['error']}")
    else:
        print("SUCCESS")
        print(json.dumps(res, indent=2))

def test_cultural_agent():
    print("\nTesting CulturalAgent...")
    agent = CulturalAgent()
    res = agent.get_cultural_intel("Tokyo")
    
    if "error" in res:
        print(f"FAILED: {res['error']}")
        return
        
    required_keys = ["etiquette_dos", "language_tips", "tipping_guide"]
    missing = [k for k in required_keys if k not in res]
    
    if missing:
        print(f"FAILED: Missing keys {missing}")
    else:
        print("SUCCESS")
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("SKIPPING: No GROQ_API_KEY found")
    else:
        test_packing_agent()
        test_cultural_agent()
