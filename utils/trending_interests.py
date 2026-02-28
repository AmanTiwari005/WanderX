from utils.model_registry import get_active_model_id
import os
import json
from groq import Groq

def get_trending_interests(destination):
    """
    Fetches trending travel interests for a specific destination using LLM, categorized.
    Returns a dict: {'Culture': [], 'Adventure': [], 'Food': [], 'Relaxation': []}
    """
    if not destination:
        return {}
        
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    Return a valid JSON object with 6 distinct categories of travel interests for {destination}.
    Categories should be specific to the location (e.g., "Anime" for Tokyo, "Jazz" for New Orleans) 
    in addition to standard ones like "Food", "Culture".
    
    Each category should have a list of 4 short, specific interest tags (max 3 words).
    
    Example Structure:
    {{
        "Local Culture": ["Ancient Temples", "Art Galleries", "Tea Ceremony", "Calligraphy"],
        "Adventure": ["River Rafting", "Jungle Trek", "Bungee Jumping", "Kayaking"],
        "Food Scene": ["Street Food Tour", "Seafood Market", "Fine Dining", "Cooking Class"],
        "Relaxation": ["Beach Yoga", "Luxury Spa", "Onsen", "Meditation"],
        "Nightlife": ["Rooftop Bars", "Jazz Clubs", "Night Markets", "Techno Clubs"],
        "Shopping": ["Vintage Shops", "Luxury Malls", "Local Crafts", "Souvenirs"]
    }}
    
    JSON ONLY. No markdown.
    """
    
    try:
        res = client.chat.completions.create(
            model=get_active_model_id(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        ).choices[0].message.content
        
        # Clean potential markdown
        clean_res = res.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        if clean_res.startswith("```"):
            clean_res = clean_res[3:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
            
        data = json.loads(clean_res)
        if isinstance(data, dict):
            # Ensure we have at least some data, otherwise fallback
            return data
        return {}
    except:
        return {}
