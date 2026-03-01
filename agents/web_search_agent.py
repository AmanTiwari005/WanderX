from utils.model_registry import get_active_model_id
from utils.web_search import search_web, search_news
import json
import logging
from datetime import datetime
import time
import concurrent.futures

logger = logging.getLogger("wanderx.web_search_agent")

class WebSearchAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = get_active_model_id()

    def live_pulse(self, location, dates, interests=None):
        """
        RTRIE live pulse aggregator:
        - concurrent fast collection
        - includes chaos/disruption signal
        - emits freshness metadata for risk confidence model
        """
        started = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                "events": pool.submit(self.find_events, location, dates),
                "trends": pool.submit(self.find_hidden_gems, location),
                "vibe": pool.submit(self.get_vibe_check, location),
                "chaos": pool.submit(self.detect_chaos, location),
                "price_signal": pool.submit(self.predict_prices, location, dates),
            }

            intel = {}
            for key, fut in futures.items():
                try:
                    intel[key] = fut.result(timeout=18)
                except Exception as e:
                    logger.warning(f"Live pulse subtask '{key}' failed: {e}")
                    intel[key] = {} if key in ("vibe", "chaos", "price_signal") else []

        latency_ms = round((time.time() - started) * 1000)

        intel["reality_check"] = []
        intel["freshness"] = {
            "fetched_at": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "source": "live_web_intel",
            "status": "live" if latency_ms < 12000 else "degraded",
        }
        intel["error"] = False

        return intel

    def find_events(self, location, dates):
        """
        🎉 Live Event Radar: Finds events during specific dates.
        """
        try:
            query = f"events in {location} {dates} festivals concerts sports"
            results = search_web(query, max_results=8)
            
            if not results:
                return []
                
            # Synthesize with LLM
            prompt = f"""
            Identify confirmed events happening in {location} during {dates} based on these search results.
            
            Search Results:
            {json.dumps(results)}
            
            Return JSON object:
            {{
                "events": [
                    {{ "title": "Event Name", "date": "Date", "type": "Music/Art/Sports", "details": "Brief info" }}
                ]
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            # Helper to parse potential wrapped JSON
            content = res.choices[0].message.content
            if "```json" in content:
                 content = content.replace("```json", "").replace("```", "")
            
            data = json.loads(content)
            return data.get("events", data) if isinstance(data, dict) else data
            
        except Exception as e:
            logger.error(f"Event Radar Error: {e}")
            return []

    def find_hidden_gems(self, location):
        """
        🔥 Trend Scout: Finds viral/new spots from recent discussions.
        """
        try:
            # Targeted query for recent "gems"
            query = f"best hidden gems {location} 2024 2025 travel blog reddit"
            results = search_web(query, max_results=6)
            
            if not results:
                return []

            prompt = f"""
            Extract 3-4 "Trending" or "Hidden Gem" spots in {location} from these findings.
            Focus on: New openings, viral food spots, or secret views.
            
            Search Results:
            {json.dumps(results)}
            
            Return JSON object:
            {{
                "gems": [
                    {{ "name": "Place Name", "category": "Food/View/Activity", "reason": "Why it's trending" }}
                ]
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            return data.get("gems", data) if isinstance(data, dict) else data
            
        except Exception as e:
            logger.error(f"Trend Scout Error: {e}")
            return []

    def get_vibe_check(self, location):
        """
        🧠 Vibe Check: Sentiment analysis of recent noise/crowds/safety.
        """
        try:
            query = f"{location} tourism overcrowding safety recent reviews reddit twitter 2025"
            results = search_web(query, max_results=5)
            
            if not results:
                return {"status": "Unknown", "note": "No recent chatter found."}

            prompt = f"""
            Analyze the "Vibe" of {location} right now based on these recent search results.
            Are travelers complaining about crowds, construction, or scams? Or is it peaceful?
            
            Search Results:
            {str(results)[:2000]}
            
            Return JSON:
            {{
                "vibe": "Chill / Hectic / Touristy / Dangerous",
                "summary": "1 sentence summary",
                "warning": "Any specific warning or 'None'"
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            return json.loads(res.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Vibe Check Error: {e}")
            return {"status": "Error", "note": str(e)}

    def find_indoor_options(self, location):
        """
        ☔ Rainy Day Rescue: Finds indoor alternatives.
        """
        try:
            query = f"best indoor activities {location} museums cafes workshops"
            results = search_web(query, max_results=5)
            
            prompt = f"""
            Suggest 3 rainy-day alternatives for {location} based on these results.
            
            Results: {str(results)}
            
            Return JSON object:
            {{
                "alternatives": [ {{ "title": "Activity", "type": "Indoor" }} ]
            }}
            """
             
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            return data.get("alternatives", data) if isinstance(data, dict) else data
            
        except Exception as e:
             logger.error(f"Rainy Day Error: {e}")
             return []

    def detect_chaos(self, location):
        """
        ⚡ Real-Time Chaos Detector: Monitors for strikes, protests, closures, and major emergencies.
        """
        try:
            # broadened query string to include severe disruptions
            query = f"{location} strike OR protest OR airport closure OR warning OR explosion OR attack OR evacuation OR emergency {datetime.now().year}"
            results = search_web(query, max_results=6, timelimit='w')

            if not results:
                return {"status": "clear", "alerts": []}

            prompt = f"""
            Scan these search results for any ACTIVE disruptions in {location}:
            strikes, protests, airport closures, natural disasters, terrorism, war, or safety warnings.
            
            Return JSON:
            {{
                "status": "clear" or "warning" or "danger",
                "alerts": [
                    {{ "type": "Strike/Protest/Closure/Disaster", "title": "Brief title", "details": "What's happening", "severity": "low/medium/high" }}
                ]
            }}
            Only include CONFIRMED, CURRENT alerts. Do NOT include historical events.
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            return json.loads(res.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Chaos Detector Error: {e}")
            return {"status": "error", "alerts": []}

    def find_local_secrets(self, location):
        """
        🗺️ Local's Secret Map: Reddit/forum sourced hidden spots.
        """
        try:
            query = f"reddit {location} locals recommend hidden spots off beaten path"
            results = search_web(query, max_results=6)
            
            if not results:
                return []

            prompt = f"""
            Extract recommendations from LOCALS (not tourists) about {location} from these results.
            Focus on places that only locals know about.
            
            Search Results: {json.dumps(results[:4])}
            
            Return JSON object:
            {{
                "secrets": [
                    {{ "name": "Place Name", "type": "Restaurant/Bar/Park/Market/View", "local_tip": "What locals say about it", "area": "Neighborhood" }}
                ]
            }}
            Include 3-5 spots maximum. Only include places mentioned by actual locals.
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            return data.get("spots", data.get("secrets", data)) if isinstance(data, dict) else data
            
        except Exception as e:
            logger.error(f"Local Secrets Error: {e}")
            return []

    def predict_prices(self, location, dates):
        """
        🔮 Price Prophet: Flight/hotel price trend predictions.
        """
        try:
            query = f"{location} flight hotel prices {dates} cheap expensive forecast 2025"
            results = search_web(query, max_results=6)
            
            if not results:
                return {"verdict": "unknown", "details": "No price data found"}

            prompt = f"""
            Based on these search results, predict whether NOW is a good time to book travel to {location} for {dates}.
            
            Search Results: {json.dumps(results[:4])}
            
            Return JSON:
            {{
                "verdict": "Book Now" or "Wait" or "It Depends",
                "confidence": "Low/Medium/High",
                "flight_trend": "Rising/Stable/Dropping",
                "hotel_trend": "Rising/Stable/Dropping",
                "best_booking_window": "When to book for best prices",
                "reason": "2-sentence explanation",
                "money_tip": "Specific saving tip"
            }}
            """
            
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(res.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Price Prophet Error: {e}")
            return {"verdict": "unknown", "details": str(e)}

