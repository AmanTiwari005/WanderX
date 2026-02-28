from utils.model_registry import get_active_model_id
from datetime import datetime

import os
import json

class CrowdAgent:
    def __init__(self, groq_client=None):
        self.client = groq_client
        self.model = get_active_model_id()
        self.SEASONAL_EVENTS = {
            "Varanasi": [
                {"month": 11, "event": "Dev Deepawali", "crowd_level": 9, "duration_days": 3},
                {"month": 10, "event": "Dussehra", "crowd_level": 8, "duration_days": 10},
                {"month": 3, "event": "Holi", "crowd_level": 7, "duration_days": 2},
            ],
            "Goa": [
                {"month": 12, "event": "Christmas & New Year", "crowd_level": 10, "duration_days": 10},
                {"month": 2, "event": "Carnival", "crowd_level": 9, "duration_days": 4},
                {"month": 11, "event": "International Film Festival", "crowd_level": 6, "duration_days": 7},
            ],
            "Jaipur": [
                {"month": 3, "event": "Holi", "crowd_level": 8, "duration_days": 2},
                {"month": 11, "event": "Diwali", "crowd_level": 9, "duration_days": 5},
                {"month": 1, "event": "Jaipur Literature Festival", "crowd_level": 7, "duration_days": 5},
            ],
            "Rishikesh": [
                {"month": 3, "event": "International Yoga Festival", "crowd_level": 7, "duration_days": 7},
                {"month": 9, "event": "Ganga Aarti Peak Season", "crowd_level": 6, "duration_days": 30},
            ],
            "Amritsar": [
                {"month": 11, "event": "Guru Nanak Jayanti", "crowd_level": 9, "duration_days": 3},
                {"month": 4, "event": "Vaisakhi", "crowd_level": 10, "duration_days": 2},
            ],
            "Udaipur": [
                {"month": 3, "event": "Holi", "crowd_level": 7, "duration_days": 2},
                {"month": 10, "event": "Dussehra", "crowd_level": 8, "duration_days": 10},
            ],
            "Kerala": [
                {"month": 8, "event": "Onam", "crowd_level": 8, "duration_days": 10},
                {"month": 4, "event": "Vishu", "crowd_level": 6, "duration_days": 2},
            ],
            "Pushkar": [
                {"month": 11, "event": "Pushkar Camel Fair", "crowd_level": 10, "duration_days": 7},
            ],
        }

        self.NATIONAL_EVENTS = [
            {"month": 1, "event": "Republic Day", "crowd_level": 5, "duration_days": 1},
            {"month": 8, "event": "Independence Day", "crowd_level": 5, "duration_days": 1},
            {"month": 10, "event": "Gandhi Jayanti", "crowd_level": 4, "duration_days": 1},
        ]

    def get_crowd_intel(self, destination):
        """
        Analyzes crowd levels and seasonality.
        """
        current_month = datetime.now().month
        
        # 1. Check Hardcoded Data
        score_data = self._get_crowd_density_score(destination, current_month)
        
        # 2. If no hardcoded data found AND we have an LLM client, query dynamic intel
        if score_data["score"] == 3 and score_data["reason"] == "Normal tourist season" and self.client:
             dynamic_intel = self._get_dynamic_crowd_intel(destination, current_month)
             if dynamic_intel:
                 score_data = dynamic_intel
        
        # 3. Generate warnings/alternatives based on the final score
        warnings = self._generate_warnings_from_score(score_data)
        alternatives = self._suggest_crowd_alternatives(destination)
        
        return {
            "crowd_score": score_data.get("score", 5),
            "crowd_level": score_data.get("level", "Moderate"),
            "warnings": warnings,
            "alternatives": alternatives
        }

    def _get_dynamic_crowd_intel(self, destination, month):
        """
        Uses LLM to estimate crowd levels for destinations not in the database.
        """
        try:
            month_name = datetime(2024, month, 1).strftime('%B')
            prompt = f"""
            Estimate the crowd level for travellers in {destination} during {month_name}.
            
            Return JSON ONLY:
            {{
                "score": (1-10 integer, 1=Empty, 10=Packed),
                "level": (Low/Moderate/High/Extreme),
                "reason": (Brief explanation, e.g. "Peak ski season" or "Off-season due to monsoon")
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception:
            return None

    def _get_events_for_destination(self, destination, month=None):
        if month is None:
            month = datetime.now().month
        
        events = []
        
        # Check destination-specific events
        dest_key = None
        for key in self.SEASONAL_EVENTS.keys():
            if key.lower() in destination.lower():
                dest_key = key
                break
        
        if dest_key:
            for event in self.SEASONAL_EVENTS[dest_key]:
                if event["month"] == month:
                    events.append(event)
        
        # Add national events
        for event in self.NATIONAL_EVENTS:
            if event["month"] == month:
                events.append(event)
        
        return events

    def _get_crowd_density_score(self, destination, month=None):
        events = self._get_events_for_destination(destination, month)
        
        if not events:
            return {
                "score": 3,
                "level": "Low",
                "reason": "Normal tourist season",
                "events": []
            }
        
        max_crowd = max([e["crowd_level"] for e in events])
        event_names = [e["event"] for e in events]
        level = "Extreme" if max_crowd >= 9 else "High" if max_crowd >= 7 else "Moderate" if max_crowd >= 4 else "Low"
        
        return {
            "score": max_crowd,
            "level": level,
            "reason": f"High traffic due to {', '.join(event_names)}",
            "events": events
        }
        
    def _generate_warnings_from_score(self, crowd_data):
        warnings = []
        if crowd_data["score"] >= 8:
            warnings.append(f"🚨 Extreme crowds expected: {crowd_data.get('reason', '')}")
            warnings.append("⚠️ Book accommodations well in advance")
        elif crowd_data["score"] >= 6:
            warnings.append(f"👥 High tourist activity: {crowd_data.get('reason', '')}")
            warnings.append("💡 Popular spots may have long queues")
        return warnings

    def _get_crowd_warnings(self, destination, month=None):
        # Legacy wrapper if needed, but we use _generate_warnings_from_score now inside get_crowd_intel
        crowd_data = self._get_crowd_density_score(destination, month)
        return self._generate_warnings_from_score(crowd_data)

    def _suggest_crowd_alternatives(self, destination, activity_type="quiet"):
        alternatives = []
        
        # Destination-specific alternatives
        if "varanasi" in destination.lower():
            if activity_type == "quiet":
                alternatives = [
                    "Early morning boat ride (5-6 AM) before crowds arrive",
                    "Visit Sarnath instead of main ghats",
                    "Explore quieter ghats like Assi Ghat"
                ]
        elif "goa" in destination.lower():
            if activity_type == "quiet":
                alternatives = [
                    "Visit South Goa beaches (Palolem, Agonda) instead of North",
                    "Explore Old Goa churches in early morning",
                    "Try Divar Island for peaceful village experience"
                ]
        
        # Generic alternatives
        if not alternatives:
            alternatives = [
                "Visit attractions during early morning hours",
                "Opt for lesser-known similar spots nearby",
                "Plan indoor activities during peak crowd times"
            ]
        
        return alternatives
