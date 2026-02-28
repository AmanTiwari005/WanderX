import streamlit as st


def generate_dynamic_suggestions(history, weather=None, mobility=None):
    text = " ".join([m["content"] for m in history]).lower()
    suggestions = []

    # ===== WEATHER AWARE =====
    try:
        if weather and "error" not in weather:
            if weather.get("rain_probability", 0) > 0:
                suggestions.append({
                    "title": "🌧 Rain-Safe Plans",
                    "desc": f"Indoor & low-risk • {weather.get('temperature_c','')}°C • {weather.get('description','')}",
                    "prompt": "Suggest meaningful indoor or rain-safe experiences near me"
                })
            else:
                suggestions.append({
                    "title": "🌤 Perfect Weather Picks",
                    "desc": f"Great outdoor • {weather.get('temperature_c','')}°C • {weather.get('description','')}",
                    "prompt": "Suggest great outdoor meaningful experiences I can enjoy right now"
                })
    except:
        pass

    # ===== MOBILITY AWARE =====
    try:
        if mobility:
            reachable = [m for m in mobility if m["drive"] or m["walk"]]
            if reachable:
                nearest = reachable[0]
                drive = f"{nearest['drive']['duration_min']} min drive" if nearest["drive"] else ""
                walk = f"{nearest['walk']['duration_min']} min walk" if nearest["walk"] else ""

                suggestions.append({
                    "title": "🚶 Nearby Meaningful Places",
                    "desc": f"{nearest['place']} • {walk} {( ' | ' + drive) if drive else ''}",
                    "prompt": "Suggest the best meaningful nearby places I can realistically visit"
                })
    except:
        pass

    # ===== INTEREST AWARE =====
    if "food" in text:
        suggestions.append({
            "title": "🍽️ Authentic Local Food",
            "desc": "Worth-it places — not tourist traps",
            "prompt": "Recommend authentic local food spots nearby"
        })

    if any(x in text for x in ["nature", "view", "scenic"]):
        suggestions.append({
            "title": "🌄 Nature & Peace",
            "desc": "Calm, scenic, meaningful places",
            "prompt": "Suggest peaceful scenic nature experiences nearby"
        })

    # ===== SAFE FALLBACK =====
    if len(suggestions) < 2:
        suggestions.extend([
            {
                "title": "🧠 Compare Smart Options",
                "desc": "Help me decide wisely",
                "prompt": "Compare top realistic options and help me decide wisely"
            },
            {
                "title": "🗓 Plan For Today",
                "desc": "Based on live weather & distance",
                "prompt": "Plan my day realistically based on weather, time and energy"
            }
        ])

    return suggestions[:4]


def render_choice_cards(suggestions):
    st.write("### 🔍 Real-Time Smart Choices For You")

    cols = st.columns(2)

    for i, s in enumerate(suggestions):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="
                    padding:14px;
                    border-radius:14px;
                    background:#0f172a;
                    border:1px solid #2f2f2f;
                    margin-bottom:10px">
                    <h4>{s['title']}</h4>
                    <p style="opacity:.8">{s['desc']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(f"Select ➜ {s['title']}", key=f"suggestion_{i}"):
                st.session_state["auto_prompt"] = s["prompt"]
                st.rerun()
