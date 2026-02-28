
import json
import os
import glob
from datetime import datetime

TRIPS_DIR = "data/saved_trips"

class TripManager:
    def __init__(self):
        if not os.path.exists(TRIPS_DIR):
            os.makedirs(TRIPS_DIR)

    def save_trip(self, profile, messages, name=None):
        """Saves the current trip state to a JSON file."""
        if not name:
            dest = profile.get("destination", "Unknown")
            date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
            name = f"{dest}_{date_str}"
        
        # Sanitize filename
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        filename = os.path.join(TRIPS_DIR, f"{safe_name}.json")
        
        data = {
            "profile": profile,
            "messages": messages,
            "saved_at": datetime.now().isoformat()
        }
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, f"Trip saved as {safe_name}"
        except Exception as e:
            return False, str(e)

    def list_trips(self):
        """Returns a list of saved trips."""
        files = glob.glob(os.path.join(TRIPS_DIR, "*.json"))
        trips = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    trips.append({
                        "filename": os.path.basename(f),
                        "destination": data.get("profile", {}).get("destination", "Unknown"),
                        "date": data.get("saved_at", "")
                    })
            except:
                continue
        # Sort by date desc
        trips.sort(key=lambda x: x["date"], reverse=True)
        return trips

    def load_trip(self, filename):
        """Loads a trip from a JSON file."""
        filepath = os.path.join(TRIPS_DIR, filename)
        if not os.path.exists(filepath):
            return None, "File not found"
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data, "Success"
        except Exception as e:
            return None, str(e)

    def delete_trip(self, filename):
        """Deletes a saved trip."""
        filepath = os.path.join(TRIPS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
