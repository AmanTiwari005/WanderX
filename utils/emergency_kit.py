"""
🆘 Emergency Kit — One-tap access to embassy, emergency numbers, hospital, key phrases.
"""
import json
import logging

logger = logging.getLogger("wanderx.emergency_kit")


def get_emergency_info(client, destination, origin_country="India"):
    """
    Generates comprehensive emergency information for a destination.
    """
    try:
        prompt = f"""
You are a travel safety expert. Generate emergency information for a traveler from {origin_country} visiting {destination}.

Return ONLY valid JSON:
{{
    "emergency_numbers": {{
        "police": "Number",
        "ambulance": "Number",
        "fire": "Number",
        "tourist_helpline": "Number (if exists)"
    }},
    "embassy": {{
        "name": "{origin_country} Embassy/Consulate in {destination}",
        "address": "Full address",
        "phone": "Phone number",
        "email": "Email if known"
    }},
    "nearest_hospitals": [
        {{ "name": "Hospital Name", "type": "Public/Private", "specialty": "General/Trauma", "area": "Location area" }}
    ],
    "emergency_phrases": [
        {{ "english": "Help!", "local": "Local translation", "pronunciation": "Phonetic guide" }},
        {{ "english": "I need a doctor", "local": "Translation", "pronunciation": "Phonetic" }},
        {{ "english": "Where is the hospital?", "local": "Translation", "pronunciation": "Phonetic" }},
        {{ "english": "Call the police", "local": "Translation", "pronunciation": "Phonetic" }},
        {{ "english": "I'm lost", "local": "Translation", "pronunciation": "Phonetic" }}
    ],
    "safety_tips": [
        "Tip 1 specific to {destination}",
        "Tip 2",
        "Tip 3"
    ],
    "insurance_reminder": "Brief reminder about travel insurance"
}}

Be accurate with real numbers and addresses. Include 2-3 hospitals.
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Emergency Kit Error: {e}")
        return {"error": str(e)}


def render_emergency_html(data):
    """Renders emergency info as compact styled HTML."""
    if not data or data.get("error"):
        return ""
    
    nums = data.get("emergency_numbers", {})
    nums_html = "".join([
        f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);'>"
        f"<span style='color:#94a3b8;font-size:0.8rem;'>{k.replace('_',' ').title()}</span>"
        f"<span style='color:#f43f5e;font-weight:700;font-size:0.9rem;'>{v}</span></div>"
        for k, v in nums.items() if v
    ])

    embassy = data.get("embassy", {})
    embassy_html = f"""<div style="margin-top:8px;font-size:0.8rem;color:#cbd5e1;">
        <div style="font-weight:600;color:#facc15;">🏛️ {embassy.get('name','Embassy')}</div>
        <div>📍 {embassy.get('address','')}</div>
        <div>📞 {embassy.get('phone','')}</div>
    </div>""" if embassy.get("name") else ""

    phrases = data.get("emergency_phrases", [])
    phrases_html = "".join([
        f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:0.78rem;'>"
        f"<span style='color:#94a3b8;'>{p.get('english','')}</span>"
        f"<span style='color:#22d3ee;font-weight:600;'>{p.get('local','')} <span style='color:#64748b;font-size:0.7rem;'>({p.get('pronunciation','')})</span></span></div>"
        for p in phrases
    ])

    tips = data.get("safety_tips", [])
    tips_html = "".join([f"<div style='font-size:0.78rem;color:#cbd5e1;padding:3px 0;'>⚠️ {t}</div>" for t in tips])

    return f"""<div style="background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.2);border-radius:12px;padding:16px;">
    <div style="font-size:1.1rem;font-weight:700;color:#ef4444;margin-bottom:12px;">🆘 Emergency Kit</div>
    <div style="margin-bottom:12px;">{nums_html}</div>
    {embassy_html}
    <div style="margin-top:12px;">
        <div style="font-weight:600;color:#e2e8f0;font-size:0.85rem;margin-bottom:6px;">🗣️ Emergency Phrases</div>
        {phrases_html}
    </div>
    <div style="margin-top:12px;">
        <div style="font-weight:600;color:#e2e8f0;font-size:0.85rem;margin-bottom:6px;">🛡️ Safety Tips</div>
        {tips_html}
    </div>
</div>"""
