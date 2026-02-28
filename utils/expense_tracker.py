
import os
import json
from datetime import datetime
from groq import Groq

def parse_expense_text(text, client=None):
    """
    Parses unstructured expense text into structured data using LLM.
    Example: "Spent 50 bucks on dinner at Mario's" -> {amount: 50, currency: "USD", category: "Food", description: "Dinner at Mario's"}
    """
    if not client:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
    prompt = f"""
    Extract expense details from this text: "{text}"
    
    Return a VALID JSON object with:
    - "amount" (number)
    - "currency" (guess based on context or default to user's home currency symbol if implied, otherwise 'USD')
    - "category" (Food, Transport, Accommodation, Activity, Shopping, Misc)
    - "description" (short summary)
    
    If invalid or unclear, return null.
    """
    
    try:
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except:
        return None

def add_expense(profile, amount, category, description, currency="USD"):
    """
    Adds an expense to the trip profile.
    """
    if "expenses" not in profile:
        profile["expenses"] = []
        
    expense = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "amount": amount,
        "category": category,
        "description": description,
        "currency": currency,
        "date": datetime.now().isoformat()
    }
    profile["expenses"].append(expense)
    return expense

def get_budget_status(profile):
    """
    Calculates total spent vs budget.
    """
    # Simple parsing of budget string like "INR 50,000"
    budget_str = profile.get("budget", "0")
    try:
        # Extract numbers only
        budget_limit = float("".join(filter(str.isdigit, budget_str)))
    except:
        budget_limit = 0
        
    total_spent = sum(e["amount"] for e in profile.get("expenses", []))
    
    return {
        "total_spent": total_spent,
        "budget_limit": budget_limit,
        "remaining": budget_limit - total_spent,
        "percent_used": (total_spent / budget_limit * 100) if budget_limit > 0 else 0
    }
