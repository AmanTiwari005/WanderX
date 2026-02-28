import streamlit as st
import re
import requests

def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error loading lottie animation from {url}: {e}")
        return None


def get_design_tokens():
    """
    Returns the core CSS variables and design tokens for the application.
    Computed here to be injected into the app's style block.
    """
    return """
    :root {
        /* Dark SaaS Palette */
        --primary: #00f2fe;  /* Cyan Neon */
        --secondary: #4facfe; /* Blue Neon */
        --accent: #ff0055;    /* Pink Neon */
        --bg-dark: #02050a;   /* Deep Space Black */
        --bg-card: rgba(15, 23, 42, 0.6);
        --glass: rgba(15, 23, 42, 0.8);
        --glass-border: rgba(255, 255, 255, 0.08);
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        
        /* Spacing */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 48px;
        
        /* Typography */
        --font-main: 'Inter', sans-serif;
    }
    """

def minify_html(html_str):
    """
    Removes newlines and extra spaces to prevent Streamlit from interpreting
    indented HTML as code blocks.
    """
    return re.sub(r'\s+', ' ', html_str).strip()

import textwrap

def render_travel_card(data):
    """
    Renders a modern, image-free travel card with focus on typography and tags.
    """
    title = data.get('title', 'Recommendation')
    desc = data.get('description', 'No description available.')
    cost = data.get('cost', 'Price varies')
    rating = data.get('rating', 'New')
    tags = data.get('tags', [])
    
    tags_html = "".join([f"<span class='card-tag'>{tag}</span>" for tag in tags])
    
    html = textwrap.dedent(f"""
    <div class="travel-card-modern">
        <div class="card-header-modern">
            <div class="card-title-row">
                <div class="card-title">{title}</div>
                <div class="card-rating">★ {rating}</div>
            </div>
            <div class="card-cost">{cost}</div>
        </div>
        <p class="card-desc">{desc}</p>
        <div class="card-tags">
            {tags_html}
        </div>
    </div>
    """)
    return minify_html(html)

def render_day_timeline(day_plan, day_num):
    """
    Renders a sleek, vertical connected-step timeline for a SINGLE day.
    Enhanced to support rich metadata (Cost, Location, Highlights).
    """
    if not day_plan:
        return ""
        
    activities = day_plan.get('activities', [])
    acts_html = ""
    for i, act in enumerate(activities):
        time = act.get('time', 'Anytime')
        title = act.get('title', 'Activity')
        desc = act.get('description', '')
        
        # Rich Metadata
        cost = act.get('cost', '') or act.get('cost_estimate', '')
        loc = act.get('location', '')
        highlight = act.get('highlight', '')
        
        meta_html = ""
        if cost: 
            meta_html += f"<span style='background:rgba(0,242,254,0.1);color:#00f2fe;font-size:10px;padding:2px 6px;border-radius:4px;margin-right:4px;'>💰 {cost}</span>"
        if loc: 
            meta_html += f"<span style='background:rgba(255,255,255,0.1);color:#adaeb0;font-size:10px;padding:2px 6px;border-radius:4px;'>📍 {loc}</span>"
            
        highlight_html = ""
        if highlight:
            highlight_html = f"<div style='margin-top:6px;font-size:11px;color:#a78bfa;font-style:italic;border-left:2px solid rgba(167,139,250,0.4);padding-left:8px;'>💡 {highlight}</div>"

        is_last = i == len(activities) - 1
        node_class = "timeline-node last" if is_last else "timeline-node"
        
        acts_html += f"""
        <div class="timeline-step">
            <div class="{node_class}"></div>
            <div class="timeline-content-modern">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span class="timeline-time-badge">{time}</span>
                    <div>{meta_html}</div>
                </div>
                <div class="timeline-step-title">{title}</div>
                <div class="timeline-step-desc">{desc}</div>
                {highlight_html}
            </div>
        </div>
        """
        
    html = textwrap.dedent(f"""
    <div class="day-section">
        <div class="day-badge">Day {day_num}</div>
        <div class="day-timeline">
            {acts_html}
        </div>
    </div>
    """)
    return minify_html(html)

def render_timeline(itinerary_data):
    """
    Renders the full multi-day itinerary by aggregating day timelines.
    Legacy wrapper for backward compatibility.
    """
    if not itinerary_data:
        return ""
        
    html = ""
    # itinerary_data is expected to be a list of day objects
    for day_plan in itinerary_data:
        day_num = day_plan.get('day', '?')
        html += render_day_timeline(day_plan, day_num)
        
    return f'<div class="modern-timeline-container">{html}</div>'

