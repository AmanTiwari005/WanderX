from utils.model_registry import get_active_model_id
import os
import json
import re
import logging
from groq import Groq
from utils.budget_parser import parse_budget
from utils.feedback_tracker import get_disliked_suggestions
import datetime

logger = logging.getLogger("wanderx.suggestions")

def extract_topics(conversation_history):
    """
    Extract key topics from recent conversation to avoid repetition.
    
    Args:
        conversation_history: List of message dicts with 'role' and 'content'
    
    Returns:
        str: Comma-separated list of topics
    """
    if not conversation_history:
        return ""
    
    topics = []
    keywords_map = {
        "hotel": ["hotel", "accommodation", "stay", "lodging"],
        "food": ["food", "restaurant", "dining", "eat", "cuisine"],
        "transport": ["transport", "taxi", "uber", "bus", "train", "flight"],
        "activities": ["activity", "activities", "things to do", "attractions"],
        "itinerary": ["itinerary", "plan", "schedule", "day trip"],
        "budget": ["budget", "cost", "price", "expensive", "cheap"]
    }
    
    for msg in conversation_history[-5:]:  # Last 5 messages
        if msg.get("role") == "user":
            content = str(msg.get("content", "")).lower()
            for topic, keywords in keywords_map.items():
                if any(kw in content for kw in keywords):
                    topics.append(topic)
    
    return ", ".join(set(topics))

