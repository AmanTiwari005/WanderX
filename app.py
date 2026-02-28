import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from dotenv import load_dotenv
import os
import json
import logging
import asyncio
import re
import textwrap
from utils.model_registry import get_active_model_id, get_active_model_info, AVAILABLE_MODELS, get_model_display_options
from streamlit_option_menu import option_menu
import streamlit_antd_components as sac

from streamlit_lottie import st_lottie
from utils.geocode import geocode_location
from utils.quick_actions import generate_quick_actions
from utils.suggestion_generator import generate_alternative_plans

from utils.nearby_places import get_nearby_places
from agents.context_agent import ContextAgent
from agents.recommendation_agent import RecommendationAgent
from engines.decision_engine import DecisionEngine

from utils.map_viewer import create_destination_map, create_route_map, create_itinerary_map, render_map_in_streamlit
from utils.pdf_generator import generate_itinerary_pdf
from utils.ui_components import get_custom_css, render_travel_card, render_timeline, render_smart_suggestion_carousel, render_day_timeline, render_smart_suggestion_sidebar, render_hero_card, load_lottieurl, render_hero_landing
from agents.news_agent import NewsAgent
from orchestrator import AgentOrchestrator
import datetime
import random
from utils.destination_duel import run_duel, render_duel_html
from utils.emergency_kit import get_emergency_info, render_emergency_html
from utils.currency_converter import detect_currency_query, convert_with_context, render_currency_card
from utils.achievements import check_achievements, render_badges_html
from utils.trip_dna import generate_trip_dna, render_trip_dna_html
from utils.golden_hour import calculate_golden_hours, get_photo_spots
from utils.jetlag_coach import generate_jetlag_plan
from agents.food_agent import FoodAgent
from utils.trending_interests import get_trending_interests

load_dotenv()

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="WanderTrip — AI Travel Copilot",
    page_icon="🧭",
    layout="wide"
)

# ================= GLOBAL STYLING =================
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ================= EARLY STATE INIT =================
if "profile" not in st.session_state:
    st.session_state.profile = {
        "destination": None, "dates": None, "duration": None,
        "budget": None, "group_type": None, "interests": None,
        "pace": None, "expenses": []
    }

# ================= SIDEBAR =================
# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; margin-bottom: 24px; margin-top: 10px;'>
            <div style='background: linear-gradient(135deg, rgba(0,242,254,0.1), rgba(79,172,254,0.1)); padding: 16px; border-radius: 20px; border: 1px solid rgba(0,242,254,0.2); display: inline-block;'>
                <img src="https://cdn-icons-png.flaticon.com/512/201/201623.png" width="48" style="filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3));"/>
            </div>
            <h2 style='color: #f8fafc; margin: 12px 0 4px 0; font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px;'>WanderTrip</h2>
            <div style='color: #00f2fe; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;'>AI Travel Copilot</div>
        </div>
    """, unsafe_allow_html=True)

    # ── AI Engine Selector ──
    st.markdown("<div style='font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>⚙️ Core Engine</div>", unsafe_allow_html=True)
    model_options = get_model_display_options()
    model_keys = [k for k, _ in model_options]
    model_labels = [label for _, label in model_options]

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "qwen3-32b"

    current_idx = model_keys.index(st.session_state.selected_model) if st.session_state.selected_model in model_keys else 5

    selected_label = st.selectbox(
        "Model",
        model_labels,
        index=current_idx,
        key="_model_selector",
        label_visibility="collapsed"
    )

    for k, lbl in model_options:
        if lbl == selected_label:
            st.session_state.selected_model = k
            break
            
    # System Operations
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("New Trip", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    with col_b:
        if st.button("Save", use_container_width=True, type="primary"):
            st.toast("Profile data refreshed!")

    st.markdown("<br>", unsafe_allow_html=True)
    render_smart_suggestion_sidebar(st.session_state.get("current_chips", {}))

# ================= UI TEMPLATES =================
DECISION_CARD_TEMPLATE = """
<div style="margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
    <span style="font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; font-weight:700;">⚡ Live Decision Engine</span>
    <span class="status-badge status-safe">Use Confidence: {conf}</span>
</div>

<div class="decision-card">
    <!-- SIGNAL BAR -->
    <div style="display:flex; gap:12px; margin-bottom:20px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:15px;">
        <div class="metric-card" style="flex:1;">
            <div class="metric-label">Weather</div>
            <div style="font-size:14px; font-weight:600; color:#e0e6ed;">{temp}°C</div>
            <div style="font-size:12px; color:#94a3b8;">{cond}</div>
        </div>
        <div class="metric-card" style="flex:1;">
            <div class="metric-label">Safety</div>
            <div style="font-size:14px; font-weight:600; color:#00ff80;">Verified</div>
            <div style="font-size:12px; color:#94a3b8;">No Threats</div>
        </div>
        <div class="metric-card" style="flex:1;">
            <div class="metric-label">Crowd</div>
            <div style="font-size:14px; font-weight:600; color:#e0e6ed;">Moderate</div>
            <div style="font-size:12px; color:#94a3b8;">Live Est.</div>
        </div>
    </div>

    <!-- BEST CALL -->
    <div class="section-title" style="color:#00e5ff; margin-bottom:8px;">✅ STRATEGIC RECOMMENDATION</div>
    <div class="best-call">
        <div style="font-size:18px; font-weight:bold; color:#fff; margin-bottom:4px;">{title}</div>
        <div style="font-size:12px; background:rgba(0,229,255,0.1); color:#00e5ff; padding:2px 6px; border-radius:4px; display:inline-block; margin-bottom:12px;">{badge}</div>
        <div style="font-size:14px; line-height:1.5; color:#cbd5e1;">{description}</div>
        
        {itin_html}
    </div>

    <!-- REASONING -->
    <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; margin-bottom:16px;">
        <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">Why this option?</div>
        <div style="font-size:13px; color:#e0e6ed; font-style:italic;">"{conf_reason}"</div>
    </div>

    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
        <!-- AVOID -->
        <div class="avoid-block">
            <div style="font-size:11px; font-weight:700; color:#ff3232; margin-bottom:4px;">❌ RISKY / AVOID</div>
            <div style="font-size:13px; font-weight:600; color:#e0e6ed; margin-bottom:2px;">{avoid_title}</div>
            <div style="font-size:12px; color:#ff7b72;">{avoid_reason}</div>
        </div>

        <!-- BACKUP -->
        <div class="backup-block">
            <div style="font-size:11px; font-weight:700; color:#eda619; margin-bottom:4px;">🔁 PLAN B</div>
            <div style="font-size:13px; font-weight:600; color:#e0e6ed; margin-bottom:2px;">{backup_title}</div>
            <div style="font-size:12px; color:#d29922;">{backup_reason}</div>
        </div>
    </div>