def render_smart_suggestion_sidebar(suggestions):
    """
    Renders suggestions vertically for the sidebar.
    """
    if not suggestions:
        return ""
        
    html = ""
    for cat, items in suggestions.items():
        is_tip = "Tip" in cat or "Trend" in cat
        icon = "💡" if "Tip" in cat else ("🔥" if "Trend" in cat else "✨")
        
        # Section Header
        html += f"<div style='font-size:12px; font-weight:600; color:var(--primary); margin:12px 0 4px 0; text-transform:uppercase;'>{icon} {cat}</div>"
        
        for item in items:
            style = "background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:8px; border-radius:8px; margin-bottom:6px; font-size:13px;"
            if is_tip:
                 style = "background:linear-gradient(90deg, rgba(255,215,0,0.1), transparent); border:1px solid rgba(255,215,0,0.2); padding:8px; border-radius:8px; margin-bottom:6px; font-size:13px;"
            
            html += f"""
            <div style="{style}">
                {item}
            </div>
            """
            
    return minify_html(html)

def render_smart_suggestion_carousel(suggestions):
    """
    Renders a horizontal scrolling carousel with special styling for Smart Tips.
    """
    if not suggestions:
        return ""
        
    slides_html = ""
    for cat, items in suggestions.items():
        is_tip = "Tip" in cat or "Trend" in cat
        style_class = "carousel-item tip-glow" if is_tip else "carousel-item"
        icon = "💡" if "Tip" in cat else ("🔥" if "Trend" in cat else "✨")
        
        for item in items:
            slides_html += f"""
            <div class="{style_class}">
                <div class="carousel-icon">{icon}</div>
                <div class="carousel-text">{item}</div>
                <div class="carousel-cat">{cat}</div>
            </div>
            """
            
    html = textwrap.dedent(f"""
    <div class="suggestion-carousel">
        {slides_html}
    </div>
    """)
    return minify_html(html)

def render_hero_card(data):
    """
    Renders a minimalist, premium hero-style recommendation card.
    Stripped of generic badges and clutter as requested.
    """
    title = data.get('title', 'Top Pick')
    
    html = textwrap.dedent(f"""
    <div class="hero-card" style="text-align: center; padding: 40px 20px;">
        <div class="hero-title" style="font-size: 32px; text-shadow: 0 4px 20px rgba(0,0,0,0.5); margin-bottom: 0;">{title}</div>
    </div>
    """)
    return minify_html(html)

