import json
import os
from datetime import datetime

FEEDBACK_FILE = "data/feedback.json"

def log_feedback(suggestion, destination, feedback_type, context=None):
    """
    Log user feedback to JSON file.
    
    Args:
        suggestion: The suggestion text that was rated
        destination: Travel destination
        feedback_type: "positive" or "negative"
        context: Optional dict with additional context (category, weather, etc.)
    """
    os.makedirs("data", exist_ok=True)
    
    # Load existing feedback
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {"feedback": []}
    else:
        data = {"feedback": []}
    
    # Append new feedback
    data["feedback"].append({
        "timestamp": datetime.now().isoformat(),
        "suggestion": suggestion,
        "destination": destination,
        "feedback_type": feedback_type,
        "context": context or {}
    })
    
    # Save
    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_feedback_stats(destination=None):
    """
    Get aggregated feedback statistics.
    
    Args:
        destination: Optional filter by destination
    
    Returns:
        dict: {"total": int, "positive": int, "negative": int, "ratio": float}
    """
    if not os.path.exists(FEEDBACK_FILE):
        return {"total": 0, "positive": 0, "negative": 0, "ratio": 0.0}
    
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return {"total": 0, "positive": 0, "negative": 0, "ratio": 0.0}
    
    feedback_list = data.get("feedback", [])
    
    if destination:
        feedback_list = [f for f in feedback_list if f.get("destination") == destination]
    
    total = len(feedback_list)
    positive = sum(1 for f in feedback_list if f.get("feedback_type") == "positive")
    negative = sum(1 for f in feedback_list if f.get("feedback_type") == "negative")
    
    ratio = positive / total if total > 0 else 0.0
    
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "ratio": round(ratio, 2)
    }


def get_disliked_suggestions(destination=None):
    """
    Get a list of suggestions that the user has disliked for a destination.
    Used by suggestion_generator to avoid repeating bad suggestions.
    
    Args:
        destination: Optional filter by destination
        
    Returns:
        list[str]: List of disliked suggestion texts
    """
    if not os.path.exists(FEEDBACK_FILE):
        return []
    
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    
    feedback_list = data.get("feedback", [])
    
    disliked = []
    for f_entry in feedback_list:
        if f_entry.get("feedback_type") == "negative":
            if destination is None or f_entry.get("destination") == destination:
                suggestion = f_entry.get("suggestion", "")
                if suggestion and suggestion not in disliked:
                    disliked.append(suggestion)
    
    return disliked
