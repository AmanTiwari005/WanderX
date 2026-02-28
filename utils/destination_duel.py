"""
🆚 Destination Duel — Compare two cities side-by-side with AI scoring.
"""
import json
import logging
from utils.web_search import search_web

logger = logging.getLogger("wanderx.destination_duel")


def run_duel(client, city_a, city_b, profile=None):
    """
    Compares two destinations across multiple dimensions using web search + LLM.
    
    Returns:
        dict: {
            "city_a": { "name": str, "scores": {...}, "highlights": [...] },
            "city_b": { "name": str, "scores": {...}, "highlights": [...] },
            "winner": str,
            "verdict": str,
            "categories": [ { "name": str, "winner": str, "reason": str } ]
        }
    """
    try:
        # Gather web intelligence for both cities
        search_a = search_web(f"travel {city_a} highlights cost safety 2025", max_results=5)
        search_b = search_web(f"travel {city_b} highlights cost safety 2025", max_results=5)

        budget = profile.get("budget", "Mid-Range") if profile else "Mid-Range"
        interests = profile.get("interests", "general sightseeing") if profile else "general sightseeing"

        prompt = f"""
You are a travel comparison expert. Compare these two destinations for a traveler.

CITY A: {city_a}
Web Intel: {json.dumps(search_a[:3])}

CITY B: {city_b}
Web Intel: {json.dumps(search_b[:3])}

Traveler Budget: {budget}
Traveler Interests: {interests}

Score each city 1-10 on these categories, then pick a winner per category and overall.

Return ONLY valid JSON:
{{
    "city_a": {{
        "name": "{city_a}",
        "scores": {{ "weather": 8, "cost": 7, "safety": 9, "food": 8, "culture": 7, "instagrammability": 8 }},
        "highlights": ["highlight 1", "highlight 2", "highlight 3"],
        "vibe": "One-sentence vibe description"
    }},
    "city_b": {{
        "name": "{city_b}",
        "scores": {{ "weather": 7, "cost": 8, "safety": 8, "food": 9, "culture": 8, "instagrammability": 7 }},
        "highlights": ["highlight 1", "highlight 2", "highlight 3"],
        "vibe": "One-sentence vibe description"
    }},
    "categories": [
        {{ "name": "Weather", "icon": "☀️", "winner": "{city_a}", "reason": "Brief reason" }},
        {{ "name": "Cost", "icon": "💰", "winner": "{city_b}", "reason": "Brief reason" }},
        {{ "name": "Safety", "icon": "🛡️", "winner": "{city_a}", "reason": "Brief reason" }},
        {{ "name": "Food", "icon": "🍜", "winner": "{city_b}", "reason": "Brief reason" }},
        {{ "name": "Culture", "icon": "🎭", "winner": "{city_a}", "reason": "Brief reason" }},
        {{ "name": "Instagrammability", "icon": "📸", "winner": "{city_b}", "reason": "Brief reason" }}
    ],
    "winner": "{city_a}",
    "verdict": "A fun, engaging 2-sentence summary of why the winner wins overall."
}}
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Destination Duel Error: {e}")
        return {"error": str(e)}


def render_duel_html(duel_data):
    """Renders the duel comparison as styled HTML cards."""
    if not duel_data or duel_data.get("error"):
        return "<div style='color:#ef4444;'>Duel failed. Try again?</div>"

    a = duel_data["city_a"]
    b = duel_data["city_b"]
    winner = duel_data.get("winner", "")
    verdict = duel_data.get("verdict", "")
    categories = duel_data.get("categories", [])

    # Score bars
    cat_rows = ""
    for cat in categories:
        name = cat.get("name", "")
        icon = cat.get("icon", "⚡")
        cat_winner = cat.get("winner", "")
        reason = cat.get("reason", "")

        a_score = a.get("scores", {}).get(name.lower().replace(" ", ""), 5)
        b_score = b.get("scores", {}).get(name.lower().replace(" ", ""), 5)

        a_bar_color = "#00f2fe" if cat_winner == a["name"] else "rgba(255,255,255,0.1)"
        b_bar_color = "#f43f5e" if cat_winner == b["name"] else "rgba(255,255,255,0.1)"

        cat_rows += f"""
        <div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <span style="font-size:0.8rem;color:#94a3b8;">{a_score}/10</span>
                <span style="font-weight:600;color:#e2e8f0;font-size:0.85rem;">{icon} {name}</span>
                <span style="font-size:0.8rem;color:#94a3b8;">{b_score}/10</span>
            </div>
            <div style="display:flex;gap:4px;height:8px;">
                <div style="flex:1;display:flex;justify-content:flex-end;">
                    <div style="width:{a_score*10}%;background:{a_bar_color};border-radius:4px;transition:width 0.8s;"></div>
                </div>
                <div style="flex:1;">
                    <div style="width:{b_score*10}%;background:{b_bar_color};border-radius:4px;transition:width 0.8s;"></div>
                </div>
            </div>
            <div style="text-align:center;font-size:0.7rem;color:#64748b;margin-top:2px;">{reason}</div>
        </div>
        """

    # Highlights
    a_highlights = "".join([f"<div style='font-size:0.8rem;color:#cbd5e1;padding:3px 0;'>✦ {h}</div>" for h in a.get("highlights", [])])
    b_highlights = "".join([f"<div style='font-size:0.8rem;color:#cbd5e1;padding:3px 0;'>✦ {h}</div>" for h in b.get("highlights", [])])

    a_crown = "👑 " if winner == a["name"] else ""
    b_crown = "👑 " if winner == b["name"] else ""

    return f"""
    <div style="background:rgba(15,23,42,0.9);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin:16px 0;">
        <div style="text-align:center;font-size:1.5rem;font-weight:800;color:#f8fafc;margin-bottom:4px;">🆚 DESTINATION DUEL</div>
        <div style="text-align:center;font-size:0.85rem;color:#64748b;margin-bottom:20px;">Who wins your heart?</div>
        
        <div style="display:flex;gap:20px;margin-bottom:20px;">
            <div style="flex:1;text-align:center;padding:16px;background:rgba(0,242,254,0.05);border:1px solid rgba(0,242,254,0.15);border-radius:12px;">
                <div style="font-size:1.3rem;font-weight:700;color:#00f2fe;">{a_crown}{a['name']}</div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;font-style:italic;">{a.get('vibe','')}</div>
                <div style="margin-top:10px;">{a_highlights}</div>
            </div>
            <div style="flex:1;text-align:center;padding:16px;background:rgba(244,63,94,0.05);border:1px solid rgba(244,63,94,0.15);border-radius:12px;">
                <div style="font-size:1.3rem;font-weight:700;color:#f43f5e;">{b_crown}{b['name']}</div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;font-style:italic;">{b.get('vibe','')}</div>
                <div style="margin-top:10px;">{b_highlights}</div>
            </div>
        </div>
        
        {cat_rows}
        
        <div style="margin-top:16px;padding:12px;background:rgba(250,204,21,0.08);border:1px solid rgba(250,204,21,0.2);border-radius:10px;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#facc15;">🏆 Winner: {winner}</div>
            <div style="font-size:0.8rem;color:#e2e8f0;margin-top:4px;">{verdict}</div>
        </div>
    </div>
    """