def get_custom_css():
    """
    Returns the complete CSS block to be injected into Streamlit.
    Uses string concatenation (NOT f-strings) to avoid CSS brace conflicts.
    """
    tokens = get_design_tokens()

    static_css = """
        /* =================== GLOBAL =================== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        .stApp {
            background-color: #02050a;
            background-image:
                radial-gradient(circle at 10% 20%, rgba(112, 0, 255, 0.15) 0%, transparent 30%),
                radial-gradient(circle at 90% 80%, rgba(0, 229, 255, 0.15) 0%, transparent 30%),
                radial-gradient(circle at 50% 50%, rgba(255, 0, 110, 0.05) 0%, transparent 50%);
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
        }

        /* =================== ANIMATIONS =================== */
        @keyframes slideInUp {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInLeft {
            from { opacity: 0; transform: translateX(-30px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeInRight {
            from { opacity: 0; transform: translateX(30px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes scaleIn {
            from { opacity: 0; transform: scale(0.85); }
            to { opacity: 1; transform: scale(1); }
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        @keyframes pulseGlow {
            0% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0.4); }
            70% { box-shadow: 0 0 0 12px rgba(0, 242, 254, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0); }
        }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        @keyframes shimmer {
            0% { background-position: -200% center; }
            100% { background-position: 200% center; }
        }
        @keyframes borderGlow {
            0%, 100% { border-color: rgba(0, 242, 254, 0.1); }
            50% { border-color: rgba(0, 242, 254, 0.35); }
        }
        @keyframes breathe {
            0%, 100% { opacity: 0.7; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); }
        }
        @keyframes typeReveal {
            from { max-width: 0; }
            to { max-width: 100%; }
        }
        @keyframes countUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* =================== HERO LANDING =================== */
        .hero-landing {
            text-align: center;
            padding: 20px 0 40px 0;
            animation: slideInUp 0.8s ease-out;
        }
        
        /* =================== SIDEBAR & SAC =================== */
        /* Force the sidebar to drop its typical background where possible */
        [data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.5) !important;
            backdrop-filter: blur(12px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }

        /* Streamlit Option Menu custom injects */
        .nav-link { 
            border-radius: 8px !important;
            transition: all 0.3s ease;
        }
        
        /* Styling SAC Components */
        .stSegmentedControl {
            background-color: rgba(255, 255, 255, 0.03) !important;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px;
        }
        
        .sac-segmented { 
            /* SAC segmented style targets */
            --sac-segmented-bg: transparent; 
        }

        .hero-badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.15), rgba(79, 172, 254, 0.15));
            border: 1px solid rgba(0, 242, 254, 0.3);
            border-radius: 50px;
            padding: 8px 20px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #00f2fe;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }

        .gradient-headline {
            font-size: 3.5rem;
            font-weight: 900;
            line-height: 1.1;
            letter-spacing: -2px;
            background: linear-gradient(135deg, #ffffff 0%, #00f2fe 30%, #4facfe 60%, #ff0055 100%);
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 6s ease infinite;
            margin-bottom: 16px;
            padding: 0 20px;
        }

        .hero-subtitle {
            font-size: 1.15rem;
            color: #94a3b8;
            max-width: 600px;
            margin: 0 auto 40px auto;
            line-height: 1.7;
            font-weight: 400;
        }

        .hero-subtitle strong, .hero-subtitle b {
            color: #00f2fe;
            font-weight: 600;
        }

        /* =================== GLASS CARDS =================== */
        .glass-card {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.8) 0%, rgba(15, 23, 42, 0.4) 100%);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 32px 24px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        .glass-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, #00f2fe, #4facfe, #ff0055);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-8px);
            border-color: rgba(0, 242, 254, 0.2);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 30px rgba(0, 242, 254, 0.1);
        }
        .glass-card:hover::before { opacity: 1; }

        /* =================== FEATURE GRID =================== */
        .feature-grid-landing {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin: 50px 0;
            animation: slideInUp 1s ease-out 0.2s both;
        }
        .feature-card-landing {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.7) 0%, rgba(15, 23, 42, 0.3) 100%);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 28px 22px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        .feature-card-landing::after {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, #00f2fe, #4facfe);
            transform: scaleX(0);
            transition: transform 0.4s ease;
        }
        .feature-card-landing:hover {
            transform: translateY(-6px) scale(1.02);
            border-color: rgba(0, 242, 254, 0.15);
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35), 0 0 20px rgba(0, 242, 254, 0.08);
        }
        .feature-card-landing:hover::after { transform: scaleX(1); }

        .feature-icon-landing {
            font-size: 2.2rem;
            margin-bottom: 14px;
            display: inline-block;
            animation: float 3s ease-in-out infinite;
        }
        .feature-title-landing {
            font-size: 1.05rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
        }
        .feature-desc-landing {
            font-size: 0.85rem;
            color: #94a3b8;
            line-height: 1.5;
        }

        /* =================== METRICS STRIP =================== */
        .metrics-strip {
            display: flex;
            justify-content: center;
            gap: 48px;
            margin: 40px 0;
            padding: 28px 20px;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.5) 0%, rgba(2, 5, 10, 0.3) 100%);
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            backdrop-filter: blur(10px);
            flex-wrap: wrap;
            animation: slideInUp 1s ease-out 0.4s both;
        }
        .metric-box {
            text-align: center;
            transition: transform 0.3s ease;
            min-width: 100px;
        }
        .metric-box:hover { transform: scale(1.08); }
        .metric-number {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(180deg, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        .metric-title {
            font-size: 0.7rem;
            color: #00f2fe;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
        }

        /* =================== CTA BUTTONS =================== */
        .cta-row {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin: 36px 0 20px 0;
            flex-wrap: wrap;
            animation: slideInUp 1s ease-out 0.6s both;
        }
        .cta-btn {
            display: inline-block;
            padding: 14px 36px;
            font-size: 1rem;
            font-weight: 700;
            color: #02050a;
            background: linear-gradient(135deg, #00f2fe, #4facfe);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            animation: pulseGlow 2.5s infinite;
            letter-spacing: 0.5px;
        }
        .cta-btn:hover {
            transform: translateY(-2px) scale(1.04);
            box-shadow: 0 12px 40px rgba(0, 242, 254, 0.4);
        }
        .cta-btn-outline {
            display: inline-block;
            padding: 14px 36px;
            font-size: 1rem;
            font-weight: 600;
            color: #f8fafc;
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .cta-btn-outline:hover {
            border-color: rgba(0, 242, 254, 0.5);
            background: rgba(0, 242, 254, 0.05);
            transform: translateY(-2px);
        }

        /* =================== EXISTING STYLES =================== */

        /* Modern Card (No Image) */
        .travel-card-modern {
            background: linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left: 3px solid #00f2fe;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: transform 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
            animation: fadeInLeft 0.5s ease-out both;
        }
        .travel-card-modern:hover { transform: translateX(4px); background: rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0, 242, 254, 0.1); }

        .card-header-modern { margin-bottom: 8px; }
        .card-title-row { display: flex; justify-content: space-between; align-items: center; }
        .card-title { font-size: 16px; font-weight: 600; color: #f8fafc; }
        .card-rating { font-size: 12px; color: #fbbf24; background: rgba(251, 191, 36, 0.1); padding: 2px 6px; border-radius: 4px; }
        .card-cost { font-size: 13px; color: #00f2fe; margin-top: 2px; }
        .card-desc { font-size: 13px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px; }

        .card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
        .card-tag { font-size: 10px; background: rgba(255,255,255,0.08); padding: 3px 8px; border-radius: 8px; color: #f8fafc; }

        /* HERO CARD */
        .hero-card {
            background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(112, 0, 255, 0.1) 100%);
            border: 1px solid rgba(0, 229, 255, 0.3);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
            animation: scaleIn 0.6s ease-out both;
        }
        .hero-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, #00f2fe, #4facfe);
            background-size: 200% 100%;
            animation: gradientShift 3s ease infinite;
        }

        .hero-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .hero-rating { font-size: 14px; font-weight: 600; color: #fbbf24; animation: countUp 0.5s ease-out 0.3s both; }

        .hero-title { font-size: 24px; font-weight: 700; color: #fff; margin-bottom: 8px; letter-spacing: -0.5px; }
        .hero-desc { font-size: 15px; color: #e2e8f0; line-height: 1.6; margin-bottom: 20px; }

        .hero-footer { display: flex; justify-content: space-between; align-items: end; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px; }
        .hero-tags { display: flex; gap: 8px; flex-wrap: wrap; }
        .hero-tag { font-size: 11px; background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 20px; color: #fff; transition: all 0.2s ease; }
        .hero-tag:hover { background: rgba(0, 242, 254, 0.15); transform: scale(1.05); }
        .hero-cost { font-size: 16px; font-weight: 600; color: #ff0055; animation: countUp 0.5s ease-out 0.4s both; }

        /* Modern Timeline */
        .modern-timeline-container { margin-top: 20px; }
        .day-section { margin-bottom: 30px; }
        .day-badge {
            display: inline-block;
            background: #4facfe;
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(112, 0, 255, 0.3);
        }

        .day-timeline {
            position: relative;
            padding-left: 12px;
            border-left: 2px solid rgba(255,255,255,0.05);
            margin-left: 10px;
        }

        .timeline-step {
            position: relative;
            padding-bottom: 24px;
            padding-left: 20px;
            animation: fadeInLeft 0.4s ease-out both;
        }
        .timeline-step:nth-child(1) { animation-delay: 0s; }
        .timeline-step:nth-child(2) { animation-delay: 0.1s; }
        .timeline-step:nth-child(3) { animation-delay: 0.2s; }
        .timeline-step:nth-child(4) { animation-delay: 0.3s; }
        .timeline-step:nth-child(5) { animation-delay: 0.4s; }

        .timeline-node {
            position: absolute;
            left: -17px;
            top: 0;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #02050a;
            border: 2px solid #00f2fe;
            z-index: 2;
            transition: all 0.3s ease;
        }
        .timeline-node.last { background: #00f2fe; animation: pulseGlow 2s infinite; }
        .timeline-step:hover .timeline-node { background: #00f2fe; transform: scale(1.3); }

        .timeline-content-modern {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            transition: all 0.3s ease;
        }
        .timeline-content-modern:hover { background: rgba(255,255,255,0.04); transform: translateX(4px); border-color: rgba(0, 242, 254, 0.15); }

        .timeline-time-badge {
            font-size: 10px;
            color: #00f2fe;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .timeline-step-title { font-size: 14px; font-weight: 600; color: #f8fafc; margin: 4px 0 2px 0; }
        .timeline-step-desc { font-size: 12px; color: #94a3b8; }

        /* Carousel */
        .suggestion-carousel { display: flex; gap: 12px; overflow-x: auto; padding: 10px 0; scrollbar-width: none; }
        .suggestion-carousel::-webkit-scrollbar { display: none; }

        .carousel-item {
            min-width: 150px;
            max-width: 180px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px;
            display: flex; flex-direction: column; gap: 8px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            animation: scaleIn 0.4s ease-out both;
        }
        .carousel-item:nth-child(1) { animation-delay: 0s; }
        .carousel-item:nth-child(2) { animation-delay: 0.08s; }
        .carousel-item:nth-child(3) { animation-delay: 0.16s; }
        .carousel-item:nth-child(4) { animation-delay: 0.24s; }
        .carousel-item:nth-child(5) { animation-delay: 0.32s; }

        .carousel-item:hover { transform: translateY(-6px) scale(1.03); border-color: #00f2fe; box-shadow: 0 8px 24px rgba(0, 242, 254, 0.12); }

        .carousel-item.tip-glow {
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.05), rgba(20,25,40,0.5));
            border-color: rgba(255, 215, 0, 0.2);
            animation: borderGlow 3s ease-in-out infinite;
        }

        .carousel-icon { font-size: 20px; transition: transform 0.3s ease; }
        .carousel-item:hover .carousel-icon { transform: scale(1.2) rotate(5deg); }
        .carousel-text { font-size: 13px; color: #f8fafc; font-weight: 500; line-height: 1.3; }
        .carousel-cat { font-size: 10px; color: #94a3b8; text-transform: uppercase; margin-top: auto; }

        /* Voice Input — styled inline (old fixed-position removed) */

        /* AI Thinking Pulse */
        .ai-thinking-pulse {
            width: 12px; height: 12px;
            background: #00f2fe;
            border-radius: 50%;
            animation: pulseGlow 2s infinite;
            margin: 10px auto;
        }

        /* Chat Bubbles — legacy (overridden by new .chat-row system) */

        /* Action Cards */
        .action-card {
            background: linear-gradient(135deg, rgba(20, 25, 40, 0.8), rgba(15, 20, 30, 0.9));
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 32px 24px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: scaleIn 0.5s ease-out both;
        }
        .action-card:hover { transform: translateY(-8px) scale(1.02); border-color: rgba(0, 229, 255, 0.3); box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4), 0 0 20px rgba(0, 242, 254, 0.08); }
        .action-icon { font-size: 3rem; margin-bottom: 16px; display: block; animation: float 3s ease-in-out infinite; }
        .action-title { font-size: 1.4rem; font-weight: 700; color: #f8fafc; }

        /* Question Cards */
        .question-card {
            background: linear-gradient(135deg, rgba(20, 25, 40, 0.9), rgba(15, 20, 30, 0.95));
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 32px;
            margin: 20px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: slideInUp 0.6s ease-out both;
        }
        .question-header {
            font-size: 1.5rem; font-weight: 700; color: #f8fafc;
            margin-bottom: 24px; text-align: center;
            display: flex; align-items: center; justify-content: center; gap: 12px;
        }
        .question-icon { font-size: 2rem; filter: drop-shadow(0 2px 8px rgba(0, 229, 255, 0.4)); animation: float 2.5s ease-in-out infinite; }

        /* Feature Grid (legacy — used elsewhere) */
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin: 60px 0;
        }
        .feature-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 32px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }
        .feature-card::before {
             content: "";
             position: absolute;
             top: 0; left: 0; right: 0; height: 2px;
             background: linear-gradient(90deg, #00f2fe, #4facfe);
             opacity: 0;
             transition: opacity 0.3s;
        }
        .feature-card:hover {
            transform: translateY(-8px);
            border-color: rgba(255,255,255,0.1);
            background: linear-gradient(145deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        }
        .feature-card:hover::before { opacity: 1; }

        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 20px;
            display: inline-block;
            animation: float 3s ease-in-out infinite;
            transition: transform 0.3s ease;
        }
        .feature-card:hover .feature-icon { transform: scale(1.15) rotate(5deg); }
        .feature-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
        }
        .feature-desc {
            font-size: 0.95rem;
            color: #94a3b8;
            line-height: 1.6;
        }

        /* Metrics (legacy) */
        .metrics-container {
            display: flex;
            justify-content: center;
            gap: 60px;
            margin: 40px 0 80px 0;
            flex-wrap: wrap;
            padding: 30px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(2, 5, 10, 0.3);
            backdrop-filter: blur(10px);
        }
        .metric-item {
            text-align: center;
            transition: transform 0.3s;
        }
        .metric-item:hover { transform: scale(1.05); }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(180deg, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #00f2fe;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
        }

        /* =================== CHAT BUBBLES =================== */
        .chat-row {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            animation: slideInUp 0.3s ease-out;
        }
        .chat-row.user { justify-content: flex-end; }
        .chat-row.bot { justify-content: flex-start; }
        .chat-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }
        .chat-avatar.user-av {
            background: linear-gradient(135deg, #4facfe, #00f2fe);
        }
        .chat-avatar.bot-av {
            background: linear-gradient(135deg, #7000ff, #ff0055);
        }
        .user-bubble {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.15), rgba(0, 242, 254, 0.08));
            border: 1px solid rgba(79, 172, 254, 0.25);
            border-radius: 18px 18px 4px 18px;
            padding: 14px 20px;
            max-width: 75%;
            color: #e0e6ed;
            font-size: 0.95rem;
            line-height: 1.6;
            backdrop-filter: blur(10px);
        }
        .bot-bubble {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 0.3));
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 18px 18px 18px 4px;
            padding: 14px 20px;
            max-width: 85%;
            color: #f1f5f9;
            font-size: 0.95rem;
            line-height: 1.7;
            backdrop-filter: blur(16px);
        }

        /* =================== DEEP INTELLIGENCE CARDS =================== */
        .intel-section-title {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #00f2fe, #4facfe, #7000ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        .intel-card {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.35));
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            transition: border-color 0.3s ease, transform 0.3s ease;
            animation: slideInUp 0.5s ease-out both;
        }
        .intel-card:nth-child(1) { animation-delay: 0.1s; }
        .intel-card:nth-child(2) { animation-delay: 0.2s; }
        .intel-card:nth-child(3) { animation-delay: 0.3s; }
        .intel-card:hover {
            border-color: rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
        }
        .intel-card-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #00f2fe;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .intel-metric-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .intel-metric {
            background: rgba(0, 242, 254, 0.08);
            border: 1px solid rgba(0, 242, 254, 0.15);
            border-radius: 12px;
            padding: 12px 16px;
            flex: 1;
            min-width: 120px;
            text-align: center;
        }
        .intel-metric-value {
            font-size: 1.3rem;
            font-weight: 800;
            color: #fff;
        }
        .intel-metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-top: 4px;
        }
        .intel-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .intel-badge.safe {
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .intel-badge.warning {
            background: rgba(234, 179, 8, 0.15);
            color: #eab308;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }
        .intel-badge.danger {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .intel-list-item {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #cbd5e1;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        .intel-list-icon {
            flex-shrink: 0;
            margin-top: 2px;
        }

        /* =================== ITINERARY SLOT CARDS =================== */
        .itin-day-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #fff;
            padding: 8px 0;
            margin-bottom: 8px;
            border-bottom: 1px solid rgba(0, 242, 254, 0.15);
        }
        .itin-slot {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 0.3));
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 10px;
            display: flex;
            gap: 14px;
            align-items: flex-start;
            transition: transform 0.2s ease, border-color 0.3s ease;
            animation: fadeInLeft 0.5s ease-out both;
        }
        .itin-slot:nth-child(1) { animation-delay: 0.1s; }
        .itin-slot:nth-child(2) { animation-delay: 0.2s; }
        .itin-slot:nth-child(3) { animation-delay: 0.3s; }
        .itin-slot:nth-child(4) { animation-delay: 0.4s; }

        .itin-slot:hover {
            transform: translateX(4px);
            border-color: rgba(0, 242, 254, 0.2);
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.4));
        }
        .itin-slot-icon {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .itin-slot-icon.morning { background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(252, 211, 77, 0.1)); }
        .itin-slot-icon.lunch { background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(248, 113, 113, 0.1)); }
        .itin-slot-icon.afternoon { background: linear-gradient(135deg, rgba(96, 165, 250, 0.2), rgba(147, 197, 253, 0.1)); }
        .itin-slot-icon.evening { background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(167, 139, 250, 0.1)); }
        .itin-slot-body { flex: 1; }
        .itin-slot-time {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .itin-slot-time.morning { color: #fbbf24; }
        .itin-slot-time.lunch { color: #f87171; }
        .itin-slot-time.afternoon { color: #60a5fa; }
        .itin-slot-time.evening { color: #a78bfa; }
        .itin-slot-title {
            font-size: 1rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 4px;
        }
        .itin-slot-desc {
            font-size: 0.85rem;
            color: #94a3b8;
            line-height: 1.5;
        }

        /* =================== VOICE TRANSCRIPT CHIP =================== */
        .voice-transcript {
            background: rgba(0, 242, 254, 0.08);
            border: 1px solid rgba(0, 242, 254, 0.15);
            border-radius: 12px;
            padding: 10px 14px;
            margin-top: 4px;
            color: #e0e6ed;
            font-size: 0.88rem;
            animation: fadeInScale 0.3s ease-out;
        }
        @keyframes fadeInScale {
            0% { opacity: 0; transform: scale(0.95); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* =================== NATIVE ELEMENTS ANIMATIONS =================== */
        /* Buttons */
        div[data-testid="stButton"] button {
            transition: all 0.3s ease !important;
        }
        div[data-testid="stButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 242, 254, 0.2);
        }

        /* Inputs */
        div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
            transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
        }
        div[data-testid="stTextInput"] input:focus, div[data-testid="stNumberInput"] input:focus {
            border-color: #00f2fe !important;
            box-shadow: 0 0 0 2px rgba(0, 242, 254, 0.2) !important;
        }

        /* Tabs */
        div[data-testid="stTabs"] button {
            transition: all 0.3s ease !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            animation: pulseGlow 2s infinite;
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            transition: border-color 0.3s ease !important;
        }
        div[data-testid="stExpander"]:hover {
            border-color: rgba(0, 242, 254, 0.3) !important;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
            animation: breathe 4s ease-in-out infinite;
        }
    """

    return "<style>\n" + tokens + "\n" + static_css + "\n</style>"


