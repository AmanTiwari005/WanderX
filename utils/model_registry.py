"""
Centralized AI Model Registry for WanderTrip.
All agents import their model from here instead of reading env vars directly.
"""
import os
import streamlit as st

# ── Model Registry ──
# Each entry: (display_name, groq_model_id, description, max_context, tier)
AVAILABLE_MODELS = {
    "gpt-oss-120b": {
        "name": "GPT OSS 120B",
        "model_id": "openai/gpt-oss-120b",
        "description": "Flagship open-weight MoE — best for complex reasoning & coding",
        "context_window": 128000,
        "tier": "heavy",
        "icon": "🧠",
    },
    "gpt-oss-20b": {
        "name": "GPT OSS 20B", 
        "model_id": "openai/gpt-oss-20b",
        "description": "Compact & cost-efficient — great for agentic workflows",
        "context_window": 128000,
        "tier": "light",
        "icon": "⚡",
    },
    "kimi-k2": {
        "name": "Kimi K2",
        "model_id": "moonshotai/kimi-k2-instruct-0905",
        "description": "256K context, advanced reasoning & agentic coding",
        "context_window": 256000,
        "tier": "heavy",
        "icon": "🌙",
    },
    "llama-4-scout": {
        "name": "Llama 4 Scout",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "description": "Multimodal with 17B active params — fast & capable",
        "context_window": 131072,
        "tier": "medium",
        "icon": "🦙",
    },
    "llama-3.3-70b": {
        "name": "Llama 3.3 70B",
        "model_id": "llama-3.3-70b-versatile",
        "description": "Versatile 70B workhorse — great all-rounder",
        "context_window": 128000,
        "tier": "medium",
        "icon": "🦙",
    },
    "qwen3-32b": {
        "name": "Qwen 3 32B",
        "model_id": "qwen/qwen3-32b",
        "description": "Current default — strong multilingual & reasoning",
        "context_window": 32768,
        "tier": "medium",
        "icon": "🔮",
    },
}

DEFAULT_MODEL_KEY = "qwen3-32b"


def get_active_model_id():
    """
    Returns the Groq model ID to use for API calls.
    Priority: session_state > env var > default.
    """
    # 1. Check session state (set by sidebar selector)
    if hasattr(st, "session_state") and "selected_model" in st.session_state:
        key = st.session_state.selected_model
        if key in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[key]["model_id"]
    
    # 2. Check env var
    env_model = os.getenv("GROQ_MODEL")
    if env_model:
        return env_model
    
    # 3. Default
    return AVAILABLE_MODELS[DEFAULT_MODEL_KEY]["model_id"]


def get_active_model_info():
    """Returns full model info dict for the currently active model."""
    if hasattr(st, "session_state") and "selected_model" in st.session_state:
        key = st.session_state.selected_model
        if key in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[key]
    return AVAILABLE_MODELS[DEFAULT_MODEL_KEY]


def get_model_display_options():
    """Returns list of (key, display_label) tuples for sidebar selector."""
    return [(k, f"{v['icon']} {v['name']}") for k, v in AVAILABLE_MODELS.items()]


def get_complex_task_model_id():
    """
    Returns a high-capability model ID for complex tasks (Itinerary, Reasoning).
    Prioritizes Llama 3.3 70B or GPT OSS 120B.
    """
    # preferred = "gpt-oss-120b" 
    # Fallback to Llama 3.3 70B as it's very reliable for JSON
    preferred = "qwen3-32b"
    
    if preferred in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[preferred]["model_id"]
    
    # Fallback to whatever is active if preferred missing
    return get_active_model_id()
