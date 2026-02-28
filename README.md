# 🧭 WanderTrip — AI Travel Copilot

An agentic AI-powered travel planning companion that makes smart, data-driven decisions using live weather, safety intelligence, crowd analysis, and cultural insights.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent Architecture** | 11 specialized agents (Weather, News, Budget, Cultural, Health, Sustainability, etc.) working in parallel |
| ⚡ **Real-Time Intelligence** | Live weather, crowd density, safety risks, and news analysis |
| 🧠 **Decision Engine** | Risk fusion scoring with confidence levels and explainability |
| 📅 **Multi-Day Itineraries** | Detailed day-by-day plans with morning/afternoon/evening structure |
| 💰 **Budget Intelligence** | Cost breakdown, feasibility analysis, and saving tips |
| 🎭 **Cultural Advisor** | Etiquette, language tips, dress code, and tipping guidance |
| 🏥 **Health Advisory** | Water safety, vaccination info, and emergency contacts |
| 🌿 **Eco Scoring** | Carbon footprint estimates and sustainable travel options |
| 🗺️ **Interactive Maps** | Destination maps with Folium integration |
| 📄 **PDF Export** | Download itineraries as formatted PDFs |
| 💡 **Smart Suggestions** | Context-aware, location-specific follow-up suggestions with feedback learning |
| 🛡️ **Proactive Alerts** | Weather, safety, and crowd alerts in the sidebar |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Streamlit UI                   │
│              (app.py — Chat + Cards)             │
└────────────────────┬────────────────────────────┘
                     │
              ┌──────▼──────┐
              │ Orchestrator │ ← Cache Manager
              └──────┬──────┘
                     │ (Parallel Execution)
     ┌───────┬───────┼───────┬───────┬───────┐
     ▼       ▼       ▼       ▼       ▼       ▼
  Weather  News   Crowd  Budget  Culture  Health
  Agent    Agent  Agent  Agent   Agent    Agent
     │       │       │       │       │       │
     └───────┴───────┼───────┴───────┴───────┘
                     ▼
          ┌────────────────────┐
          │ Risk Fusion Engine │
          └────────┬───────────┘
                   ▼
          ┌────────────────────┐
          │ Recommendation     │ ← All Intel Synthesized
          │ Agent              │
          └────────────────────┘
```

## 🚀 Setup

### Prerequisites
- Python 3.10+
- API keys (see below)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd wanderx

# Install dependencies
pip install -r requirements.txt

# Copy environment template and add your keys
cp .env.example .env
# Edit .env with your actual API keys
```

### API Keys Required

| Key | Service | Get it at |
|-----|---------|-----------|
| `GROQ_API_KEY` | AI/LLM (Required) | [console.groq.com](https://console.groq.com) |
| `OWM_API_KEY` | Weather (Required) | [openweathermap.org](https://openweathermap.org/api) |
| `ORS_API_KEY` | Routes (Optional) | [openrouteservice.org](https://openrouteservice.org) |

### Run

```bash
streamlit run app.py
```

## 📁 Project Structure

```
wanderx/
├── app.py                  # Main Streamlit application
├── orchestrator.py         # Agent orchestration with caching
├── agents/                 # Specialized AI agents
│   ├── weather_agent.py    # Live weather intelligence
│   ├── news_agent.py       # Safety & news analysis
│   ├── crowd_agent.py      # Crowd density estimation
│   ├── budget_agent.py     # Budget feasibility analysis
│   ├── cultural_agent.py   # Etiquette & cultural tips
│   ├── health_agent.py     # Health & safety advisory
│   ├── sustainability_agent.py  # Eco scoring
│   ├── mobility_agent.py   # Route & transport intelligence
│   ├── itinerary_agent.py  # Multi-day itinerary generation
│   ├── context_agent.py    # User context building
│   └── recommendation_agent.py  # Final synthesis agent
├── engines/                # Decision-making engines
│   ├── risk_fusion_engine.py    # Multi-source risk scoring
│   ├── decision_engine.py       # Feasibility & safety logic
│   └── alert_engine.py          # Proactive alert generation
├── utils/                  # Shared utilities
│   ├── llm_client.py       # Centralized LLM wrapper with retry
│   ├── cache_manager.py    # In-memory TTL cache
│   ├── geocode.py          # Location geocoding
│   ├── map_viewer.py       # Folium map generation
│   ├── pdf_generator.py    # Itinerary PDF export
│   ├── suggestion_generator.py  # Smart suggestion engine
│   ├── feedback_tracker.py # User feedback storage
│   ├── analytics_tracker.py # Usage analytics
│   └── ...
├── prompts/
│   └── system_prompt.txt   # Core AI personality & rules
├── data/                   # Runtime data (feedback, analytics)
├── requirements.txt        # Pinned dependencies
└── .env.example            # Environment template
```

## 🔧 Configuration

Set `GROQ_MODEL` in your `.env` to change the LLM model (default: `qwen/qwen3-32b`).

## 📝 License

MIT
