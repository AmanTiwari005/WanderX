
import os
import sys
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

def verify_system():
    print("Starting System Verification...")
    
    # 1. Check Environment
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("X GROQ_API_KEY missing in .env")
        return
    else:
        print("OK GROQ_API_KEY found")
        
    owm_key = os.getenv("OWM_API_KEY")
    if not owm_key:
        print("! OWM_API_KEY missing (Weather will fail)")
    else:
        print("OK OWM_API_KEY found")

    # 2. Check Dependencies
    try:
        import groq
        import streamlit
        import folium
        print("OK Core dependencies installed")
    except ImportError as e:
        print(f"X Missing dependency: {e}")
        return

    # 3. Test LLM Client
    try:
        from groq import Groq
        from utils.llm_client import call_llm
        
        client = Groq(api_key=api_key)
        print("Testing LLM connection...")
        response = call_llm(client, [{"role": "user", "content": "Hello"}], max_retries=1)
        print(f"OK LLM Connected: {response[:20]}...")
    except Exception as e:
        print(f"X LLM Test Failed: {e}")
        return

    # 4. Test Orchestrator Init
    try:
        from orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(client)
        print("OK Orchestrator Initialized")
    except Exception as e:
        print(f"X Orchestrator Init Failed: {e}")
        return
        
    print("\nVerification Complete! System appears ready.")
    print("Run 'streamlit run app.py' to launch.")

if __name__ == "__main__":
    verify_system()
