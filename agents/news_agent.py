from utils.model_registry import get_active_model_id
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime

from utils.web_search import search_news

class NewsAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = get_active_model_id()

    def fetch_news(self, location, query_suffix="weather OR strike OR protest OR festival OR event OR closure"):
        """
        Fetches raw news items using the web search utility (DuckDuckGo/Google fallback)
        for much faster and more accurate results than standard RSS.
        """
        try:
            query = f"{location} {query_suffix}"
            
            # Using search_news from utils, bounded to 7 results for context window
            results = search_news(query, max_results=7)
            
            items = []
            for res in results:
                items.append({
                    "title": res.get("title", "No Title"),
                    "link": res.get("url", ""),
                    "pub_date": res.get("date", "Recent"),
                    "snippet": res.get("body", "")
                })
                
            return items
        except Exception as e:
            print(f"NewsAgent Fetch Error: {e}")
            return []

    def analyze_news(self, location, news_items):
        """
        Uses LLM to analyze news items for Safety Risks, Opportunities, and Interesting Facts.
        """
        if not news_items:
            return {"safety_risks": [], "opportunities": [], "interesting_facts": []}

        prompt = f"""
        You are a Decision Intelligence Agent for a Travel Planning System.
        
        Analyze the news for {location} and extract THREE categories:
        
        **1. SAFETY RISKS (Only if travel-critical):**
        ✅ INCLUDE: Natural disasters, severe weather, transport strikes, civil unrest, health emergencies, site closures, safety threats
        ❌ EXCLUDE: Political news (unless riots), sports, celebrity news, business news
        
        **2. OPPORTUNITIES (Events that enhance trips):**
        - Major festivals, cultural events, food fairs, concerts
        - Seasonal activities, special exhibitions
        
        **3. INTERESTING FACTS (Make the trip memorable):**
        - Local cultural highlights or traditions
        - Historical significance of the location
        - Unique food or cuisine to try
        - Hidden gems or lesser-known attractions
        - Best time/season insights
        - Local tips that tourists should know
        
        **OUTPUT RULES:**
        - If no items found for a category, return empty array
        - Keep summaries brief and actionable
        - Focus on what helps travelers make better decisions
        - Assign a Safety Score (0-100) where 0=Safe, 100=Do Not Travel
        
        Return JSON structure:
        {{
            "safety_score": 0,
            "verdict": "Safe/Caution/Critical",
            "safety_risks": [ {{ "title": "Headline", "summary": "Impact on travel", "severity": "High/Medium/Low", "actionable_advice": "What should the traveler do right now to avoid this" }} ],
            "opportunities": [ {{ "title": "Event name", "summary": "Why it enhances trip", "type": "Festival/Event/Exhibition" }} ],
            "interesting_facts": [ {{ "title": "Fact title", "description": "Brief interesting info", "category": "Culture/History/Food/Nature/Tip" }} ]
        }}
        
        News Items:
        {json.dumps(news_items, indent=2)}
        """
        
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "You are a JSON-only News Analyst."},
                          {"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            
            # Ensure defaults
            if "safety_score" not in data: data["safety_score"] = 0
            if "verdict" not in data: data["verdict"] = "Safe"
            
            return data
        except Exception as e:
            print(f"NewsAgent Analysis Error: {e}")
            return {"safety_risks": [], "opportunities": [], "interesting_facts": []}

    def get_intel(self, location):
        """
        Orchestrates the fetch and analyze process.
        Always returns a valid structure, never None.
        """
        raw_news = self.fetch_news(location)
        
        if raw_news:
            intel = self.analyze_news(location, raw_news)
        else:
            intel = {"safety_risks": [], "opportunities": [], "interesting_facts": []}
        
        # If no interesting facts from news, generate some about the destination
        if not intel.get("interesting_facts"):
            intel["interesting_facts"] = self.get_destination_facts(location)
            
        return intel
    
    def get_destination_facts(self, location):
        """
        Generates interesting facts about a destination using LLM.
        """
        try:
            prompt = f"""
            Generate 3-4 interesting facts about {location} for travelers.
            Focus on: local culture, must-try food, best photo spots, hidden gems, or unique traditions.
            
            Return JSON:
            {{
                "facts": [
                    {{"title": "Fact title", "description": "Brief 1-2 sentence description", "category": "Culture/History/Food/Nature/Tip"}}
                ]
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            return data.get("facts", [])
        except Exception as e:
            print(f"Destination Facts Error: {e}")
            return []