def generate_dynamic_suggestions(destination, current_context=None, user_preferences=None, conversation_history=None):
    """
    Generates 4-5 short, context-aware, categorized interaction chips for the user.
    
    Args:
        destination: Travel destination
        current_context: Dict with weather, time, risk info
        user_preferences: Dict with budget, interests, etc.
        conversation_history: List of recent messages
    
    Returns:
        Dict[str, List[str]]: Categorized suggestions
        {
            "Food": ["Suggestion 1", "Suggestion 2"],
            "Culture": ["Suggestion 3"],
            "Logistics": ["Suggestion 4"],
            "Hidden Gems": ["Suggestion 5"]
        }
    """
    if not destination:
        return {
            "Surprise Me Options": [
                "Suggest unique destinations",
                "Find me a hidden beach getaway",
                "Plan a cultural city break",
                "Show me mountain retreats",
                "Give me a culinary tour idea",
                "Recommend an off-the-grid adventure"
            ]
        }

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Build context string
    ctx_str = f"Destination: {destination}"
    
    if current_context:
        if current_context.get("weather"):
            ctx_str += f"\nWeather: {current_context['weather']}"
        if current_context.get("time"):
            ctx_str += f"\nTime: {current_context['time']}"
        if current_context.get("risk"):
            ctx_str += f"\nRisk Level: {current_context['risk']}"
    
    # Budget tier
    budget_tier = "mid-range"
    if user_preferences and user_preferences.get("budget"):
        budget_tier = parse_budget(user_preferences["budget"])
        ctx_str += f"\nBudget Tier: {budget_tier}"
    
    # Conversation awareness
    recent_topics = ""
    if conversation_history:
        recent_topics = extract_topics(conversation_history)
        if recent_topics:
            ctx_str += f"\nUser already discussed: {recent_topics}"

    # Feedback loop: load disliked suggestions
    disliked = get_disliked_suggestions(destination)
    disliked_str = ", ".join(disliked[:10]) if disliked else "None"

    prompt = f"""
Generate 6 highly specific, location-aware interaction chips for a traveler in {destination}.

Context:
{ctx_str}

CRITICAL: Focus on {destination}-SPECIFIC suggestions. Use local knowledge, famous spots, and unique experiences.

Requirements:
1. Return VALID JSON ONLY in this exact format. You MUST use double quotes for all keys and string values. NO SINGLE QUOTES. NO MARKDOWN:
{{
  "Smart Tips": ["Tip 1", "Tip 2"],
  "Local Flavors": ["Dish 1", "Dish 2"],
  "Hidden Gems": ["Gem 1"]
}}

2. Categories & Content:
   - **Smart Tips**: Practical, insider advice for {destination} (e.g., "Use Suica card", "Book months ahead").
   - **Local Flavors**: Specific dish or restaurant (e.g., "Try Monjayaki at Tsukishima").
   - **Hidden Gems**: Off-beat spot (e.g., "Yanaka Ginza for cats").

3. Constraints:
   - Max 5-6 words per suggestion.
   - Action-oriented.
   - NO IMAGES needed.
   - AVOID generic advice.
   - AVOID topics discussed: {recent_topics}
   - AVOID disliked: {disliked_str}

4. Total 5 suggestions.
"""
    
    try:
        res = client.chat.completions.create(
            model=get_active_model_id(),
            messages=[
                {"role": "system", "content": "You are a JSON API. You MUST return strictly valid JSON. Do not include markdown or conversational text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5  # Slightly higher for more creative suggestions
        ).choices[0].message.content
        
        # Clean response
        clean_res = res.strip()
        
        # Remove <think> blocks if present
        clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
        
        # Try to find the start and end of the JSON object
        if "{" in clean_res and "}" in clean_res:
            s = clean_res.find("{")
            e = clean_res.rfind("}") + 1
            clean_res = clean_res[s:e]
            
        suggestions = json.loads(clean_res)
        
        # Ensure it's a dict with string keys
        if isinstance(suggestions, dict):
            # Filter out empty categories
            filtered = {k: v for k, v in suggestions.items() if v and isinstance(v, list)}
            return filtered if filtered else get_fallback_suggestions(destination, budget_tier)
        
        return get_fallback_suggestions(destination, budget_tier)
        
    except Exception as e:
        print(f"Suggestion Generation Error: {e}")
        return get_fallback_suggestions(destination, budget_tier)

def get_fallback_suggestions(destination, budget_tier="mid-range"):
    """Fallback suggestions when LLM fails"""
    return {
        "Food": [f"Best {budget_tier} dining in {destination}"],
        "Culture": [f"Top attractions in {destination}"],
        "Logistics": ["Find hotels nearby"],
        "Hidden Gems": ["Local recommendations"]
    }


def generate_alternative_plans(destination, context=None, profile=None, primary_suggestion=None):
    """
    Generate Plan A/B/C alternatives for a given context.
    
    Args:
        destination: Travel destination
        context: Current context (weather, time, risk)
        profile: User preferences
        primary_suggestion: The main recommendation (optional)
        
    Returns:
        Dict with plan_a, plan_b, plan_c, each containing:
        {
            "title": str,
            "description": str,
            "reasoning": str,
            "conditions": str  # When to use this plan
        }
    """
    if not destination:
        return None
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Build context
    ctx_str = f"Destination: {destination}"
    current_hour = datetime.datetime.now().hour
    time_of_day = "morning" if 6 <= current_hour < 12 else "afternoon" if 12 <= current_hour < 18 else "evening"
    
    ctx_str += f"\nTime: {time_of_day}"
    
    if context:
        if context.get("weather"):
            ctx_str += f"\nWeather: {context['weather']}"
        if context.get("risk"):
            ctx_str += f"\nRisk: {context['risk']}"
    
    budget = "mid-range"
    if profile and profile.get("budget"):
        budget = parse_budget(profile["budget"])
        ctx_str += f"\nBudget: {budget}"
    
    if profile and profile.get("interests"):
        ctx_str += f"\nInterests: {profile['interests']}"
    
    prompt = f"""
Generate 3 alternative activity plans for a traveler in {destination}.

Context:
{ctx_str}

Return ONLY valid JSON in this exact format:
{{
  "plan_a": {{
    "title": "Best primary option",
    "description": "1-2 sentence description",
    "reasoning": "Why this is the best choice now",
    "conditions": "Ideal for current conditions"
  }},
  "plan_b": {{
    "title": "Reliable backup",
    "description": "1-2 sentence description",
    "reasoning": "Why this is a good alternative",
    "conditions": "Good if Plan A is not feasible"
  }},
  "plan_c": {{
    "title": "Weather/condition adaptive",
    "description": "1-2 sentence description",
    "reasoning": "When to use this option",
    "conditions": "If weather changes or time runs out"
  }}
}}

Requirements:
- Plan A: Best option for current conditions (weather, time, etc.)
- Plan B: Indoor/safe alternative if conditions worsen
- Plan C: Low-effort or nearby option if tired/time-limited
- All must be SPECIFIC to {destination}
- Keep descriptions concise
- Match {budget} budget tier
"""
    
    try:
        res = client.chat.completions.create(
            model=get_active_model_id(),
            messages=[
                {"role": "system", "content": "You are a JSON API. You MUST return strictly valid JSON. Do not include markdown or conversational text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.6
        ).choices[0].message.content
        
        # Clean response
        clean_res = res.strip()
        clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
        
        if "{" in clean_res and "}" in clean_res:
            s = clean_res.find("{")
            e = clean_res.rfind("}") + 1
            clean_res = clean_res[s:e]
        
        plans = json.loads(clean_res)
        
        if isinstance(plans, dict) and "plan_a" in plans:
            return plans
        
        return get_fallback_plans(destination)
        
    except Exception as e:
        print(f"Plan Generation Error: {e}")
        return get_fallback_plans(destination)


def get_fallback_plans(destination):
    """Fallback plans when LLM fails"""
    return {
        "plan_a": {
            "title": f"Explore {destination} highlights",
            "description": "Visit top attractions and landmarks",
            "reasoning": "Classic sightseeing experience",
            "conditions": "Good weather and daylight"
        },
        "plan_b": {
            "title": "Indoor cultural experiences",
            "description": "Museums, galleries, and cultural centers",
            "reasoning": "Weather-independent activities",
            "conditions": "If weather is unfavorable"
        },
        "plan_c": {
            "title": "Local food tour",
            "description": "Explore local cuisine and markets",
            "reasoning": "Flexible, low-effort activity",
            "conditions": "When time or energy is limited"
        }
    }
