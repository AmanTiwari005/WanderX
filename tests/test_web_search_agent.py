import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.web_search_agent import WebSearchAgent
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

def test_live_pulse():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    agent = WebSearchAgent(client)
    
    print("Testing Event Radar for Tokyo...")
    events = agent.find_events("Tokyo", "next week")
    print(f"Events Found: {len(events)}")
    print(json.dumps(events, indent=2)[:500])
    
    print("\nTesting Trend Scout for Tokyo...")
    gems = agent.find_hidden_gems("Tokyo")
    print(f"Gems Found: {len(gems)}")
    print(json.dumps(gems, indent=2)[:500])

    print("\nTesting Vibe Check for Tokyo...")
    vibe = agent.get_vibe_check("Tokyo")
    print(json.dumps(vibe, indent=2))

if __name__ == "__main__":
    test_live_pulse()