</div>
"""


# ================= SESSION =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "interest_tags" not in st.session_state:
    st.session_state.interest_tags = []

if "temp_interests" not in st.session_state:
    st.session_state.temp_interests = set()

if "profile" not in st.session_state:
    st.session_state.profile = {
        "destination": None,
        "dates": None,
        "duration": None,
        "group_type": None,
        "pace": None,
        "budget": None,
        "interests": None,
        "constraints": None
    }

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "context_manager" not in st.session_state:
    st.session_state.context_manager = ContextAgent()

if "decision_engine" not in st.session_state:
    st.session_state.decision_engine = DecisionEngine()

# Initialize Groq Client (Global)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

if "groq_client" not in st.session_state:
    st.session_state.groq_client = client

if "news_agent" not in st.session_state:
    # Initialize News Agent (Agentic)
    st.session_state.news_agent = NewsAgent(client)
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = AgentOrchestrator(client)
    
if "recommendation_agent" not in st.session_state:
    st.session_state.recommendation_agent = RecommendationAgent(client)

# ================= SIDEBAR: PERSONALIZATION & CONTEXT =================
# ================= SIDEBAR: PERSONALIZATION & CONTEXT =================

# Force Sync Logic (Must be before widget rendering)
if st.session_state.get("force_sync_sidebar"):
    st.session_state.sb_dest = st.session_state.profile.get("destination") or ""
    
    # Sync Duration
    val = st.session_state.profile.get("duration")
    st.session_state.sb_duration = int(val) if val else 3
    
    # Sync Budget Value
    b_val = str(st.session_state.profile.get("budget", ""))
    import re
    digits = re.findall(r'\d+', b_val)
    st.session_state.sb_budget_value = int(digits[0]) if digits else 1000
        
    # Sync People Count
    p_val = str(st.session_state.profile.get("group_type", ""))
    digits = re.findall(r'\d+', p_val)
    st.session_state.sb_people_count = int(digits[0]) if digits else 1
    
    # Sync Pace
    p_str = str(st.session_state.profile.get("pace", "")).title()
    valid_paces = ["Fast", "Relaxed", "Energetic", "Chilled", "Moderate"]
    st.session_state.sb_pace = p_str if p_str in valid_paces else "Moderate"
        
    st.session_state.force_sync_sidebar = False

with st.sidebar:
    # No profile form rendering — relies completely on chat interface

    sac.divider(label='Mission Control', icon='rocket', align='center')
    
    # 1. RISK METER (Live)
    if st.session_state.get("latest_risk"):
        risk = st.session_state.latest_risk
        score = risk.get("total_risk_score", 0)
        verdict = risk.get("verdict", "Unknown")
        
        # Color logic
        r_color = "off"
        if verdict == "Safe": r_color = "normal"
        elif verdict == "Critical": r_color = "inverse"
        
        st.metric(label="🛡️ Safety Status", value=verdict, delta=f"{score}/100 Risk", delta_color=r_color)
    else:
        st.info("Waiting for mission data... (Enter destination)")

    # 2. WEATHER (Live)
    if st.session_state.get("latest_weather"):
        weather = st.session_state.latest_weather.get("weather_data", {})
        col1, col2 = st.columns(2)
        col1.metric("Temp", f"{weather.get('temperature_c', '--')}°C")
        col2.metric("Rain", f"{weather.get('rain_probability', 0)}%")
        st.caption(f"📍 {weather.get('city', 'Locating...')}")

    # 3. LIVE PULSE (New)
    if st.session_state.get("latest_pulse"):
        pulse = st.session_state.latest_pulse
        vibe = pulse.get("vibe", {})
        
        st.markdown("---")
        st.markdown("### 📡 Live Pulse")
        
        # Vibe Check
        v_status = vibe.get("vibe", "Unknown")
        v_note = vibe.get("summary", "")
        if v_status != "Unknown":
            st.info(f"**Vibe:** {v_status}\n\n_{v_note}_")
            
        # Events Count
        events = pulse.get("events", [])
        if events:
            st.success(f"🎉 **{len(events)} Events** detected during your dates!")

    # 4. ACHIEVEMENTS (Badges)
    badges = check_achievements(st.session_state.profile, st.session_state.get("latest_itinerary"), st.session_state)
    if badges:
        st.markdown(render_badges_html(badges), unsafe_allow_html=True)

    # 5. DESTINATION DUEL
    st.markdown("---")
    with st.expander("🆚 Destination Duel", expanded=False):
        duel_col1, duel_col2 = st.columns(2)
        city_a = duel_col1.text_input("City A", placeholder="Tokyo", key="duel_a")
        city_b = duel_col2.text_input("City B", placeholder="Seoul", key="duel_b")
        if st.button("⚔️ DUEL!", use_container_width=True, key="duel_btn"):
            if city_a and city_b:
                with st.spinner(f"⚡ {city_a} vs {city_b}..."):
                    duel_result = run_duel(st.session_state.groq_client, city_a, city_b, st.session_state.profile)
                    st.session_state.latest_duel = duel_result
            else:
                st.warning("Enter both cities!")
    
    if st.session_state.get("latest_duel"):
        st.markdown(render_duel_html(st.session_state.latest_duel), unsafe_allow_html=True)

    # 6. EMERGENCY KIT
    if st.session_state.profile.get("destination"):
        with st.expander("🆘 Emergency Kit", expanded=False):
            if st.session_state.get("emergency_data") and st.session_state.get("emergency_dest") == st.session_state.profile["destination"]:
                st.markdown(render_emergency_html(st.session_state.emergency_data), unsafe_allow_html=True)
            elif st.button("🆘 Load Emergency Info", key="emer_btn", use_container_width=True):
                with st.spinner("Fetching emergency info..."):
                    data = get_emergency_info(st.session_state.groq_client, st.session_state.profile["destination"])
                    st.session_state.emergency_data = data
                    st.session_state.emergency_dest = st.session_state.profile["destination"]
                    st.rerun()

    # 7. REAL-TIME INTEL (News & Events)
    if st.session_state.get("latest_news_intel"):
        news = st.session_state.latest_news_intel
        risks = news.get("safety_risks", [])
        opportunities = news.get("opportunities", [])
        
        if risks or opportunities:
            st.markdown("---")
            with st.expander("🗞️ Real-Time News & Intel", expanded=False):
                # Risks first
                for i, risk in enumerate(risks[:2]):
                    st.markdown(f"**<span style='color:#ff4d4d;'>⚠️ {risk.get('title', '')}</span>**", unsafe_allow_html=True)
                    st.caption(f"{risk.get('summary', '')}")
                    if risk.get('actionable_advice'):
                         st.markdown(f"<div style='font-size:11px; color:#ffb3b3; background:rgba(255,77,77,0.1); padding:4px 8px; border-radius:4px; margin-top:2px;'>💡 {risk.get('actionable_advice')}</div>", unsafe_allow_html=True)
                    if i < min(len(risks), 2) - 1 or opportunities:
                        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed rgba(255,255,255,0.1);' />", unsafe_allow_html=True)

                # Opportunities
                for i, opp in enumerate(opportunities[:2]):
                    st.markdown(f"**<span style='color:#4facfe;'>🌟 {opp.get('title', '')}</span>**", unsafe_allow_html=True)
                    if opp.get('type'):
                         st.markdown(f"<span style='font-size:9px;background:rgba(79,172,254,0.2);color:#4facfe;padding:2px 6px;border-radius:4px; border:1px solid rgba(79,172,254,0.3); text-transform:uppercase;'>{opp.get('type')}</span>", unsafe_allow_html=True)
                    st.caption(f"{opp.get('summary', '')}")
                    if i < min(len(opportunities), 2) - 1:
                        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed rgba(255,255,255,0.1);' />", unsafe_allow_html=True)

    # 8. DID YOU KNOW?
    if st.session_state.get("latest_news_intel"):
        news = st.session_state.latest_news_intel
        facts = news.get("interesting_facts", [])
        if facts:
            st.markdown("---")
            with st.expander("💡 Did You Know?", expanded=False):
                for i, fact in enumerate(facts[:3]):
                    st.markdown(f"**{fact.get('title', '')}**")
                    if fact.get('category'):
                        st.markdown(f"<span style='font-size:9px;background:rgba(255,255,255,0.1);color:#cbd5e1;padding:2px 6px;border-radius:4px; text-transform:uppercase;'>{fact.get('category')}</span>", unsafe_allow_html=True)
                    st.caption(f"{fact.get('description', '')}")
                    if i < min(len(facts), 3) - 1:
                        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid rgba(255,255,255,0.05);' />", unsafe_allow_html=True)



# ================= SYSTEM PROMPT =================
with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


# ================= SMART SUGGESTIONS =================

# ================= DECISION UI RENDERER =================
# ================= DIALOGS =================
# ================= DIALOGS =================
if hasattr(st, "dialog"):
    @st.dialog("✨ Alternative Adventures")
    def show_day_alternatives(day_num, dest):
        # Ensure arguments are safe strings
        safe_day = str(day_num)
        safe_dest = str(dest) if dest else "your destination"
        
        st.markdown(f"Finding unique alternatives for **{safe_day}** in **{safe_dest}**...")
        
        # Quick LLM Call for context-aware alternatives
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            prompt = f"""
            Suggest 3 unique, non-generic alternative activities for a traveler in {safe_dest}.
            Context: They are looking for something different for {safe_day}.
            Return VALID JSON array:
            [
              {{"title": "Activity Name", "description": "Why it's cool (1 sentence)", "time": "Morning/Afternoon/Evening"}}
            ]
            """
            
            res = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            content = res.choices[0].message.content
            # Extract JSON
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                
                for item in data:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin-bottom:8px; border-left:3px solid var(--primary);">
                        <div style="font-weight:bold; color:#fff;">{item.get('title')} <span style="font-weight:normal; font-size:12px; color:#94a3b8; float:right;">{item.get('time')}</span></div>
                        <div style="font-size:13px; color:#cbd5e1; margin-top:4px;">{item.get('description')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Simple confirmation button (no rerun needed inside dialog unless we want to close it)
                    if st.button(f"Swaptop {item.get('title')}", key=f"swap_{safe_day}_{item.get('title')}"):
                         st.toast(f"Tip: You can manually add '{item.get('title')}' to your plan!")
            else:
                st.error("Could not generate alternatives. Please try again.")
        except Exception as e:
            st.error(f"System Error: {str(e)}")

# ================= NATIVE UI RENDERER =================
def render_native_recommendation(data, key_suffix=""):
    """
    Renders the recommendation data using native Streamlit components.
    Enhanced with confidence scoring and Plan A/B/C alternatives.
    """
    if not isinstance(data, dict) or data.get("type") != "recommendation":
        return False
        
    with st.container():
        # Header with Confidence Meter
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption("✨ AI Recommendation")
        with c2:
            # Get confidence from session state risk assessment
            conf_data = st.session_state.get("latest_risk", {}).get("confidence", {})
            conf_score = conf_data.get("score", 0.75)
            
            # Color-coded confidence
            if conf_score >= 0.85:
                conf_color = "🟢"
            elif conf_score >= 0.65:
                conf_color = "🟡"
            else:
                conf_color = "🔴"
            
            st.markdown(f"**{conf_color} {int(conf_score * 100)}% Conf.**")
            
        # Best Call - VISUAL CARD
        best = data.get('best_call', {})
        card_data = {
            "title": best.get('title', 'Top Choice'),
            "description": best.get('description', ''),
            "cost": best.get('cost', 'Price varies'),
            "rating": "Top Pick",
            "tags": [best.get('badge', 'Recommended')]
        }
        st.markdown(render_hero_card(card_data), unsafe_allow_html=True)
        
        # Primary Action Buttons
        # Primary Action Buttons
        # Removed "Book Selection" as per user request
        if st.button("Save to Trip", key=f"save_{key_suffix}", use_container_width=True):
            st.toast("Saved to itinerary!")
            
        # Store detailed options for Deep Intelligence Tab
        if "detailed_options" in data:
            st.session_state.latest_options = data["detailed_options"]
        
        st.divider()

        # Itinerary Preview - TIMELINE (Interactive with Popups)
        if "itinerary_preview" in data and data["itinerary_preview"]:
            st.markdown("#### 📅 Itinerary Preview")
            raw_preview = data["itinerary_preview"]
            
            # Group by day if structure allows, else map to days
            # Assuming raw_preview is a list of activities.
            # We'll group them into days.
            
            days = {}
            for item in raw_preview:
                d_num = item.get("day", "Day 1")
                if d_num not in days:
                    days[d_num] = []
                days[d_num].append(item)
                
            # Natural Sort
            sorted_days = sorted(days.keys(), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999)
            
            if sorted_days:
                # Grid Layout: 2 Columns for better use of space
                cols = st.columns(2)
                
                for i, day_label in enumerate(sorted_days):
                    with cols[i % 2]:
                        # Get data for this day
                        day_acts = days[day_label] 
                        
                        # Extract title
                        day_title = "Highlights"
                        if day_acts and "title" in day_acts[0]:
                             day_title = day_acts[0]["title"]
                        
                        # Use a styled container instead of a simple expander
                        should_expand = (i < 2)
                        with st.expander(f"**{day_title}**", expanded=should_expand):
                            for act in day_acts:
                                # Render the summary description
                                st.markdown(f"{act.get('description', '')}", unsafe_allow_html=True)
                                
                                # Highlights badges
                                badges = []
                                if act.get('location'): badges.append(f"📍 {act['location']}")
                                if act.get('highlight'): badges.append(f"⭐ {act['highlight']}")
                                if act.get('cost_estimate'): badges.append(f"💰 {act['cost_estimate']}")
                                
                                if badges:
                                    st.caption(" | ".join(badges))
                            
                            # Interactive Actions
                            if hasattr(st, "dialog"):
                                if st.button(f"🔄 Alternatives", key=f"alt_{day_label}_{key_suffix}"):
                                    show_day_alternatives(day_label, st.session_state.profile.get("destination"))
                            else:
                                if st.button(f"🔄 Alternatives", key=f"alt_{day_label}_{key_suffix}"):
                                    st.toast("Alternative options feature coming soon!")
                                st.info("Popups require Streamlit 1.34+. Upgrade to see alternatives!")

    return True



# ================= SMART SUGGESTIONS =================
from utils.suggestion_generator import generate_dynamic_suggestions
from utils.feedback_tracker import log_feedback
from utils.analytics_tracker import track_event

def update_suggestion_cache(history):
    # Only look at the last assistant message content for context
    if not history:
        return
        
    last_msg = history[-1]
    if last_msg["role"] != "assistant":
        return

    # Check for existing cached chips for this turn to avoid regeneration
    cache_key = f"chips_{len(history)}_{hash(str(last_msg['content']))}"
    
    # Build Context Summary (needed for both generation and feedback)
    context_summary = {}
    if "latest_weather" in st.session_state:
        weather_data = st.session_state.latest_weather.get("weather_data", {})
        context_summary["weather"] = weather_data.get("condition")
        context_summary["time"] = st.session_state.latest_weather.get("local_time")
    
    if "latest_risk" in st.session_state:
        context_summary["risk"] = st.session_state.latest_risk.get("verdict")
    
    if "current_chips" not in st.session_state or st.session_state.get("chips_cache_key") != cache_key:
        
        # Generate NEW Chips
        dest = st.session_state.profile.get("destination")
        
        # Get conversation history (last 5 messages)
        conversation_history = st.session_state.messages[-5:] if len(st.session_state.messages) > 0 else []
            
        # Call Utility (now returns dict)
        placeholder = st.empty()
        with placeholder.container():
             st.markdown('<div class="ai-thinking-pulse"></div><div style="text-align:center;color:#94a3b8;font-size:12px;margin-top:8px;">Finding smart ideas...</div>', unsafe_allow_html=True)
        
        chips = generate_dynamic_suggestions(
            dest, 
            context_summary, 
            st.session_state.profile,
            conversation_history
        )
        placeholder.empty()
        st.session_state.current_chips = chips
        st.session_state.chips_cache_key = cache_key








# ================= WELCOME SCREEN =================
if len(st.session_state.messages) == 0 and not st.session_state.pending_action:
    # HERO SECTION
    col_text, col_visual = st.columns([1.2, 1], gap="large")
    
    with col_text:
        st.markdown("""
        <div style="padding-top: 20px; text-align: left;">
            <div style="
                display: inline-block; 
                background: rgba(0, 242, 254, 0.1); 
                color: #00f2fe; 
                padding: 4px 12px; 
                border-radius: 20px; 
                font-size: 12px; 
                font-weight: 700; 
                letter-spacing: 1px; 
                margin-bottom: 16px; 
                border: 1px solid rgba(0, 242, 254, 0.2);">
                ✨ NEW: AI TRAVEL V2.0
            </div>
            <h1 style="
                font-size: 4rem; 
                font-weight: 800; 
                line-height: 1.1; 
                margin-bottom: 20px; 
                background: linear-gradient(135deg, #e0e6ed 0%, #94a3b8 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;">
                Plan Your Next <br />
                <span style="background: linear-gradient(90deg, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Adventure</span>
            </h1>
            <p style="font-size: 1.2rem; color: #94a3b8; line-height: 1.6; margin-bottom: 30px; max-width: 90%;">
                Experience the future of travel with our <b>Agentic AI Copilot</b>. 
                Get real-time safety checks, crowd insights, and hyper-personalized itineraries in seconds.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Call to Actions
        b1, b2 = st.columns([1, 1.5])
        with b1:
             if st.button("🚀 Start Planning", type="primary", use_container_width=True):
                 st.session_state.pending_action = "Plan a weekend trip"
                 st.rerun()

    with col_visual:
        lottie_url = "https://assets5.lottiefiles.com/packages/lf20_t2rfa1k1.json" # Travel Animation
        lottie_json = load_lottieurl(lottie_url)
        if lottie_json:
            st_lottie(lottie_json, height=400, key="hero_lottie")

    # METRICS STRIP
    st.markdown("""
    <div class="metrics-container">
        <div class="metric-item">
            <div class="metric-value">10k+</div>
            <div class="metric-label">Travelers</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">500+</div>
            <div class="metric-label">Destinations</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">98%</div>
            <div class="metric-label">Satisfaction</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">24/7</div>
            <div class="metric-label">AI Support</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # FEATURE GRID
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <span class="feature-icon">🧠</span>
            <div class="feature-title">Agentic AI Planning</div>
            <div class="feature-desc">Our multi-agent system autonomously researches, plans, and validates your entire trip itinerary.</div>
        </div>
        <div class="feature-card">
            <span class="feature-icon">🛡️</span>
            <div class="feature-title">Real-time Safety</div>
            <div class="feature-desc">Live feedback on weather, crowd levels, and political stability for every destination.</div>
        </div>
        <div class="feature-card">
            <span class="feature-icon">💰</span>
            <div class="feature-title">Smart Budgeting</div>
            <div class="feature-desc">Dynamic currency conversion and cost estimation tailored to your spending style.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # QUICK ACTION GRID
    c1, c2, c3 = st.columns(3, gap="large")
    
    with c1:
        st.markdown("""
        <div class="action-card">
            <span class="action-icon">🗺️</span>
            <div class="action-title">Plan</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start New Trip", key="cmd_plan", use_container_width=True, type="primary"):
            st.session_state.pending_action = "Plan a weekend trip"
            st.rerun()
        
    with c2:
        st.markdown("""
        <div class="action-card">
            <span class="action-icon">🏨</span>
            <div class="action-title">Stays</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Find Hotels", key="cmd_hotel", use_container_width=True, type="primary"):
            st.session_state.pending_action = "Find hotels"
            st.rerun()
        
    with c3:
        st.markdown("""
        <div class="action-card">
            <span class="action-icon">🎲</span>
            <div class="action-title">Inspire</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Surprise Me", key="cmd_inspire", use_container_width=True, type="primary"):
            st.session_state.pending_action = "Suggest unique destinations"
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Tip**: I can check live weather, crowd density, and safety risks for any destination.")
    st.stop()


# ================= CHAT RENDER =================
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"""<div class='chat-row user'>
            <div class='user-bubble'>{msg['content']}</div>
            <div class='chat-avatar user-av'>🧑</div>
        </div>""", unsafe_allow_html=True)
    else:

        content = msg['content']
        is_card = False
        
        # Case A: Content is already a Dict (from Agent)
        if isinstance(content, dict):
            is_card = render_native_recommendation(content, key_suffix=str(idx))
            
        # Case B: Content is a String (Legacy or Raw LLM fallback)
        elif isinstance(content, str):
            # Try to parse as JSON first
            clean_content = content.replace("```json", "").replace("```", "").strip()
            if clean_content.startswith("{") and clean_content.endswith("}"):
                try:
                    data = json.loads(clean_content)
                    if isinstance(data, dict) and data.get("type") == "recommendation":
                        is_card = render_native_recommendation(data, key_suffix=str(idx))
                except:
                    pass

        # Fallback: Render as Text/HTML Bubble
        if not is_card:
            # If it's a dict but not a recommendation, dump it as string
            if isinstance(content, dict):
                text_content = json.dumps(content, indent=2)
            else:
                text_content = str(content)
                
            # Clean strict HTML/Code blocks from fallback text
            clean_fallback = text_content.replace("```html", "").replace("```", "").strip()
            
            # Check for allowed HTML tags
            if '<div' in clean_fallback or '<span' in clean_fallback:
                 st.markdown(clean_fallback, unsafe_allow_html=True)
            else:
                 st.markdown(f"""<div class='chat-row bot'>
                     <div class='chat-avatar bot-av'>🤖</div>
                     <div class='bot-bubble'>{text_content}</div>
                 </div>""", unsafe_allow_html=True)


# ================= PROFILE EXTRACTOR =================
def extract_profile(message):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
You are a trip profile extractor. Extract travel details from the user's message.
- "Tomorrow", "Next week" → Convert to approximate dates if possible.
- For "budget", output a real currency value (e.g. "$5000" or "$1500") if mentioned.
- For "duration", output the number of days as an integer (e.g. 5).
- For "group_type", output the number of people and composition (e.g. "2 (Couple)", "4 (Family)", "1 (Solo)"). YOU MUST INCLUDE THE NUMBER.
- For "pace", detect if they want a fast, relaxed, energetic, or chilled pace.

Return a JSON object with strictly these keys. If a value is not mentioned, use null.
Keys:
"destination" (string or null)
"dates" (string or null)
"duration" (integer or null)
"group_type" (string or null)
"pace" (string or null)
"budget" (string or null)
"interests" (string or null)
"constraints" (string or null)

User:
{message}
"""

    try:
        res = client.chat.completions.create(
            # Force smaller model to avoid rate limits and reduce cost for background tasks
            model="qwen/qwen3-32b", 
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        ).choices[0].message.content
    except Exception as e:
        # Fail silently for background profile extraction to keep app running
        print(f"Profile extraction skipped: {e}")
        return

    try:
        # Robust JSON extraction
        clean_res = res.strip()
        clean_res = re.sub(r'<think>.*?</think>', '', clean_res, flags=re.DOTALL).strip()
        if "{" in clean_res and "}" in clean_res:
            s = clean_res.find("{")
            e = clean_res.rfind("}") + 1
            clean_res = clean_res[s:e]
        data = json.loads(clean_res)
        print("LLM extracted:", data) # Debug
        for k, v in data.items():
            
            # Explicitly wipe "Flexible" from state if the new payload sends null destination
            if k == "destination" and (v is None or str(v).lower() in ["none", "null", "undefined", "unknown", ""]):
                if st.session_state.profile.get("destination", "").lower() == "flexible":
                    st.session_state.profile["destination"] = None
                    st.session_state.force_sync_sidebar = True
                continue
                
            if k in st.session_state.profile and v is not None and str(v).lower() not in ["none", "null", "undefined", "unknown", ""]:

                # Special Handling for Duration
                if k == "duration":
                    try:
                        st.session_state.profile[k] = int(v)
                    except ValueError:
                        import re
                        digits = re.findall(r'\d+', str(v))
                        if digits:
                            st.session_state.profile[k] = int(digits[0])
                else:
                    # Strip symbols from budget if it's a number
                    if k == "budget":
                        import re
                        numeric_budget = re.sub(r'[^\d.]', '', str(v))
                        if numeric_budget:
                            st.session_state.profile[k] = f"${numeric_budget}"
                        else:
                            st.session_state.profile[k] = str(v).strip()
                    else:
                        st.session_state.profile[k] = str(v).strip()

            # Sync Sidebar Keys Auto-Update on ALL fields
            st.session_state.force_sync_sidebar = True
                
    except:
        pass

    if not st.session_state.profile["destination"] and "goa" in message.lower():
        st.session_state.profile["destination"] = "Goa"


# Removed missing_questions function
# The system now allows the LLM to decide what to ask.


# ================= INTERACTIVE FORM LOGIC =================
def render_interactive_stage():
    """
    Checks for missing profile fields and renders a specialized UI widget
    to collect that specific piece of information.
    Returns TRUE if an interactive widget was shown (blocking normal chat),
    False otherwise.
    """
    profile = st.session_state.profile
    
    # 1. Destination (Modern Card Design)
    if not profile["destination"]:
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">🌍</span>
                <span>Where would you like to go?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get seasonal recommendations
        de = st.session_state.decision_engine
        recs = de.get_seasonal_recommendations()

        # --- 🎲 I'M FEELING LUCKY ---
        col_lucky, col_help = st.columns([1, 2])
        with col_lucky:
             if st.button("🎲 I'm Feeling Lucky", type="primary", use_container_width=True, help="Let AI pick a perfect spot for you!"):
                 # Flatten all places
                 all_places = [p for cat in recs.values() for p in cat]
                 if all_places:
                     lucky_pick = random.choice(all_places)
                     st.toast(f"✨ Destiny chose: {lucky_pick}!")
                     st.session_state.profile["destination"] = lucky_pick
                     st.session_state.force_sync_sidebar = True
                     st.session_state.messages.append({"role": "user", "content": f"I'm feeling lucky! Let's go to {lucky_pick}."})
                     st.rerun()

        st.markdown("---")
        
        # --- ✍️ MANUAL INPUT ---
        st.markdown("<div style='margin-bottom: 8px;'><em style='color:#94a3b8;'>Or type your dream destination:</em></div>", unsafe_allow_html=True)
        col_dest, col_go = st.columns([3, 1])
        manual_dest = col_dest.text_input("Enter city or country", key="manual_dest_input", label_visibility="collapsed", placeholder="e.g. Paris, France")
        if col_go.button("🚀 Let's Go", use_container_width=True, type="primary"):
            if manual_dest:
                st.session_state.profile["destination"] = manual_dest
                st.session_state.force_sync_sidebar = True
                
                # Check for pending action from Surprise Me or Plan My Trip
                if st.session_state.get("pending_action"):
                    action = st.session_state.pending_action
                    st.session_state.pending_action = None
                    st.session_state.messages.append({"role": "user", "content": f"I'd like to travel to {manual_dest}. {action}"})
                else:
                    st.session_state.messages.append({"role": "user", "content": f"I'd like to travel to {manual_dest}."})
                    
                st.rerun()
            else:
                st.warning("Please enter a destination!")

        st.markdown("---")
        
        # --- 🗂️ TABBED CATEGORIES ---
        # Sort tabs to keep "International" and "Adventure" prominent if they exist
        cat_order = ["🌏 International Gems", "🧗 Adventure Capital", "❄️ Snowy Peaks", "🏖️ Winter Sun", "🧘 Spiritual Journeys", "🍜 Foodie Paradise"]
        # Add remaining categories dynamically
        for k in recs.keys():
            if k not in cat_order:
                cat_order.append(k)
        
        # Filter tabs to only those that actually exist in recs
        final_tabs = [c for c in cat_order if c in recs]
        
        if final_tabs:
            tabs = st.tabs(final_tabs)
            
            for i, category in enumerate(final_tabs):
                with tabs[i]:
                    places = recs[category]
                    
                    # Responsive Grid using columns
                    cols = st.columns(3) # 3 cards per row looks better
                    
                    for idx, place in enumerate(places):
                        with cols[idx % 3]:
                            # Card-like Container
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
                                border: 1px solid rgba(255,255,255,0.08);
                                border-radius: 12px;
                                padding: 16px;
                                margin-bottom: 12px;
                                text-align: center;
                                transition: transform 0.2s;
                            ">
                                <div style="font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 4px;">{place}</div>
                                <div style="font-size: 0.8rem; color: #94a3b8;">{category.split(' ')[0]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Action Button (Unique Key Fixed)
                            if st.button(f"Explore {place}", key=f"btn_{category}_{place}", use_container_width=True):
                                st.session_state.profile["destination"] = place
                                st.session_state.force_sync_sidebar = True
                                st.session_state.messages.append({"role": "user", "content": f"I want to explore {place}."})
                                st.rerun()
                                
        return True

    # 2. Dates (Modern Calendar Design)
    if not profile["dates"]:
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">📅</span>
                <span>When are you planning to travel?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        d1 = c1.date_input("🛫 Start Date", key="d_start")
        d2 = c2.date_input("🛬 End Date", key="d_end")
        
        # Show duration preview
        if d1 and d2:
            days_count = (d2 - d1).days
            st.markdown(f"<div style='text-align:center; margin:16px 0; font-size:1.1rem; color:#00e5ff;'>📆 Trip Duration: <strong>{days_count} days</strong></div>", unsafe_allow_html=True)
        
        if st.button("✅ Confirm Dates", type="primary", use_container_width=True):
            days_count = (d2 - d1).days
            st.session_state.profile["dates"] = f"{d1} to {d2}"
            st.session_state.profile["duration"] = days_count
            st.session_state.messages.append({"role": "assistant", "content": "When are you planning to travel?"})
            st.session_state.messages.append({"role": "user", "content": f"I've selected travel dates from {d1} to {d2}. This is a {days_count}-day trip."})
            st.rerun()
        return True

    # 3. Travelers (Icon-based Selection)
    if not profile["group_type"]:
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">👥</span>
                <span>Who's traveling?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Traveler type options
        traveler_options = [
            {"icon": "🧍", "label": "Solo", "count": 1},
            {"icon": "👫", "label": "Couple", "count": 2},
            {"icon": "👨‍👩‍👧", "label": "Family", "count": 4},
            {"icon": "👥", "label": "Group", "count": 6}
        ]
        
        cols = st.columns(4)
        for idx, option in enumerate(traveler_options):
            with cols[idx]:
                if st.button(f"{option['icon']}\n{option['label']}", key=f"trav_{option['label']}", use_container_width=True):
                    st.session_state.profile["group_type"] = f"{option['count']} ({option['label']})"
                    st.session_state.messages.append({"role": "assistant", "content": "Who's traveling?"})
                    st.session_state.messages.append({"role": "user", "content": f"It will be {option['count']} traveler(s) - {option['label']}."})
                    st.rerun()
        
        st.markdown("<div style='text-align:center; margin:20px 0;'><em style='color:#94a3b8;'>Or specify custom details:</em></div>", unsafe_allow_html=True)
        col_count, col_type, col_btn = st.columns([2, 5, 2])
        count = col_count.number_input("Count", min_value=1, max_value=20, value=1, step=1, label_visibility="collapsed")
        g_type = col_type.selectbox("Type", ["Friends", "Family", "Business", "Other"], label_visibility="collapsed", key="custom_gtype")
        if col_btn.button("✓", use_container_width=True, key="btn_custom_trav"):
            st.session_state.profile["group_type"] = f"{count} ({g_type})"
            st.session_state.messages.append({"role": "assistant", "content": "Who's traveling?"})
            st.session_state.messages.append({"role": "user", "content": f"It will be {count} traveler(s) - {g_type}."})
            st.rerun()
        
        return True

    # 3.5 Pace (Actionable Selection)
    if not profile.get("pace"):
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">⚡</span>
                <span>Select your travel pace</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        pace_options = ["Relaxed", "Chilled", "Moderate", "Energetic", "Fast"]
        cols = st.columns(len(pace_options))
        for idx, p in enumerate(pace_options):
            with cols[idx]:
                if st.button(p, key=f"btn_pace_{p}", use_container_width=True):
                    st.session_state.profile["pace"] = p
                    st.session_state.force_sync_sidebar = True
                    st.session_state.messages.append({"role": "assistant", "content": "What's your preferred travel pace?"})
                    st.session_state.messages.append({"role": "user", "content": f"I prefer a {p} pace."})
                    st.rerun()
        
        st.markdown("---")
        return True

    # 4. Budget (Currency Cards + Amount)
    if not profile["budget"]:
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">💰</span>
                <span>What's your budget?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Currency selection with cards
        st.markdown("<div style='font-size:1rem; color:#94a3b8; margin-bottom:12px;'>Select Currency:</div>", unsafe_allow_html=True)
        currencies = [
            {"code": "INR", "symbol": "₹", "name": "Indian Rupee"},
            {"code": "USD", "symbol": "$", "name": "US Dollar"},
            {"code": "EUR", "symbol": "€", "name": "Euro"},
            {"code": "GBP", "symbol": "£", "name": "Pound"}
        ]
        
        cols = st.columns(4)
        selected_currency = None
        for idx, curr in enumerate(currencies):
            with cols[idx]:
                if st.button(f"{curr['symbol']}\n{curr['code']}", key=f"curr_{curr['code']}", use_container_width=True):
                    selected_currency = curr
        
        # Amount input
        st.markdown("<div style='font-size:1rem; color:#94a3b8; margin:20px 0 12px 0;'>Enter Amount:</div>", unsafe_allow_html=True)
        
        if "selected_currency" not in st.session_state:
            st.session_state.selected_currency = currencies[0]
        
        if selected_currency:
            st.session_state.selected_currency = selected_currency
        
        curr = st.session_state.selected_currency
        default_amount = 50000 if curr['code'] == 'INR' else 1000
        
        col_amount, col_confirm = st.columns([3, 1])
        amount = col_amount.number_input(
            f"Amount in {curr['code']}",
            min_value=0,
            value=default_amount,
            step=100 if curr['code'] != 'INR' else 1000,
            label_visibility="collapsed"
        )
        
        if col_confirm.button("✅ Confirm", use_container_width=True, type="primary"):
            formatted_budget = f"{curr['symbol']} {amount:,.0f}"
            st.session_state.profile["budget"] = formatted_budget
            st.session_state.messages.append({"role": "assistant", "content": "What's your budget?"})
            st.session_state.messages.append({"role": "user", "content": f"My budget is around {formatted_budget}."})
            st.rerun()
        
        return True
        
    # 5. Interests (Enhanced Chips)
    if not profile["interests"]:
        dest = profile.get("destination", "")

        # Dynamic AI Categories
        if "interest_tags" not in st.session_state or not st.session_state.interest_tags:
             with st.spinner(f"🌍 Scouting trending interests in {dest}..."):
                 st.session_state.interest_tags = get_trending_interests(dest)

        st.markdown(f"""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">🎭</span>
                <span>What interests you in {dest}?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Quick Action Buttons (Random / Select All) ---
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🎲 Random Selection", use_container_width=True, key="rand_interests"):
                all_tags = []
                if isinstance(st.session_state.interest_tags, dict):
                    for tags in st.session_state.interest_tags.values():
                        all_tags.extend(tags)
                if all_tags:
                    # Pick 3-5 random interests
                    pick = min(random.randint(3, 5), len(all_tags))
                    st.session_state.temp_interests = set(random.sample(all_tags, pick))
                    st.rerun()
        with btn_col2:
            if st.button("✅ Select All", use_container_width=True, key="all_interests"):
                if isinstance(st.session_state.interest_tags, dict):
                    all_tags = []
                    for tags in st.session_state.interest_tags.values():
                        all_tags.extend(tags)
                    st.session_state.temp_interests = set(all_tags)
                    st.rerun()

        # Render Enhanced Chips
        if isinstance(st.session_state.interest_tags, dict):
            for category, tags in st.session_state.interest_tags.items():
                st.markdown(f"<div class='category-title'>✨ {category}</div>", unsafe_allow_html=True)
                
                # Create columns for chips
                cols = st.columns(min(len(tags), 4))
                for i, tag in enumerate(tags):
                    with cols[i % 4]:
                        is_selected = tag in st.session_state.temp_interests
                        label = f"✅ {tag}" if is_selected else tag
                        btn_type = "primary" if is_selected else "secondary"
                        
                        if st.button(label, key=f"int_{category}_{tag}", type=btn_type, use_container_width=True):
                            if is_selected:
                                st.session_state.temp_interests.remove(tag)
                            else:
                                st.session_state.temp_interests.add(tag)
                            st.rerun()
        else:
            st.info("Type your interests below.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Show selected count
        if st.session_state.temp_interests:
            st.markdown(f"<div style='text-align:center; color:#00e5ff; margin:16px 0;'>Selected: <strong>{len(st.session_state.temp_interests)} interests</strong></div>", unsafe_allow_html=True)
            
            if st.button("✅ Confirm Selection", type="primary", use_container_width=True):
                final_interests = ", ".join(st.session_state.temp_interests)
                st.session_state.profile["interests"] = final_interests
                st.session_state.messages.append({"role": "assistant", "content": f"What interests you in {dest}?"})
                st.session_state.messages.append({"role": "user", "content": f"I'm interested in: {final_interests}."})
                st.session_state.temp_interests = set()
                st.rerun()
        
        # Manual Input fallback
        st.markdown("<div style='text-align:center; margin:20px 0;'><em style='color:#94a3b8;'>Or add custom interest:</em></div>", unsafe_allow_html=True)
        col_manual, col_add = st.columns([3, 1])
        manual = col_manual.text_input("Custom interest", key="manual_int", label_visibility="collapsed", placeholder="e.g., Photography")
        if manual and col_add.button("➕", use_container_width=True):
            st.session_state.temp_interests.add(manual)
            st.rerun()
        
        return True
        
    # 6. Constraints / Special Requirements
    if not profile.get("constraints"):
        st.markdown("""
        <div class="question-card">
            <div class="question-header">
                <span class="question-icon">✨</span>
                <span>Any special requirements, restrictions, or must-dos?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick Constraints Options
        constraint_options = ["None (Fully Flexible)", "Vegetarian/Vegan options", "Wheelchair Accessible", "Kid-Friendly Activities", "Romantic Vibe"]
        cols = st.columns(len(constraint_options) if len(constraint_options) <= 3 else 3)
        for idx, constr in enumerate(constraint_options):
            with cols[idx % 3]:
                if st.button(constr, key=f"btn_constr_{idx}", use_container_width=True):
                    val = "None" if "None" in constr else constr
                    st.session_state.profile["constraints"] = val
                    st.session_state.force_sync_sidebar = True
                    st.session_state.messages.append({"role": "assistant", "content": "Any special requirements or must-dos?"})
                    st.session_state.messages.append({"role": "user", "content": f"My focus: {constr}."})
                    st.rerun()
                    
        st.markdown("<div style='text-align:center; margin:20px 0;'><em style='color:#94a3b8;'>Or type your specific needs:</em></div>", unsafe_allow_html=True)
        col_c_text, col_c_btn = st.columns([3, 1])
        c_text = col_c_text.text_input("Custom requirements", key="manual_constr", label_visibility="collapsed", placeholder="e.g. 'Must see Eiffel Tower', 'Nut allergy'")
        if col_c_btn.button("✅ Save", use_container_width=True, key="btn_save_constr"):
            st.session_state.profile["constraints"] = c_text if c_text else "None"
            st.session_state.messages.append({"role": "assistant", "content": "Any special requirements or must-dos?"})
            st.session_state.messages.append({"role": "user", "content": f"Requirements: {c_text}."})
            st.rerun()
            
        return True
        
    return False


# ================= INPUT HANDLER =================
auto = st.session_state.pending_action
user = None

# Sidebar Context
with st.sidebar:
    # --- SMART SUGGESTIONS (Moved from Main View) ---
    if st.session_state.get("current_chips"):
        st.markdown("### ✨ Smart Ideas")
        st.markdown(render_smart_suggestion_sidebar(st.session_state.current_chips), unsafe_allow_html=True)
        st.markdown("---")

    st.markdown("### 🛸 Mission Control")
    st.caption(f"System Status: 🟢 Online | {datetime.datetime.now().strftime('%H:%M')}")
    st.markdown("---")

    # --- SAVE / LOAD TRIPS ---
    from utils.trip_manager import TripManager
    trip_mgr = TripManager()
    
    with st.expander("📂 My Trips", expanded=False):
        # Save Current
        if st.button("💾 Save Current Trip", use_container_width=True):
            if st.session_state.profile.get("destination"):
                success, msg = trip_mgr.save_trip(st.session_state.profile, st.session_state.messages)
                if success:
                    st.success(msg)
                else:
                    st.error(f"Save failed: {msg}")
            else:
                st.warning("Start a trip plan first!")

        # Load Previous
        saved_trips = trip_mgr.list_trips()
        if saved_trips:
            selected_trip = st.selectbox(
                "Load Trip:", 
                options=[t["filename"] for t in saved_trips],
                format_func=lambda x: next((f"{t['destination']} ({t['date'][:10]})" for t in saved_trips if t["filename"] == x), x)
            )
            
            if st.button("📂 Load Selected", use_container_width=True):
                data, msg = trip_mgr.load_trip(selected_trip)
                if data:
                    st.session_state.profile = data["profile"]
                    st.session_state.messages = data["messages"]
                    st.success("Trip loaded!")
                    st.rerun()
                else:
                    st.error(f"Load failed: {msg}")
        else:
            st.caption("No saved trips found.")

    # --- EXPENSE TRACKER ---
    with st.expander("💸 Expense Tracker", expanded=False):
        from utils.expense_tracker import add_expense, get_budget_status, parse_expense_text
        
        # Budget Visualization
        b_status = get_budget_status(st.session_state.profile)
        if b_status["budget_limit"] > 0:
            st.progress(min(b_status["percent_used"] / 100, 1.0), text=f"Spent: {b_status['total_spent']:,.0f} / {b_status['budget_limit']:,.0f}")
        else:
            st.info("Set a budget in the chat to track progress.")

        # Quick Add Tabs
        tab_manual, tab_scan = st.tabs(["Manual", "Smart Scan"])
        
        with tab_manual:
            with st.form("expense_form"):
                ex_desc = st.text_input("Description", placeholder="Lunch at Mario's")
                ex_amount = st.number_input("Amount", min_value=0.0, step=10.0)
                ex_cat = st.selectbox("Category", ["Food", "Transport", "Stay", "Activity", "Shopping", "Misc"])
                if st.form_submit_button("Add Expense"):
                    add_expense(st.session_state.profile, ex_amount, ex_cat, ex_desc)
                    st.success("Added!")
                    st.rerun()
        
        with tab_scan:
            scan_text = st.text_area("Paste Receipt Text / Description", placeholder="Spent 50 bucks on taxi...")
            if st.button("✨ Parse & Add"):
                with st.spinner("AI Parsing..."):
                    # Use client from session or re-init
                    parsed = parse_expense_text(scan_text)
                    if parsed and parsed.get("amount"):
                        add_expense(st.session_state.profile, parsed["amount"], parsed.get("category", "Misc"), parsed.get("description", scan_text))
                        st.success(f"Added: {parsed['description']} ({parsed['amount']})")
                        st.rerun()
                    else:
                        st.error("Could not parse expense.")
                        
        # Recent Expenses
        if st.session_state.profile.get("expenses"):
            st.caption("Recent:")
            for e in st.session_state.profile["expenses"][-3:]:
                st.text(f"{e.get('category')}: {e.get('amount')} - {e.get('description')}")
    
    st.markdown("---")
    
    # 0. PROACTIVE ALERTS
    if "latest_alerts" in st.session_state and st.session_state.latest_alerts:
        for alert in st.session_state.latest_alerts:
            type_map = {"warning": "⚠️", "critical": "🚨", "info": "ℹ️"}
            icon = type_map.get(alert.get("type", "info"), "ℹ️")
            
            if alert.get("type") == "critical":
                st.error(f"**{icon} {alert.get('title')}**\n\n{alert.get('message')}")
            elif alert.get("type") == "warning":
                st.warning(f"**{icon} {alert.get('title')}**\n\n{alert.get('message')}")
            else:
                st.info(f"**{icon} {alert.get('title')}**\n\n{alert.get('message')}")
        st.markdown("---")

    # 1. RISK METER
    if "latest_risk" in st.session_state:
        risk = st.session_state.latest_risk
        score = risk.get("total_risk_score", 0)
        verdict = risk.get("verdict", "Unknown")
        
        # Color logic
        r_color = "off"
        if verdict == "Safe": r_color = "normal"
        elif verdict == "Caution": r_color = "off"
        elif verdict == "Critical": r_color = "inverse"
        
        st.metric(label="🛡️ Risk Analysis", value=f"{score}/100", delta=verdict, delta_color=r_color)
        st.progress(score)
        
        risk_factors = risk.get("risk_factors", [])
        recommendations = risk.get("actionable_recommendations", [])
        
        if recommendations:
            st.markdown("#### 💡 Actionable Advice")
            for rec in recommendations:
                st.markdown(f"- {rec}")
                
        if risk_factors:
            with st.expander("🔍 Risk Reasons", expanded=False):
                for factor in risk_factors:
                    level = factor.get("level", "Info")
                    source = factor.get("source", "General")
                    msg = factor.get("message", "")
                    
                    if level == "Critical" or level == "High":
                        st.error(f"**{source} ({level})**: {msg}")
                    elif level in ["Medium", "Caution"]:
                        st.warning(f"**{source} ({level})**: {msg}")
                    else:
                        st.info(f"**{source} ({level})**: {msg}")
        else:
            with st.expander("🔍 Risk Reasons", expanded=False):
                st.success("✅ No significant risks detected.")
    else:
        st.info("Waiting for mission data...")

    # 2. BUDGET TRACKER
    budget = st.session_state.profile.get("budget", "Not set")
    st.metric(label="💰 Budget Tier", value=budget)

    # 3. LIVE SIGNALS
    st.markdown("### 📡 Live Signals")
    
    # Weather
    weather = st.session_state.get("latest_weather", {}).get("weather_data", {})
    if weather:
        col1, col2 = st.columns(2)
        col1.metric("Temp", f"{weather.get('temperature_c', '--')}°C")
        col2.metric("Rain", f"{weather.get('rain_probability', 0)}%")
        st.caption(f"📍 {weather.get('city', 'Locating...')}")
    
    # News Alerts (Collapsible)
    if "latest_news_intel" in st.session_state:
        news = st.session_state.latest_news_intel or {}  # Handle None case
        if news.get("safety_risks"):
            with st.expander("🚨 Active Threats", expanded=True):
                for n in news["safety_risks"]:
                    st.error(f"**{n['title']}**\n\n{n['summary']}")
        
        # Interesting Facts Section
        if news.get("interesting_facts"):
            with st.expander("✨ Did You Know?", expanded=False):
                for fact in news["interesting_facts"]:
                    category = fact.get("category", "Tip")
                    icon = {"Culture": "🎭", "History": "🏛️", "Food": "🍽️", "Nature": "🌿", "Tip": "💡"}.get(category, "📌")
                    st.info(f"{icon} **{fact.get('title', 'Local Highlight')}**\n\n{fact.get('description', '')}")
        
        # Opportunities Section
        if news.get("opportunities"):
            with st.expander("🎉 Happening Now", expanded=False):
                for op in news["opportunities"]:
                    st.success(f"**{op.get('title', 'Event')}**\n\n{op.get('summary', '')}")

    st.markdown("---")
    
    # ================= AUTHENTICATION MODAL =================
    if "users" not in st.session_state:
        st.session_state.users = {} # Free authentication technique (dict in session state)
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if hasattr(st, "dialog"):
        @st.dialog("Save Your Trip Plan")
        def auth_dialog():
            if st.session_state.current_user:
                st.success(f"Trip saved successfully to {st.session_state.current_user['name']}'s profile!")
                st.balloons()
            else:
                tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])
                
                with tab_signin:
                    si_email = st.text_input("Email", key="si_email")
                    si_password = st.text_input("Password", type="password", key="si_pass")
                    
                    if st.button("Sign In", use_container_width=True, key="btn_signin"):
                        if si_email in st.session_state.users and st.session_state.users[si_email]["password"] == si_password:
                            st.session_state.current_user = st.session_state.users[si_email]
                            st.success("Signed in successfully! Your plan is saved.")
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                            
                with tab_signup:
                    su_name = st.text_input("Full Name", key="su_name")
                    su_gender = st.selectbox("Gender", ["Select...", "Male", "Female", "Non-binary", "Other", "Prefer not to say"], key="su_gender")
                    su_email = st.text_input("Email Address", key="su_email")
                    su_password = st.text_input("Create Password", type="password", key="su_pass")
                    su_interests = st.text_input("Favorite Interests (comma separated)", placeholder="Hiking, Food, History", key="su_int")
                    
                    if st.button("Create Account & Save Plan", use_container_width=True, key="btn_signup"):
                        if not su_name or not su_email or not su_password or su_gender == "Select...":
                            st.warning("Please fill in all required fields.")
                        elif su_email in st.session_state.users:
                            st.error("An account with this email already exists.")
                        else:
                            st.session_state.users[su_email] = {
                                "name": su_name,
                                "gender": su_gender,
                                "email": su_email,
                                "password": su_password,
                                "interests": [i.strip() for i in su_interests.split(",") if i.strip()]
                            }
                            st.session_state.current_user = st.session_state.users[su_email]
                            st.success("Account created successfully! Your plan is saved.")
                            st.balloons()
                            st.rerun()
    else:
        # Fallback if st.dialog is not available
        def auth_dialog():
            st.warning("Please update Streamlit to use the Save functionality.")


    # Save Plan button
    if st.button("💾 Save this plan", type="primary", use_container_width=True):
        auth_dialog()

    if st.button("🧹 Reset Mission", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ================= HERO LANDING (First Visit) =================
if not st.session_state.messages:
    # Render hero as components.html (bypasses Streamlit markdown sanitizer)
    hero_css = get_custom_css().replace('<style>', '').replace('</style>', '')
    hero_html_block = f"""
    <html><head>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; color: #f8fafc; }}
        {hero_css}
    </style>
    </head><body>
    {render_hero_landing()}
    </body></html>
    """
    components.html(hero_html_block, height=700, scrolling=False)

    # CTA buttons
    cta_col1, cta_col2, cta_col3 = st.columns([1, 2, 1])
    with cta_col2:
        if st.button("🚀 Start Planning Your Trip", type="primary", use_container_width=True, key="hero_cta"):
            st.session_state.pending_action = "Hi! I'd like to plan a trip."
            st.rerun()

# Check for Interactive Mode FIRST
is_interactive_mode = render_interactive_stage()

if not is_interactive_mode:
    # Check for pending actions (from buttons)
    if st.session_state.get("pending_action"):
        user = st.session_state.pending_action
        st.session_state.pending_action = None
    else:
        # Chat Input
        text_input = st.chat_input("Talk about your trip… anything 🙂")
        
        user = text_input


if user:
    st.session_state.messages.append({"role": "user", "content": user})
    extract_profile(user)
    
    # Force clear legacy "Flexible" hallucinations
    if st.session_state.profile.get("destination", "").lower() == "flexible":
        st.session_state.profile["destination"] = None
        st.session_state.force_sync_sidebar = True

    # ===== AGENTIC THINKING PROCESS =====
    try:
        with st.status("🧠 Orchestrating Agents...", expanded=True) as status:
            
            # 1. Orchestration
            status.write("dispatching task to sub-agents...")
            destination = st.session_state.profile.get("destination")
            
            if destination and destination.lower() != "flexible":
                 orch = st.session_state.orchestrator
                 current_loc = st.session_state.get("current_location")
                 
                 # RUN AGENTS
                 intel = orch.run_analysis(destination, st.session_state.profile, current_loc)
                 
                 if "error" in intel:
                     st.error(f"Orchestration Error: {intel['error']}")
                 else:
                     # Update Session State with fresh intel
                     st.session_state.latest_news_intel = intel["news_intel"]
                     st.session_state.latest_risk = intel["risk_assessment"]
                     st.session_state.latest_weather = intel["weather_intel"]
                     st.session_state.latest_crowd = intel["crowd_intel"]
                     
                     # New Agent Intel
                     st.session_state.latest_budget = intel.get("budget_intel")
                     st.session_state.latest_culture = intel.get("cultural_intel")
                     st.session_state.latest_health = intel.get("health_intel")
                     st.session_state.latest_sustainability = intel.get("sustainability_intel")
                     st.session_state.latest_packing = intel.get("packing_list")
                     st.session_state.latest_itinerary = intel.get("itinerary")
                     
                     # Proactive Alerts
                     st.session_state.latest_alerts = intel.get("alerts", [])
                     
                     # Legacy Context Adapter (for DecisionEngine compatibility if needed)
                     # But ideally we use the intel directly.
                     ctx_str = f"""
                     Weather: {intel['weather_intel']}
                     News Risks: {intel['risk_assessment']['risk_factors']}
                     Crowd: {intel['crowd_intel']}
                     """
                     
                     status.write(f"Risk Verdict: {intel['risk_assessment']['verdict']} (Score: {intel['risk_assessment']['total_risk_score']})")
    
            # 3. Decision Engine Logic (Legacy - keep for detailed suggestions)
            # We can still use the old DE for suggestion generation until we fully migrate that too.
            # rebuilding context for legacy DE
            cm = st.session_state.context_manager
            de = st.session_state.decision_engine
            
            # Dummy weather/loc for legacy compat
            loc = st.session_state.get("current_location", {})
            weather_ctx = st.session_state.get("latest_weather", {}).get("weather_data", {})
            
            ctx = cm.build_context(st.session_state.profile, loc, weather_ctx)
            
            # Inject Agent Intel into Legacy Context
            if "latest_news_intel" in st.session_state:
                ctx["news"] = st.session_state.latest_news_intel
                
            if "latest_weather" in st.session_state:
                 ctx["daylight_remaining"] = st.session_state.latest_weather.get("daylight_remaining")
                 
            if "latest_crowd" in st.session_state:
                 ctx["crowd"] = st.session_state.latest_crowd
                
            warnings = de.get_safety_warnings(ctx)
            suggestions = de.generate_plan_suggestions(ctx)
            
            st.session_state.latest_warnings = warnings
            st.session_state.latest_suggestions = suggestions
            
            status.update(label="Agent Consensus Reached!", state="complete", expanded=False)
    
        # Determine if we should use Recommendation Agent (JSON mode)
        use_json_mode = bool(st.session_state.profile.get("destination"))
        
        if use_json_mode:
            # Use the specialized agent with ALL available intel
            try:
                # Gather ALL Intel
                user_context = st.session_state.profile
                risk_assessment = st.session_state.get("latest_risk", {})
                weather_intel = st.session_state.get("latest_weather", {})
                news_intel = st.session_state.get("latest_news_intel", {})
                suggestions = st.session_state.get("latest_suggestions", [])
                
                # Deep Intelligence (now connected!)
                budget_intel = st.session_state.get("latest_budget")
                cultural_intel = st.session_state.get("latest_culture")
                health_intel = st.session_state.get("latest_health")
                sustainability_intel = st.session_state.get("latest_sustainability")
                itinerary = st.session_state.get("latest_itinerary")
                
                # Get latest user query
                user_query = st.session_state.messages[-1]["content"]
                
                # Generate Recommendation with ALL intel synthesized
                rec_agent = RecommendationAgent(st.session_state.groq_client)
                
                # DEBUG: Check Itinerary Source
                if itinerary:
                    print(f"DEBUG: Itinerary keys passed to RecAgent: {list(itinerary.keys())}")
                    # st.toast(f"Debug: Sending {len([k for k in itinerary.keys() if k.startswith('day_')])} days to AI")

                reply_data = rec_agent.generate_recommendation(
                    user_context, 
                    risk_assessment, 
                    weather_intel, 
                    news_intel, 
                    suggestions,
                    user_query=user_query,
                    budget_intel=budget_intel,
                    cultural_intel=cultural_intel,
                    health_intel=health_intel,
                    sustainability_intel=sustainability_intel,
                    itinerary=itinerary,
                    conversation_history=st.session_state.get("messages")
                )
                
                # Store structured data
                st.session_state.messages.append({"role": "assistant", "content": reply_data})
                st.rerun()
                
            except Exception as e:
                st.error(f"Agent Error: {e}")
                # Fallback to simple chat if agent fails
                use_json_mode = False
    
        if not use_json_mode:
            # Fallback / General Chat (Raw LLM)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            # Add context summary
            if "latest_risk" in st.session_state:
                messages.append({"role": "system", "content": f"Risk Context: {st.session_state.latest_risk}"})
                
            # Add Deep Intelligence to context
            if "latest_budget" in st.session_state:
                messages.append({"role": "system", "content": f"Budget Analysis: {st.session_state.latest_budget}"})
            if "latest_culture" in st.session_state:
                messages.append({"role": "system", "content": f"Cultural Tips: {st.session_state.latest_culture}"})
                
            for m in st.session_state.messages:
                # If historical message is a Dict (from Agent), convert to string for context
                if isinstance(m["content"], dict):
                    content_str = json.dumps(m["content"])
                else:
                    content_str = m["content"]
                messages.append({"role": m["role"], "content": content_str})
    
            llm_params = {
                "model": get_active_model_id(),
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 1024
            }
            
            res = client.chat.completions.create(**llm_params)
            reply = res.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()
            
    except Exception as e:
        status.update(label="Mission Failed", state="error", expanded=True)
        st.error(f"⚠️ **Mission Critical Error**: {str(e)}")
        st.info("The system has encountered an unexpected error. Please try resetting the mission.")
        print(f"CRITICAL ERROR: {e}") # Log to console


# ================= SHOW SMART CHIPS AFTER BOT REPLY =================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    update_suggestion_cache(st.session_state.messages)
    
    # Render Interactive Quick Replies
    if st.session_state.get("current_chips"):
        st.markdown("<div style='margin-bottom: 8px;'><em style='color:#94a3b8;'>✨ Quick Ideas:</em></div>", unsafe_allow_html=True)
        all_suggestions = []
        if isinstance(st.session_state.current_chips, dict):
            for items in st.session_state.current_chips.values():
                if isinstance(items, list):
                    all_suggestions.extend(items)
        elif isinstance(st.session_state.current_chips, list):
            all_suggestions.extend(st.session_state.current_chips)
        
        # Filter explicitly to 6 elements max and display dynamically
        all_suggestions = all_suggestions[:6]
        if all_suggestions:
            cols = st.columns(3 if len(all_suggestions) >= 3 else len(all_suggestions))
            for idx, sug in enumerate(all_suggestions):
                with cols[idx % 3]:
                    if st.button(sug, key=f"quick_sug_{idx}_{hash(sug)}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": sug})
                        st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)


    # ================= DEEP INTELLIGENCE TABS =================
    if "latest_budget" in st.session_state:
        st.markdown("<div class='intel-section-title'>🧠 Deep Intelligence</div>", unsafe_allow_html=True)
        tab_budget, tab_culture, tab_health, tab_stays, tab_eco, tab_packing, tab_food, tab_jetlag, tab_dna, tab_trends = st.tabs(["💰 Budget", "🎭 Culture", "🏥 Health", "🏨 Stays & Eats", "🌿 Eco", "🎒 Packing", "🍜 Food", "🧳 Jet Lag", "📊 Trip DNA", "🔥 Trends"])
        
        with tab_budget:
            b_data = st.session_state.latest_budget
            if b_data and not b_data.get("error"):
                # Feasibility badge
                feasibility = b_data.get("feasibility", "Unknown")
                badge_class = "safe" if feasibility.lower() in ["feasible", "comfortable", "easy"] else "warning" if feasibility.lower() in ["tight", "moderate"] else "danger"
                
                st.markdown(textwrap.dedent(f"""
                    <div class='intel-card'>
                        <div class='intel-card-title'>Budget Overview</div>
                        <div class='intel-metric-row'>
                            <div class='intel-metric'>
                                <div class='intel-metric-value'>{b_data.get("daily_needed", "--")}</div>
                                <div class='intel-metric-label'>Est. Daily Cost</div>
                            </div>
                            <div class='intel-metric'>
                                <div class='intel-metric-value'><span class='intel-badge {badge_class}'>{feasibility}</span></div>
                                <div class='intel-metric-label'>Feasibility</div>
                            </div>
                        </div>
                    </div>"""), unsafe_allow_html=True)
                
                # Breakdown as styled cards
                breakdown = b_data.get("breakdown", {})
                if breakdown:
                    items_html = ""
                    icons = {"accommodation": "🏨", "food": "🍽️", "transport": "🚕", "activities": "🎯", "shopping": "🛍️", "misc": "📦"}
                    for k, v in breakdown.items():
                        icon = icons.get(k.lower(), "💸")
                        items_html += f"<div class='intel-list-item'><span class='intel-list-icon'>{icon}</span><span><strong>{k.title()}:</strong> {v}</span></div>"
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Cost Breakdown</div>{items_html}</div>", unsafe_allow_html=True)
                
                # Tips
                tips = b_data.get("tips", [])
                if tips:
                    tips_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>💡</span><span>{tip}</span></div>" for tip in tips])
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Saving Tips</div>{tips_html}</div>", unsafe_allow_html=True)
            else:
                st.info("Budget analysis unavailable.")
                
        with tab_culture:
            c_data = st.session_state.latest_culture
            if c_data and not c_data.get("error"):
                # Etiquette Card
                dos_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>✅</span><span>{do}</span></div>" for do in c_data.get("etiquette_dos", [])])
                donts_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>❌</span><span>{dont}</span></div>" for dont in c_data.get("etiquette_donts", [])])
                st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Etiquette Guide</div>{dos_html}{donts_html}</div>", unsafe_allow_html=True)
                
                # Dress Code & Tipping
                dress = c_data.get('dress_code', 'Standard')
                tipping = c_data.get('tipping_guide', 'Standard')
                if isinstance(tipping, dict):
                    tipping_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>💸</span><span><strong>{k.title()}:</strong> {v}</span></div>" for k, v in tipping.items()])
                else:
                    tipping_html = f"<div class='intel-list-item'><span class='intel-list-icon'>💸</span><span>{tipping}</span></div>"
                
                st.markdown(textwrap.dedent(f"""
                    <div class='intel-card'>
                        <div class='intel-card-title'>Essentials</div>
                        <div class='intel-list-item'><span class='intel-list-icon'>👕</span><span><strong>Dress Code:</strong> {dress}</span></div>
                        {tipping_html}
                    </div>"""), unsafe_allow_html=True)
                    
                # Local Laws
                if "local_laws" in c_data:
                    laws_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>⚠️</span><span>{law}</span></div>" for law in c_data["local_laws"]])
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Local Laws & Customs</div>{laws_html}</div>", unsafe_allow_html=True)
            else:
                st.info("Cultural intelligence unavailable.")

        with tab_health:
            h_data = st.session_state.latest_health
            if h_data and not h_data.get("error"):
                # Water Safety Badge
                water = h_data.get('water_safety', 'Check locally')
                water_class = "safe" if "safe" in water.lower() else "warning" if "caution" in water.lower() or "boil" in water.lower() else "danger"
                st.markdown(textwrap.dedent(f"""
                    <div class='intel-card'>
                        <div class='intel-card-title'>Water & Food Safety</div>
                        <div class='intel-list-item'><span class='intel-list-icon'>💧</span><span><strong>Water:</strong> <span class='intel-badge {water_class}'>{water}</span></span></div>
                    </div>"""), unsafe_allow_html=True)
                
                # Vaccinations
                vacc_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>💉</span><span>{v}</span></div>" for v in h_data.get("vaccinations", [])])
                pharmacy = h_data.get('pharmacy_tips', '')
                if vacc_html or pharmacy:
                    st.markdown(textwrap.dedent(f"""
                        <div class='intel-card'>
                            <div class='intel-card-title'>Vaccinations & Meds</div>
                            {vacc_html}
                            {"<div class='intel-list-item'><span class='intel-list-icon'>💊</span><span>" + pharmacy + "</span></div>" if pharmacy else ""}
                        </div>"""), unsafe_allow_html=True)
                    
                # Emergency Numbers
                if "emergency_numbers" in h_data:
                    nums = h_data["emergency_numbers"]
                    nums_html = ""
                    if isinstance(nums, dict):
                        for k, v in nums.items():
                            nums_html += f"<div class='intel-list-item'><span class='intel-list-icon'>📞</span><span><strong>{k.title()}:</strong> {v}</span></div>"
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Emergency Numbers</div>{nums_html}</div>", unsafe_allow_html=True)
            else:
                st.info("Health intelligence unavailable.")

        with tab_stays:
             # Logic to show detailed options (Hotels/Cafes) from Decision Engine or Agent
             # We check the latest recommendation for 'detailed_options'
             found_options = False
             
             # Check distinct session state storage first
             if "latest_options" in st.session_state:
                 options = st.session_state.latest_options
                 if options:
                     found_options = True
                     st.write("**🏨 Recommended Stays & Eats**")
                     cols = st.columns(2)
                     for i, opt in enumerate(options):
                         with cols[i % 2]:
                            st.markdown(render_travel_card({
                                "title": opt.get('title'),
                                "description": opt.get('description'),
                                "cost": opt.get('cost'),
                                "rating": opt.get('rating'),
                                "tags": ["Deep Intel"]
                            }), unsafe_allow_html=True)
             
             if not found_options:
                 st.info("No specific detailed options in this plan. Ask 'Show hotels' for more.")

        with tab_eco:
            e_data = st.session_state.latest_sustainability
            if e_data and not e_data.get("error"):
                green = e_data.get('green_rating', 'Moderate')
                green_class = "safe" if green.lower() in ["high", "excellent", "good"] else "warning"
                st.markdown(f"""<div class='intel-card'>
                    <div class='intel-card-title'>Sustainability Overview</div>
                    <div class='intel-metric-row'>
                        <div class='intel-metric'>
                            <div class='intel-metric-value'>{e_data.get("carbon_footprint_est", "--")}</div>
                            <div class='intel-metric-label'>Carbon Footprint</div>
                        </div>
                        <div class='intel-metric'>
                            <div class='intel-metric-value'><span class='intel-badge {green_class}'>{green}</span></div>
                            <div class='intel-metric-label'>Green Rating</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
                
                transport_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>🚲</span><span>{t}</span></div>" for t in e_data.get("eco_transport", [])])
                if transport_html:
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Eco-Friendly Transport</div>{transport_html}</div>", unsafe_allow_html=True)
                    
                practices_html = "".join([f"<div class='intel-list-item'><span class='intel-list-icon'>♻️</span><span>{p}</span></div>" for p in e_data.get("sustainable_practices", [])])
                if practices_html:
                    st.markdown(f"<div class='intel-card'><div class='intel-card-title'>Sustainable Practices</div>{practices_html}</div>", unsafe_allow_html=True)
            else:
                st.info("Sustainability intelligence unavailable.")

        with tab_packing:

            p_list = st.session_state.get("latest_packing")
            
            if p_list and not p_list.get("error"):
                # Must Haves
                if "must_haves" in p_list:
                    st.info(f"**⚠️ Non-Negotiables:** {', '.join(p_list['must_haves'])}")
                
                # Render Categorized Checklist
                cats = p_list.get("categories", {})
                for category, items in cats.items():
                    with st.expander(f"**{category}**", expanded=False):
                        for item in items:
                            st.checkbox(item, key=f"pack_{category}_{item}")
            else:
                 st.info("Packing list unavailable. Try planning a trip first.")
                
        with tab_food:
            dest = st.session_state.profile.get("destination")
            if dest:
                if st.session_state.get("food_intel") and st.session_state.get("food_dest") == dest:
                    food = st.session_state.food_intel
                    
                    # Seasonal Dishes
                    dishes = food.get("seasonal_dishes", [])
                    if dishes:
                        st.markdown("<div class='intel-card'><div class='intel-card-title'>🍽️ Seasonal Dishes</div>", unsafe_allow_html=True)
                        for d in dishes:
                            st.markdown(textwrap.dedent(f"""
                            <div class='intel-list-item'>
                                <span class='intel-list-icon'>🍜</span>
                                <span><strong>{d.get('name','')}</strong> — {d.get('description','')}
                                <br/><span style='font-size:0.72rem;color:#64748b;'>📍 {d.get('where_to_try','')} | {d.get('price_range','')}</span></span>
                            </div>"""), unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Trending Restaurants
                    restos = food.get("trending_restaurants", [])
                    if restos:
                        st.markdown("<div class='intel-card'><div class='intel-card-title'>🔥 Trending Restaurants</div>", unsafe_allow_html=True)
                        for r in restos:
                            st.markdown(textwrap.dedent(f"""
                            <div class='intel-list-item'>
                                <span class='intel-list-icon'>🍴</span>
                                <span><strong>{r.get('name','')}</strong> ({r.get('cuisine','')})
                                <br/><span style='font-size:0.72rem;color:#f43f5e;'>{r.get('why_trending','')}</span></span>
                            </div>"""), unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Street Food
                    street = food.get("street_food", [])
                    if street:
                        st.markdown("<div class='intel-card'><div class='intel-card-title'>🛒 Street Food</div>", unsafe_allow_html=True)
                        for s in street:
                            must = "⭐ " if s.get("must_try") else ""
                            st.markdown(textwrap.dedent(f"""
                            <div class='intel-list-item'>
                                <span class='intel-list-icon'>{must}🥡</span>
                                <span><strong>{s.get('name','')}</strong> — {s.get('area','')} ({s.get('price','')})</span>
                            </div>"""), unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Food Neighborhoods
                    hoods = food.get("food_neighborhoods", [])
                    if hoods:
                        for h in hoods:
                            st.info(f"📍 **{h.get('name','')}** — Known for: {h.get('known_for','')} | Vibe: _{h.get('vibe','')}_")
                else:
                    if st.button("🍜 Load Food Intel", use_container_width=True, key="food_btn"):
                        with st.spinner("Scouting the food scene..."):
                            food_agent = FoodAgent(st.session_state.groq_client)
                            import datetime as _dt
                            month = _dt.datetime.now().strftime("%B")
                            result = food_agent.get_food_intel(dest, month)
                            st.session_state.food_intel = result
                            st.session_state.food_dest = dest
                            st.rerun()
            else:
                st.info("Set a destination to discover its food scene!")

        with tab_jetlag:
            dest = st.session_state.profile.get("destination")
            if dest:
                if st.session_state.get("jetlag_plan") and st.session_state.get("jetlag_dest") == dest:
                    plan = st.session_state.jetlag_plan
                    
                    severity = plan.get("severity", "Unknown")
                    sev_color = "#22c55e" if severity == "Mild" else "#f59e0b" if severity == "Moderate" else "#ef4444"
                    
                    st.markdown(textwrap.dedent(f"""
                    <div class='intel-card'>
                        <div class='intel-card-title'>🧳 Jet Lag Recovery Plan</div>
                        <div class='intel-metric-row'>
                            <div class='intel-metric'>
                                <div class='intel-metric-value'>{plan.get('timezone_difference','--')}</div>
                                <div class='intel-metric-label'>Time Diff</div>
                            </div>
                            <div class='intel-metric'>
                                <div class='intel-metric-value'><span class='intel-badge' style='background:{sev_color};color:#fff;'>{severity}</span></div>
                                <div class='intel-metric-label'>Severity</div>
                            </div>
                            <div class='intel-metric'>
                                <div class='intel-metric-value'>{plan.get('recovery_days','--')}</div>
                                <div class='intel-metric-label'>Recovery Days</div>
                            </div>
                        </div>
                    </div>
                    """), unsafe_allow_html=True)
                    
                    # Pre-flight
                    pre = plan.get("pre_flight", [])
                    if pre:
                        with st.expander("✈️ Pre-Flight Prep", expanded=False):
                            for p in pre:
                                st.markdown(f"**{p.get('day','')}**")
                                st.markdown(f"😴 {p.get('sleep_advice','')}")
                                st.markdown(f"☕ {p.get('caffeine','')}")
                                st.markdown(f"☀️ {p.get('light','')}")
                                st.divider()
                    
                    # Post-arrival
                    post = plan.get("post_arrival", [])
                    if post:
                        with st.expander("🛬 Post-Arrival Schedule", expanded=True):
                            for p in post:
                                st.markdown(f"**{p.get('day','')}** — Wake: {p.get('wake_time','')} | Sleep: {p.get('sleep_time','')}")
                                st.markdown(f"☕ Caffeine: {p.get('caffeine_window','')} | 🏃 {p.get('activity','')}")
                                st.caption(f"💡 {p.get('key_tip','')}")
                                st.divider()
                    
                    # Quick Tips
                    tips = plan.get("quick_tips", [])
                    if tips:
                        for t in tips:
                            st.success(f"💡 {t}")
                else:
                    origin = st.text_input("Your origin city:", placeholder="Mumbai", key="jetlag_origin")
                    if st.button("🧳 Generate Jet Lag Plan", use_container_width=True, key="jetlag_btn"):
                        if origin:
                            with st.spinner("Calculating recovery plan..."):
                                result = generate_jetlag_plan(st.session_state.groq_client, origin, dest)
                                st.session_state.jetlag_plan = result
                                st.session_state.jetlag_dest = dest
                                st.rerun()
                        else:
                            st.warning("Enter your origin city!")
            else:
                st.info("Set a destination to get your jet lag recovery plan!")

        with tab_dna:
            if st.session_state.get("trip_dna_data"):
                st.markdown(render_trip_dna_html(st.session_state.trip_dna_data), unsafe_allow_html=True)
            else:
                if st.button("📊 Analyze My Trip DNA", use_container_width=True, key="dna_btn"):
                    with st.spinner("Analyzing your travel personality..."):
                        result = generate_trip_dna(
                            st.session_state.groq_client,
                            st.session_state.profile,
                            st.session_state.get("latest_itinerary")
                        )
                        st.session_state.trip_dna_data = result
                        st.rerun()

        # --- Deep Research Agent --- #
        with st.expander("🧠 Deep Research Agent (Autonomous)", expanded=False):
            st.markdown("Ask complex questions. The Agent will search, read, and search again until it finds the answer.")
            
            research_query = st.text_area("What do you want to research?", placeholder="e.g. Find the latest hidden gems in Kyoto for 2025, considering I am traveling with a toddler.", key="research_query_input")
            
            if st.button("🔍 Run Autonomous Research", type="primary", use_container_width=True, key="run_research_btn"):
                if research_query:
                    # Execute Deep Research using Orchestrator
                    with st.spinner("🧠 Autonomous Agent is thinking..."):
                        result = st.session_state.orchestrator.deep_research(research_query, st.session_state.profile)
                        st.session_state.latest_research = result
                else:
                    st.warning("Please enter a research topic.")
                    
            if st.session_state.get("latest_research"):
                res = st.session_state.latest_research
                if "error" in res:
                    st.error(f"Research failed: {res['error']}")
                else:
                    st.success(f"✅ Research completed in {res.get('iterations_used', 1)} thinking steps.")
                    
                    st.markdown("### 💡 Agent's Thought Process")
                    for idx, t in enumerate(res.get('thoughts', [])):
                         st.markdown(f"""
                         <div style="background:rgba(255,255,255,0.05); padding:8px; border-radius:5px; margin-bottom:5px; border-left:3px solid #00f2fe; font-size: 0.9em; font-family: monospace;">
                             [{idx+1}] {t}
                         </div>
                         """, unsafe_allow_html=True)
                         
                    st.markdown("### 📄 Final Research Report")
                    st.markdown(res.get('report', 'No report generated.'))


        with tab_trends:
             if "live_pulse_intel" in st.session_state:
                 pulse = st.session_state.live_pulse_intel
                 trends = pulse.get("trends", [])
                 
                 if trends:
                     st.subheader("🔥 Viral & Hidden Gems")
                     st.caption("Fresh from travel blogs & social discussions (Last 3 months)")
                     
                     for item in trends:
                          st.markdown(f"""
<div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:10px; margin-bottom:10px; border-left:3px solid #f43f5e;">
    <div style="font-weight:bold; color:#f43f5e; font-size:1.1rem;">{item.get('name', 'Unknown Spot')} <span style="font-size:0.8rem; color:#fff; background:#f43f5e; padding:2px 8px; border-radius:10px;">{item.get('category', 'Spot')}</span></div>
    <div style="color:#e2e8f0; margin-top:4px;">{item.get('reason', 'Trending now.')}</div>
</div>
""", unsafe_allow_html=True)
                 else:
                     st.info("No specific trending gems found right now.")
             else:
                 st.info("Plan a trip to see live trends!")
                
    # ================= MULTI-DAY ITINERARY =================
    if "latest_itinerary" in st.session_state and st.session_state.latest_itinerary:
        itin = st.session_state.latest_itinerary
        if not itin.get("error"):
            st.markdown("<div class='intel-section-title'>📅 Multi-Day Itinerary</div>", unsafe_allow_html=True)
            
            # 🔄 LIVE REPLAN ENGINE
            with st.expander("🔄 Live Replan Engine", expanded=False):
                st.caption("Plans changed? Regenerate your itinerary from any day onward.")
                day_keys = [k for k in itin.keys() if k.startswith("day_")]
                total_days = len(day_keys)
                
                replan_col1, replan_col2 = st.columns([1, 2])
                replan_from = replan_col1.number_input(
                    "Replan from Day", min_value=1, max_value=max(total_days, 1), value=1, key="replan_day"
                )
                replan_reason = replan_col2.text_input(
                    "Reason", placeholder="Heavy rain forecast / Museum closed / Want more food options",
                    key="replan_reason"
                )
                
                if st.button("🔄 Replan Remaining Days", use_container_width=True, key="replan_btn"):
                    if replan_reason:
                        dest = st.session_state.profile.get("destination", "")
                        with st.spinner(f"🔄 Replanning Day {replan_from}+ because: {replan_reason}..."):
                            new_itin = st.session_state.orchestrator.replan_remaining(
                                dest,
                                st.session_state.profile,
                                itin,
                                replan_from,
                                replan_reason,
                                current_intel={
                                    "weather_intel": st.session_state.get("latest_weather"),
                                    "risk_assessment": st.session_state.get("latest_risk"),
                                }
                            )
                            st.session_state.latest_itinerary = new_itin
                            st.rerun()
                    else:
                        st.warning("Tell me why you're replanning!")
            
            # Sort keys to ensure day_1, day_2 order
            # Natural Sort for Day Keys (day_1, day_2, ... day_10)
            day_keys = [k for k in itin.keys() if k.startswith("day_")]
            sorted_days = sorted(day_keys, key=lambda x: int(x.split("_")[-1]) if x.split("_")[-1].isdigit() else 999)
            
            if sorted_days:
                # Tabs Layout for Multi-Day
                tab_labels = []
                for k in sorted_days:
                    label = k.replace("_", " ").title()
                    if itin[k].get("replanned"):
                        label = f"🔄 {label}"
                    tab_labels.append(label)
                tabs = st.tabs(tab_labels)
                
                for i, day_key in enumerate(sorted_days):
                    with tabs[i]:
                        day_data = itin[day_key]
                        
                        # Replan badge
                        if day_data.get("replanned"):
                            st.markdown(f"""
                            <div style="background:rgba(34,211,238,0.1);border:1px solid rgba(34,211,238,0.3);border-radius:8px;
                                        padding:6px 12px;margin-bottom:8px;font-size:0.8rem;color:#22d3ee;">
                                🔄 <strong>Replanned</strong> — {day_data.get('replan_reason','')}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"<div class='itin-day-header'>{day_data.get('title', f'Day {i+1}')}</div>", unsafe_allow_html=True)

                        
                        # Time slot definitions
                        slots = [
                            ("morning", "🌅", "Morning", day_data.get('morning', '')),
                            ("lunch", "🍽️", "Lunch", day_data.get('lunch', '')),
                            ("afternoon", "☀️", "Afternoon", day_data.get('afternoon', '')),
                            ("evening", "🌙", "Evening", day_data.get('evening', '')),
                        ]
                        
                        slot_colors = {"morning": "#fbbf24", "lunch": "#f97316", "afternoon": "#60a5fa", "evening": "#a78bfa"}
                        
                        for slot_class, icon, label, content in slots:
                            if not content:
                                continue
                            
                            color = slot_colors.get(slot_class, "#00f2fe")
                            
                            # Handle structured slot objects (new format) vs plain strings (legacy)
                            if isinstance(content, dict):
                                activity = content.get("activity", "")
                                location = content.get("location", "")
                                duration = content.get("duration", "")
                                cost = content.get("cost", "")
                                transport = content.get("transport", "")
                                insider_tip = content.get("insider_tip", "")
                                
                                # Build badge row
                                badges_html = ""
                                if location:
                                    badges_html += f"<span style='background:rgba(255,255,255,0.06);color:#94a3b8;font-size:0.65rem;padding:2px 7px;border-radius:8px;margin-right:6px;'>📍 {location}</span>"
                                if duration:
                                    badges_html += f"<span style='background:rgba(255,255,255,0.06);color:#94a3b8;font-size:0.65rem;padding:2px 7px;border-radius:8px;margin-right:6px;'>⏱️ {duration}</span>"
                                if cost:
                                    badges_html += f"<span style='background:rgba(0,242,254,0.12);color:#00f2fe;font-size:0.65rem;padding:2px 7px;border-radius:8px;font-weight:600;'>💰 {cost}</span>"
                                
                                # Transport line
                                transport_html = f"<div style='margin-top:6px;font-size:0.72rem;color:#64748b;'><span style='color:#38bdf8;'>🚶</span> {transport}</div>" if transport else ""
                                
                                # Insider tip
                                tip_html = f"<div style='margin-top:6px;font-size:0.73rem;color:#a78bfa;font-style:italic;border-left:2px solid rgba(167,139,250,0.3);padding-left:8px;'>💡 {insider_tip}</div>" if insider_tip else ""
                                
                                st.markdown(f"""<div style='
                                    background: linear-gradient(145deg, rgba(15,23,42,0.8), rgba(15,23,42,0.4));
                                    border: 1px solid rgba(255,255,255,0.06);
                                    border-left: 3px solid {color};
                                    border-radius: 12px;
                                    padding: 14px 16px;
                                    margin-bottom: 10px;
                                '>
                                    <div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>
                                        <span style='font-size:22px;'>{icon}</span>
                                        <span style='font-size:0.72rem;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;color:{color};'>{label}</span>
                                    </div>
                                    <div style='font-size:0.88rem;color:#e2e8f0;line-height:1.6;margin-bottom:8px;'>{activity}</div>
                                    <div style='display:flex;flex-wrap:wrap;gap:4px;'>{badges_html}</div>
                                    {transport_html}
                                    {tip_html}
                                </div>""", unsafe_allow_html=True)
                            else:
                                # Legacy plain string format
                                st.markdown(f"""<div class='itin-slot'>
                                    <div class='itin-slot-icon {slot_class}'>{icon}</div>
                                    <div class='itin-slot-body'>
                                        <div class='itin-slot-time {slot_class}'>{label}</div>
                                        <div class='itin-slot-desc'>{content}</div>
                                    </div>
                                </div>""", unsafe_allow_html=True)
                        
                        # Day-level summary: cost, safety, group tip, backup plan
                        est_cost = day_data.get('estimated_cost', '')
                        safety_note = day_data.get('safety_note', '')
                        group_tip = day_data.get('group_tip', '')
                        backup_plan = day_data.get('backup_plan', '')
                        
                        footer_parts = []
                        if est_cost:
                            footer_parts.append(f"💰 **Day Budget**: {est_cost}")
                        if safety_note and safety_note.lower() not in ['all clear', 'none', '', 'n/a']:
                            footer_parts.append(f"⚠️ **Safety**: {safety_note}")
                        elif safety_note:
                            footer_parts.append(f"✅ **Safety**: {safety_note}")
                        if group_tip:
                            footer_parts.append(f"👥 **Tip**: {group_tip}")
                        if backup_plan:
                            footer_parts.append(f"🔄 **Backup Plan**: {backup_plan}")
                        
                        if footer_parts:
                            st.markdown("---")
                            for fp in footer_parts:
                                st.markdown(fp)
        else:
            st.error(f"Itinerary Generation Error: {itin.get('error')}")
            
        # Itinerary Map
        if "destination" in st.session_state.profile:
            dest = st.session_state.profile["destination"]
            dest_coords = None
            
            # Try to get coords from cache or geocode
            from utils.geocode import geocode_location
            from utils.cache_manager import get_cache
            
            cache = get_cache()
            cached = cache.get("geocode", dest)
            if cached:
                dest_coords = cached
            else:
                try:
                    dest_coords = geocode_location(dest)
                    if dest_coords:
                        cache.set("geocode", dest, dest_coords)
                except:
                    pass
            
            if dest_coords:
                with st.expander("🗺️ Itinerary Map", expanded=False):
                    num_days = len([k for k in itin.keys() if k.startswith("day_")])
                    if num_days > 0:
                        itin_map = create_itinerary_map(dest_coords, dest, num_days)
                        render_map_in_streamlit(itin_map, height=350)
                
    # Show map if destination is set
    if st.session_state.profile.get("destination"):
        with st.expander("🗺️ View Destination Map", expanded=False):
            dest = st.session_state.profile["destination"]
            
            # Get location coordinates if available
            loc = st.session_state.get("current_location", {})
                   
            if loc and loc.get("lat") and loc.get("lon"):
                # POI Toggles
                st.markdown("##### 📍 Points of Interest")
                poi_options = ["Sightseeing", "Food", "Relax", "Pharmacies", "ATMs"]
                selected_pois = st.multiselect("Show on map:", poi_options, default=["Sightseeing"])
                
                pois_data = {}
                if selected_pois:
                    from utils.nearby_places import get_nearby_places, get_utility_places
                    lat, lon = loc["lat"], loc["lon"]
                    
                    with st.spinner("Fetching POIs..."):
                        if "Sightseeing" in selected_pois:
                            pois_data["Sightseeing"] = get_nearby_places(lat, lon, limit=5, pace="Moderate")
                        if "Food" in selected_pois:
                             # Use nearby places with specific category filtering if possible, or just general for now
                             # For simplicity, we'll map Food to amenity=restaurant/cafe in get_nearby_places if we modify it, 
                             # or just call it and filter. 
                             # Current get_nearby_places returns mixed. Let's make a specific call for Food if we want, 
                             # or just accept that "Sightseeing" covers tourism/leisure and we need a new function for Food.
                             # Let's use get_utility_places logic but for food? No, get_utility is specific.
                             # Let's use get_nearby_places but filter for food.
                             # Actually `get_nearby_places` in utils/nearby_places.py fetches tourism, amenity, leisure. 
                             # It categorizes them. We can filter the result of ONE call?
                             # For now, let's just call get_utility_places for known utilities and get_nearby_places for general.
                             pass
                        
                        if "Pharmacies" in selected_pois:
                             pois_data["Pharmacies"] = get_utility_places(lat, lon, "pharmacy")
                        if "ATMs" in selected_pois:
                             pois_data["ATMs"] = get_utility_places(lat, lon, "atm")

                # Create a simple destination map
                locations = [{
                    "coords": (loc["lat"], loc["lon"]),
                    "name": dest,
                    "description": f"Your travel destination: {dest}"
                }]
                
                dest_map = create_destination_map(locations, pois=pois_data, zoom_start=12)
                if dest_map:
                    render_map_in_streamlit(dest_map, height=350)
            else:
                st.info(f"📍 Destination: {dest}. Enable location services for map view.")
    
    # PDF Export Button
    last_msg = st.session_state.messages[-1]["content"]
    
    # Only show if we have substantial content (not just questions)
    if len(last_msg) > 100:
        st.markdown("---")
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
             if st.button("📸 Send AI Postcard", use_container_width=True):
                 from utils.postcard_generator import generate_postcard_html, get_ai_postcard_message
                 dest = st.session_state.profile.get("destination", "WanderX")
                 
                 with st.spinner("Designing your postcard..."):
                     # Generate message
                     try:
                         # Use existing client if available in scope or create new
                         # Assuming client is initialized in main app scope or we re-init
                         from groq import Groq
                         client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                         msg = get_ai_postcard_message(client, dest)
                     except:
                         msg = None
                     
                     html_code = generate_postcard_html(dest, message=msg)
                     st.session_state.latest_postcard = html_code
                     st.success("Postcard Created! Scroll down.")

        with col2:
            if st.button("📄 Download PDF", type="primary", use_container_width=True):
                try:
                    # Import the PDF generator
                    from utils.pdf_generator import generate_itinerary_pdf
                    
                    pdf_buffer = generate_itinerary_pdf(
                        profile=st.session_state.profile,
                        itinerary_text=last_msg,
                        weather_context=st.session_state.get("latest_weather", {}).get("weather_data", {}),
                        budget_intel=st.session_state.get("latest_budget"),
                        cultural_intel=st.session_state.get("latest_culture"),
                        health_intel=st.session_state.get("latest_health"),
                        sustainability_intel=st.session_state.get("latest_sustainability")
                    )
                    
                    st.download_button(
                        label="⬇️ Save Travel Dossier",
                        data=pdf_buffer,
                        file_name=f"wandertrip_{st.session_state.profile.get('destination', 'itinerary').replace(' ', '_').lower()}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")

    # Display Postcard if available
    if "latest_postcard" in st.session_state:
        st.markdown("### 💌 Your Travel Postcard")
        st.components.v1.html(st.session_state.latest_postcard, height=450, scrolling=False)
        if st.button("❌ Close Postcard"):
            del st.session_state.latest_postcard
            st.rerun()


