"""
📊 Trip DNA Report — Personality analysis based on itinerary choices.
"""
import json
import logging
import textwrap

logger = logging.getLogger("wanderx.trip_dna")

ARCHETYPES = {
    "Explorer": {"icon": "🧭", "color": "#3b82f6"},
    "Foodie": {"icon": "🍜", "color": "#ef4444"},
    "Culture Seeker": {"icon": "🎭", "color": "#a855f7"},
    "Relaxer": {"icon": "🧘", "color": "#22c55e"},
    "Adventurer": {"icon": "⛰️", "color": "#f97316"},
    "Night Owl": {"icon": "🦉", "color": "#6366f1"},
    "Shopaholic": {"icon": "🛍️", "color": "#ec4899"},
    "Nature Lover": {"icon": "🌿", "color": "#10b981"},
}


def generate_trip_dna(client, profile, itinerary):
    """
    Analyzes itinerary choices to generate a traveler personality breakdown.
    """
    try:
        prompt = f"""
Analyze this traveler's profile and itinerary to determine their travel personality.

Profile: {json.dumps(profile)}
Itinerary: {json.dumps(itinerary) if itinerary else "No itinerary yet"}

Categorize them into these archetypes with percentage weights (must sum to 100):
Explorer, Foodie, Culture Seeker, Relaxer, Adventurer, Night Owl, Shopaholic, Nature Lover

Return ONLY valid JSON:
{{
    "archetypes": [
        {{ "name": "Explorer", "percentage": 35, "reason": "Why this percentage" }},
        {{ "name": "Foodie", "percentage": 25, "reason": "Why" }}
    ],
    "dominant_type": "Explorer",
    "travel_spirit_animal": "An animal that matches their style",
    "tagline": "A fun, personalized one-liner about their travel style",
    "recommendation": "A destination they'd love based on this DNA"
}}

Only include archetypes with >= 5%. Order by percentage descending.
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Trip DNA Error: {e}")
        return {"error": str(e)}


def render_trip_dna_html(dna_data):
    """Renders Trip DNA as a styled card with arc bars."""
    if not dna_data or dna_data.get("error"):
        return ""
    
    archetypes = dna_data.get("archetypes", [])
    dominant = dna_data.get("dominant_type", "Explorer")
    tagline = dna_data.get("tagline", "")
    spirit = dna_data.get("travel_spirit_animal", "")
    rec = dna_data.get("recommendation", "")

    bars_html = ""
    for arch in archetypes:
        name = arch.get("name", "")
        pct = arch.get("percentage", 0)
        meta = ARCHETYPES.get(name, {"icon": "✦", "color": "#94a3b8"})
        
        # Construct bar HTML with NO indentation to avoid markdown code block triggering
        bars_html += f"""
<div style="margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;margin-bottom:3px;">
<span style="font-size:0.82rem;color:#e2e8f0;">{meta['icon']} {name}</span>
<span style="font-size:0.82rem;font-weight:700;color:{meta['color']};">{pct}%</span>
</div>
<div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
<div style="height:100%;width:{pct}%;background:{meta['color']};border-radius:4px;transition:width 1s ease;"></div>
</div>
<div style="font-size:0.68rem;color:#64748b;margin-top:2px;">{arch.get('reason','')}</div>
</div>"""

    dom_meta = ARCHETYPES.get(dominant, {"icon": "✦", "color": "#00f2fe"})

    # Final HTML assembly - ensure flush left
    return f"""
<div style="background:linear-gradient(145deg,rgba(15,23,42,0.95),rgba(30,41,59,0.8)); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:24px; margin:12px 0;">
<div style="text-align:center;margin-bottom:16px;">
<div style="font-size:2rem;">{dom_meta['icon']}</div>
<div style="font-size:1.3rem;font-weight:800;color:{dom_meta['color']};">You're a {dominant}!</div>
<div style="font-size:0.85rem;color:#94a3b8;font-style:italic;margin-top:4px;">"{tagline}"</div>
<div style="font-size:0.78rem;color:#64748b;margin-top:4px;">🐾 Spirit Animal: {spirit}</div>
</div>
{bars_html}
<div style="margin-top:14px;padding:10px;background:rgba(0,242,254,0.06);border-radius:10px;text-align:center;">
<div style="font-size:0.75rem;color:#64748b;">✨ You'd love:</div>
<div style="font-size:0.9rem;font-weight:600;color:#22d3ee;">{rec}</div>
</div>
</div>
"""
