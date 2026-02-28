import json
import os
import datetime
from pathlib import Path

ANALYTICS_FILE = os.path.join(os.path.dirname(__file__), "../data/analytics_events.json")

def track_event(event_type, event_data):
    """
    Logs user events for analytics.
    
    Args:
        event_type (str): e.g., "suggestion_click", "plan_accepted", "feedback"
        event_data (dict): Details about the event
    """
    try:
        # ensure directory exists
        Path(os.path.dirname(ANALYTICS_FILE)).mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": event_type,
            "data": event_data
        }
        
        # Append to JSON lines file
        with open(ANALYTICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
    except Exception as e:
        print(f"Analytics error: {e}")

def get_analytics_summary():
    """
    Returns basic usage stats.
    """
    if not os.path.exists(ANALYTICS_FILE):
        return {}
        
    counts = {}
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                entry = json.loads(line)
                etype = entry.get("type", "unknown")
                counts[etype] = counts.get(etype, 0) + 1
    except:
        pass
    return counts
