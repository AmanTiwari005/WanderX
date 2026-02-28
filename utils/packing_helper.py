from utils.model_registry import get_active_model_id

import os
import json
from groq import Groq

def generate_packing_list(destination, weather_summary, duration, gender="Neutral", interests=None):
    """
    Generates a smart packing list based on destination context.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    Generate a smart, categorized packing list for a trip to {destination}.
    
    Context:
    - Duration: {duration} days
    - Weather: {weather_summary}
    - Traveler: {gender}
    - Interests/Activities: {interests}
    
    Return a VALID JSON object with the following categories:
    - "Essentials" (Documents, Money, etc.)
    - "Clothing" (Weather-appropriate)
    - "Toiletries"
    - "Electronics"
    - "Specialized" (Based on interests, e.g., Hiking gear, Swimwear)
    
    Format:
    {{
      "Essentials": ["Item 1", "Item 2"],
      "Clothing": ["Item 1", "Item 2"],
      ...
    }}
    
    Keep it concise and practical.
    """
    
    try:
        res = client.chat.completions.create(
            model=get_active_model_id(),
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"Packing List Error: {e}")
        return None