def render_hero_landing():
    """
    Returns the HTML for the hero landing section.
    Displayed when user has no messages (first visit).
    """
    html = """
    <div class="hero-landing">
        <div class="hero-badge">✦ AI-Powered Travel Intelligence</div>
        <h1 class="gradient-headline">Your Journey, Reimagined by AI</h1>
        <p class="hero-subtitle"><b>WanderX</b> analyzes real-time weather, safety data, local events and your preferences to craft the <b>perfect trip</b> — instantly.</p>
    </div>
    <div class="metrics-strip">
        <div class="metric-box">
            <div class="metric-number">1,200+</div>
            <div class="metric-title">Trips Planned</div>
        </div>
        <div class="metric-box">
            <div class="metric-number">50+</div>
            <div class="metric-title">Countries</div>
        </div>
        <div class="metric-box">
            <div class="metric-number">4.9★</div>
            <div class="metric-title">User Rating</div>
        </div>
        <div class="metric-box">
            <div class="metric-number">24/7</div>
            <div class="metric-title">AI Copilot</div>
        </div>
    </div>
    <div class="feature-grid-landing">
        <div class="feature-card-landing">
            <div class="feature-icon-landing">🧠</div>
            <div class="feature-title-landing">Smart Itineraries</div>
            <div class="feature-desc-landing">AI builds day-by-day plans optimized for your pace, budget, and interests</div>
        </div>
        <div class="feature-card-landing">
            <div class="feature-icon-landing">🛡️</div>
            <div class="feature-title-landing">Risk Analysis</div>
            <div class="feature-desc-landing">Real-time safety scoring with news monitoring and travel advisories</div>
        </div>
        <div class="feature-card-landing">
            <div class="feature-icon-landing">📡</div>
            <div class="feature-title-landing">Live Intelligence</div>
            <div class="feature-desc-landing">Weather, events, and local insights updated every session</div>
        </div>
        <div class="feature-card-landing">
            <div class="feature-icon-landing">💰</div>
            <div class="feature-title-landing">Budget Optimizer</div>
            <div class="feature-desc-landing">Track expenses and get cost-optimized alternatives on the fly</div>
        </div>
    </div>
    """
    return html

