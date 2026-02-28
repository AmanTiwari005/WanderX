"""
Context-aware quick action generator.
Generates always-visible action chips based on current context.
"""

import datetime


def generate_quick_actions(destination=None, context=None, profile=None):
    """
    Generate context-aware quick action chips.
    
    Args:
        destination: Current destination
        context: Dict with weather, time, risk info
        profile: User profile data
        
    Returns:
        List of action strings (max 6)
    """
    actions = []
    
    # Always include core actions
    baseline = [
        "📅 Give me a full itinerary",
        "🏨 Find hotels nearby",
        "🍽️ Best restaurants",
        "🎯 Top attractions"
    ]
    
    if not destination:
        return baseline
    
    # Context-aware additions
    context = context or {}
    
    # Time-based actions
    current_hour = datetime.datetime.now().hour
    if 6 <= current_hour < 11:
        actions.append("☕ Breakfast spots nearby")
    elif 11 <= current_hour < 14:
        actions.append("🍴 Lunch recommendations")
    elif 18 <= current_hour < 22:
        actions.append("🌆 Evening activities")
    elif 22 <= current_hour or current_hour < 6:
        actions.append("🌙 Late night options")
    
    # Weather-based actions
    weather = (context.get("weather") or "").lower()
    if "rain" in weather or "storm" in weather:
        actions.append("🏛️ Indoor activities")
    elif "sunny" in weather or "clear" in weather:
        actions.append("🌳 Outdoor adventures")
    
    # Risk-based actions
    risk_level = (context.get("risk") or "").lower()
    if "critical" in risk_level or "unsafe" in risk_level:
        actions.append("🛡️ Safety tips")
        actions.append("📞 Emergency contacts")
    
    # Budget-aware
    if profile and profile.get("budget"):
        actions.append("💰 Budget breakdown")
    
    # Location services
    actions.extend([
        "📍 Navigate to destination",
        "🚖 Book transport",
        "🏧 Find ATMs nearby"
    ])
    
    # Combine and limit to 6 actions
    # Priority: baseline first, then context-aware
    final_actions = baseline[:4]  # Keep top 4 baseline
    
    # Add unique context actions
    for action in actions:
        if action not in final_actions and len(final_actions) < 6:
            final_actions.append(action)
    
    return final_actions[:6]


def get_contextual_icon(time_of_day=None, weather=None):
    """
    Get appropriate icon based on context.
    
    Args:
        time_of_day: "morning", "afternoon", "evening", "night"
        weather: Weather condition string
        
    Returns:
        Emoji icon
    """
    if weather:
        weather = weather.lower()
        if "rain" in weather:
            return "🌧️"
        elif "sun" in weather or "clear" in weather:
            return "☀️"
        elif "cloud" in weather:
            return "☁️"
        elif "snow" in weather:
            return "❄️"
    
    if time_of_day:
        time_map = {
            "morning": "🌅",
            "afternoon": "☀️",
            "evening": "🌆",
            "night": "🌙"
        }
        return time_map.get(time_of_day, "🕐")
    
    return "📌"
