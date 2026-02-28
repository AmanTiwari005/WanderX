"""
💱 Smart Currency Converter — Inline conversion with purchasing power context.
"""
import json
import re
import logging

logger = logging.getLogger("wanderx.currency_converter")

# Common currency symbols/codes
CURRENCY_PATTERNS = [
    (r'(?:how much is |convert |what\'?s )?([¥€£₹$₩₺฿₫₱])\s*([0-9,]+(?:\.\d+)?)', 'symbol'),
    (r'(?:how much is |convert |what\'?s )?([0-9,]+(?:\.\d+)?)\s*(USD|EUR|GBP|JPY|INR|CNY|KRW|THB|AUD|CAD|SGD|MYR|VND|PHP|IDR|BRL|MXN|TRY|AED|SAR)', 'code'),
    (r'([0-9,]+(?:\.\d+)?)\s*(?:dollars?|euros?|pounds?|yen|rupees?|won|baht)', 'word'),
]

SYMBOL_TO_CODE = {
    '¥': 'JPY', '€': 'EUR', '£': 'GBP', '₹': 'INR',
    '$': 'USD', '₩': 'KRW', '₺': 'TRY', '฿': 'THB',
    '₫': 'VND', '₱': 'PHP',
}

WORD_TO_CODE = {
    'dollar': 'USD', 'euro': 'EUR', 'pound': 'GBP', 'yen': 'JPY',
    'rupee': 'INR', 'won': 'KRW', 'baht': 'THB',
}


def detect_currency_query(text):
    """
    Detects if user message contains a currency conversion request.
    Returns (amount, currency_code) or None.
    """
    text_lower = text.lower().strip()
    
    for pattern, ptype in CURRENCY_PATTERNS:
        match = re.search(pattern, text_lower if ptype == 'word' else text, re.IGNORECASE)
        if match:
            if ptype == 'symbol':
                symbol, amount = match.group(1), match.group(2)
                code = SYMBOL_TO_CODE.get(symbol, 'USD')
                return float(amount.replace(',', '')), code
            elif ptype == 'code':
                amount, code = match.group(1), match.group(2)
                return float(amount.replace(',', '')), code.upper()
            elif ptype == 'word':
                amount = match.group(1)
                word = re.search(r'(dollars?|euros?|pounds?|yen|rupees?|won|baht)', text_lower)
                if word:
                    code = WORD_TO_CODE.get(word.group(1).rstrip('s'), 'USD')
                    return float(amount.replace(',', '')), code
    
    return None


def convert_with_context(client, amount, from_currency, destination):
    """
    Converts currency and provides purchasing power context.
    """
    try:
        prompt = f"""
A traveler asks about {amount} {from_currency} in the context of traveling to {destination}.

Provide a helpful conversion with purchasing power context. 
CRITICAL REQUIREMENT: You MUST convert the amount to Indian Rupees (INR) regardless of the destination country. 

Return ONLY valid JSON:
{{
    "from_amount": {amount},
    "from_currency": "{from_currency}",
    "to_amount": 0.0,
    "to_currency": "INR",
    "to_currency_name": "Indian Rupee",
    "exchange_rate": 0.0,
    "purchasing_power": "What this amount (in INR) buys in {destination} (be specific — meals, taxi rides, etc.)",
    "fun_fact": "A fun purchasing power comparison",
    "tip": "A practical money tip for travelers in {destination} regarding INR conversion or local costs"
}}
"""
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Currency Converter Error: {e}")
        return {"error": str(e)}


def render_currency_card(data):
    """Renders currency conversion as a styled inline card."""
    if not data or data.get("error"):
        return ""

    return f"""
    <div style="background:linear-gradient(135deg, rgba(34,211,238,0.08), rgba(168,85,247,0.08));
                border:1px solid rgba(34,211,238,0.2);border-radius:14px;padding:16px;margin:8px 0;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
            <span style="font-size:1.8rem;">💱</span>
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#22d3ee;">
                    {data.get('from_amount',0):,.2f} {data.get('from_currency','')} = {data.get('to_amount',0):,.2f} {data.get('to_currency','')}
                </div>
                <div style="font-size:0.75rem;color:#64748b;">
                    1 {data.get('from_currency','')} ≈ {data.get('exchange_rate',0)} {data.get('to_currency','')} ({data.get('to_currency_name','')})
                </div>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:10px;margin-bottom:8px;">
            <div style="font-size:0.78rem;color:#a78bfa;font-weight:600;margin-bottom:2px;">🛒 What it buys:</div>
            <div style="font-size:0.82rem;color:#e2e8f0;">{data.get('purchasing_power','')}</div>
        </div>
        <div style="display:flex;gap:8px;">
            <div style="flex:1;font-size:0.72rem;color:#94a3b8;padding:6px;background:rgba(255,255,255,0.03);border-radius:8px;">
                💡 {data.get('tip','')}
            </div>
        </div>
    </div>
    """
