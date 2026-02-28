"""
🏆 Travel Achievements — Unlock badges based on trip planning behavior.
"""
import logging

logger = logging.getLogger("wanderx.achievements")

BADGE_DEFINITIONS = [
    {
        "id": "globe_trotter",
        "name": "Globe Trotter",
        "icon": "🌍",
        "description": "Planned trips to 3+ different countries",
        "color": "#3b82f6",
    },
    {
        "id": "budget_boss",
        "name": "Budget Boss",
        "icon": "💰",
        "description": "Planned a trip on a Budget tier",
        "color": "#22c55e",
    },
    {
        "id": "luxury_liner",
        "name": "Luxury Liner",
        "icon": "👑",
        "description": "Planned a Luxury-tier trip",
        "color": "#f59e0b",
    },
    {
        "id": "culture_vulture",
        "name": "Culture Vulture",
        "icon": "🎭",
        "description": "Interests include museums, history, or art",
        "color": "#a855f7",
    },
    {
        "id": "foodie_explorer",
        "name": "Foodie Explorer",
        "icon": "🍜",
        "description": "Interests include food, restaurants, or street food",
        "color": "#ef4444",
    },
    {
        "id": "night_owl",
        "name": "Night Owl",
        "icon": "🦉",
        "description": "Planned evening activities in your itinerary",
        "color": "#6366f1",
    },
    {
        "id": "eco_warrior",
        "name": "Eco Warrior",
        "icon": "🌿",
        "description": "Checked sustainability intel for your trip",
        "color": "#10b981",
    },
    {
        "id": "marathon_planner",
        "name": "Marathon Planner",
        "icon": "🏃",
        "description": "Planned a trip longer than 7 days",
        "color": "#f97316",
    },
    {
        "id": "speed_demon",
        "name": "Speed Demon",
        "icon": "⚡",
        "description": "Set your pace to Fast",
        "color": "#eab308",
    },
    {
        "id": "solo_adventurer",
        "name": "Solo Adventurer",
        "icon": "🧭",
        "description": "Planning a solo trip",
        "color": "#06b6d4",
    },
]


def check_achievements(profile, itinerary=None, session_state=None):
    """
    Scans profile + itinerary for achievement trigger conditions.
    Returns list of earned badge dicts.
    """
    earned = []
    
    budget = (profile.get("budget") or "").lower()
    interests = (profile.get("interests") or "").lower()
    pace = (profile.get("pace") or "").lower()
    group = (profile.get("group_type") or "").lower()
    duration = 0
    try:
        duration = int(str(profile.get("duration", 0)).split()[0])
    except:
        pass

    # Budget Boss
    if budget in ["budget", "cheap", "low"]:
        earned.append("budget_boss")

    # Luxury Liner
    if budget in ["luxury", "premium", "high"]:
        earned.append("luxury_liner")

    # Culture Vulture
    if any(k in interests for k in ["museum", "history", "art", "culture", "heritage"]):
        earned.append("culture_vulture")

    # Foodie Explorer
    if any(k in interests for k in ["food", "restaurant", "street food", "cuisine", "eat"]):
        earned.append("foodie_explorer")

    # Marathon Planner
    if duration >= 7:
        earned.append("marathon_planner")

    # Speed Demon
    if pace == "fast":
        earned.append("speed_demon")

    # Solo Adventurer
    if "solo" in group:
        earned.append("solo_adventurer")

    # Night Owl — check itinerary
    if itinerary and isinstance(itinerary, dict):
        for key, day in itinerary.items():
            if key.startswith("day_") and isinstance(day, dict):
                if day.get("evening"):
                    earned.append("night_owl")
                    break

    # Eco Warrior
    if session_state and session_state.get("latest_sustainability"):
        earned.append("eco_warrior")

    # Return full badge objects
    return [b for b in BADGE_DEFINITIONS if b["id"] in earned]


def render_badges_html(badges):
    """Renders earned badges as compact HTML."""
    if not badges:
        return ""
    
    badges_html = ""
    for b in badges:
        badges_html += f"""<div style="display:inline-flex;align-items:center;gap:4px;
                    background:rgba({_hex_to_rgb(b['color'])},0.12);
                    border:1px solid rgba({_hex_to_rgb(b['color'])},0.3);
                    border-radius:20px;padding:4px 10px;margin:3px;font-size:0.72rem;">
            <span style="font-size:1rem;">{b['icon']}</span>
            <span style="color:{b['color']};font-weight:600;">{b['name']}</span>
        </div>"""
    
    return f"""<div style="margin-top:8px;">
    <div style="font-size:0.75rem;color:#64748b;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;">🏆 Achievements ({len(badges)})</div>
    <div style="display:flex;flex-wrap:wrap;gap:2px;">{badges_html}</div>
</div>"""


def _hex_to_rgb(hex_color):
    """Convert hex to RGB string."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r},{g},{b}"
