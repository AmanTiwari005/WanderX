import concurrent.futures
import logging

from agents.weather_agent import WeatherAgent
from agents.news_agent import NewsAgent
from agents.mobility_agent import MobilityAgent
from agents.crowd_agent import CrowdAgent
from agents.web_search_agent import WebSearchAgent # NEW
from agents.research_agent import AutonomousResearchAgent # NEW
from agents.context_agent import ContextAgent
from agents.budget_agent import BudgetAgent
from agents.cultural_agent import CulturalAgent
from agents.health_agent import HealthAgent
from agents.sustainability_agent import SustainabilityAgent
from agents.packing_agent import PackingAgent
from agents.itinerary_agent import ItineraryAgent
from engines.risk_fusion_engine import RiskFusionEngine
from engines.alert_engine import AlertEngine
from engines.decision_engine import DecisionEngine
from engines.travel_brain import TravelBrain
from utils.geocode import geocode_location
from utils.cache_manager import get_cache
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    add_script_run_ctx = None
    get_script_run_ctx = None

logger = logging.getLogger("wanderx.orchestrator")


class AgentOrchestrator:
    def __init__(self, groq_client):
        self.weather_agent = WeatherAgent()
        self.news_agent = NewsAgent(groq_client)
        self.web_search_agent = WebSearchAgent(groq_client) # NEW
        self.research_agent = AutonomousResearchAgent(groq_client) # NEW
        self.mobility_agent = MobilityAgent()
        self.crowd_agent = CrowdAgent(groq_client)
        self.context_agent = ContextAgent()
        
        # Specialized Agents
        self.budget_agent = BudgetAgent(groq_client)
        self.cultural_agent = CulturalAgent(groq_client)
        self.health_agent = HealthAgent(groq_client)
        self.sustainability_agent = SustainabilityAgent(groq_client)
        self.packing_agent = PackingAgent(groq_client)
        
        self.risk_engine = RiskFusionEngine()
        self.alert_engine = AlertEngine()
        self.decision_engine = DecisionEngine()
        self.travel_brain = TravelBrain()
        self.itinerary_agent = ItineraryAgent(groq_client)
        
        self.cache = get_cache()
        
    def _safe_result(self, future, agent_name, fallback=None):
        """
        Safely extract a future's result with graceful degradation.
        Returns fallback dict if the agent raised an exception.
        """
        if future is None:
            return fallback or {}
        try:
            return future.result(timeout=30)
        except Exception as e:
            logger.error(f"Agent '{agent_name}' failed: {e}")
            return fallback or {"error": f"{agent_name} failed: {str(e)}"}

    def _cached_or_run(self, executor, cache_type, cache_key, agent_fn, ctx, *args):
        """
        Check cache first; if miss, submit agent to thread pool.
        Returns (future_or_None, cached_data_or_None).
        """
        cached = self.cache.get(cache_type, cache_key)
        if cached is not None:
            logger.debug(f"Cache HIT: {cache_type}:{cache_key}")
            return None, cached
        
        logger.debug(f"Cache MISS: {cache_type}:{cache_key}")
        
        if ctx and add_script_run_ctx:
            def sync_ctx_wrapper(func, *inner_args):
                add_script_run_ctx(ctx=ctx)
                return func(*inner_args)
            future = executor.submit(sync_ctx_wrapper, agent_fn, *args)
        else:
            future = executor.submit(agent_fn, *args)
            
        return future, None

    def run_analysis(self, destination, profile, current_location=None):
        """
        Orchestrates the parallel execution of all agents with caching
        and graceful degradation.
        """
        partial_failures = []
        
        # 1. Context Build
        user_context = self.context_agent.build_user_context(profile)
        
        # 2. Geocoding (with cache)
        cached_coords = self.cache.get("geocode", destination)
        if cached_coords:
            dest_coords = cached_coords
        else:
            dest_coords = geocode_location(destination)
            if dest_coords:
                self.cache.set("geocode", destination, dest_coords)
        
        if not dest_coords:
            return {"error": "Could not locate destination"}
            
        # 3. Two-Wave Parallel Execution
        # Wave 1: Real-time data agents (no dependencies)
        # Wave 2: Deep intelligence agents (need Wave 1 results for context)
        budget_str = profile.get("budget", "Moderate")
        budget_cache_key = f"{destination}:{budget_str}"
        
        ctx = get_script_run_ctx() if get_script_run_ctx else None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # === WAVE 1: Real-time data (weather, news, crowd) ===
            f_weather, c_weather = self._cached_or_run(
                executor, "weather", destination,
                self.weather_agent.get_weather_intel, ctx, dest_coords
            )
            f_news, c_news = self._cached_or_run(
                executor, "news", destination,
                self.news_agent.get_intel, ctx, destination
            )
            f_crowd, c_crowd = self._cached_or_run(
                executor, "crowd", destination,
                self.crowd_agent.get_crowd_intel, ctx, destination
            )
            
            # Mobility (only if current location is known)
            f_mobility = None
            c_mobility = None
            if current_location:
                mobility_key = f"{current_location}:{destination}"
                f_mobility, c_mobility = self._cached_or_run(
                    executor, "mobility", mobility_key,
                    self.mobility_agent.get_mobility_intel, ctx, current_location, dest_coords
                )
            
            # Collect Wave 1 results (needed as context for Wave 2)
            weather_intel = c_weather or self._safe_result(f_weather, "WeatherAgent")
            news_intel = c_news or self._safe_result(f_news, "NewsAgent")
            crowd_intel = c_crowd or self._safe_result(f_crowd, "CrowdAgent")
            mobility_intel = c_mobility or self._safe_result(f_mobility, "MobilityAgent")
            
            # === WAVE 2: Deep intelligence (contextualized with Wave 1 + profile) ===
            f_budget, c_budget = self._cached_or_run(
                executor, "budget", budget_cache_key,
                self.budget_agent.get_budget_intel, ctx, 
                destination, budget_str, profile.get("duration", 3),
                profile, weather_intel
            )
            f_culture, c_culture = self._cached_or_run(
                executor, "culture", destination,
                self.cultural_agent.get_cultural_intel, ctx, 
                destination, profile
            )
            f_health, c_health = self._cached_or_run(
                executor, "health", destination,
                self.health_agent.get_health_intel, ctx,
                destination, profile, weather_intel, news_intel
            )
            f_sustain, c_sustain = self._cached_or_run(
                executor, "sustainability", destination,
                self.sustainability_agent.get_sustainability_intel, ctx, 
                destination, "flight", profile
            )
            
            # Packing (uses weather from Wave 1)
            weather_summary = "Unknown"
            if weather_intel and not weather_intel.get("error"):
                weather_summary = f"{weather_intel.get('condition', 'Unknown')}, {weather_intel.get('temp_c', '--')}°C"
            
            f_packing, c_packing = self._cached_or_run(
                executor, "packing", destination,
                self.packing_agent.generate_packing_list, ctx, 
                destination, 
                profile.get("duration", 5), 
                weather_summary,
                profile
            )
            
            # === WAVE 3: Live Pulse (Web Intelligence) ===
            # Run in parallel with Wave 2, but logically deeper
            f_live_pulse, c_live_pulse = self._cached_or_run(
                executor, "web_search", destination,
                self.web_search_agent.live_pulse, ctx, 
                destination, 
                profile.get("dates", ""), 
                profile.get("interests", "")
            )
            
            # Collect Wave 2 results
            budget_intel = c_budget or self._safe_result(f_budget, "BudgetAgent")
            cultural_intel = c_culture or self._safe_result(f_culture, "CulturalAgent")
            health_intel = c_health or self._safe_result(f_health, "HealthAgent")
            sustainability_intel = c_sustain or self._safe_result(f_sustain, "SustainabilityAgent")
            packing_list = c_packing or self._safe_result(f_packing, "PackingAgent")
            live_pulse_intel = c_live_pulse or self._safe_result(f_live_pulse, "WebSearchAgent")
        
        # Store successful results in cache
        for cache_type, cache_key, data in [
            ("weather", destination, weather_intel),
            ("news", destination, news_intel),
            ("crowd", destination, crowd_intel),
            ("budget", budget_cache_key, budget_intel),
            ("culture", destination, cultural_intel),
            ("health", destination, health_intel),
            ("sustainability", destination, sustainability_intel),
            ("sustainability", destination, sustainability_intel),
            ("packing", destination, packing_list),
            ("web_search", destination, live_pulse_intel), # Cache live pulse
        ]:
            if data and not data.get("error"):
                self.cache.set(cache_type, cache_key, data)
        
        # Track partial failures
        for name, data in [
            ("WeatherAgent", weather_intel),
            ("NewsAgent", news_intel),
            ("CrowdAgent", crowd_intel),
            ("BudgetAgent", budget_intel),
            ("CulturalAgent", cultural_intel),
            ("HealthAgent", health_intel),
            ("SustainabilityAgent", sustainability_intel),
            ("PackingAgent", packing_list),
        ]:
            if isinstance(data, dict) and data.get("error"):
                partial_failures.append(f"{name}: {data['error']}")
            
        # 4. TravelBrain Analysis (coordinates all engines)
        intel_bundle = {
            "weather_intel": weather_intel,
            "news_intel": news_intel,
            "crowd_intel": crowd_intel,
            "mobility_intel": mobility_intel,
            "health_intel": health_intel,
            "budget_intel": budget_intel,
            "cultural_intel": cultural_intel,
            "sustainability_intel": sustainability_intel,
            "live_pulse_intel": live_pulse_intel,
        }
        brain_result = self.travel_brain.analyze(intel_bundle, profile=profile)
        
        risk_assessment = brain_result["risk_assessment"]
        alerts = brain_result["alerts"]
        plan_suggestions = brain_result["plan_suggestions"]
        safety_warnings = brain_result["safety_warnings"]
        travel_score = brain_result["travel_score"]
        cross_agent_insights = brain_result["cross_agent_insights"]
        
        # 5. Itinerary Generation (with full intel bundle)
        duration = int(profile.get("duration", 1))
        itinerary = None
        itinerary_validation = None
        if duration > 0:
            itin_context = {
                "weather_intel": weather_intel,
                "risk_assessment": risk_assessment,
                "news_intel": news_intel,
                "budget_intel": budget_intel,
                "health_intel": health_intel,
                "crowd_intel": crowd_intel,
                "live_pulse_intel": live_pulse_intel,
            }
            try:
                itinerary = self.itinerary_agent.generate_itinerary(
                    destination, duration, itin_context, profile
                )
                # 5b. Validate itinerary against live conditions
                if itinerary and not itinerary.get("error"):
                    itinerary_validation = self.travel_brain.validate_itinerary(
                        itinerary, intel_bundle, profile
                    )
            except Exception as e:
                logger.error(f"ItineraryAgent failed: {e}")
                itinerary = {"error": str(e)}
                partial_failures.append(f"ItineraryAgent: {e}")
        
        return {
            "user_context": user_context,
            "weather_intel": weather_intel,
            "news_intel": news_intel,
            "crowd_intel": crowd_intel,
            "mobility_intel": mobility_intel,
            "budget_intel": budget_intel,
            "cultural_intel": cultural_intel,
            "health_intel": health_intel,
            "sustainability_intel": sustainability_intel,
            "packing_list": packing_list,
            "live_pulse_intel": live_pulse_intel,
            "risk_assessment": risk_assessment,
            "alerts": alerts,
            "plan_suggestions": plan_suggestions,
            "safety_warnings": safety_warnings,
            "travel_score": travel_score,
            "cross_agent_insights": cross_agent_insights,
            "itinerary": itinerary,
            "itinerary_validation": itinerary_validation,
            "engine_metadata": brain_result.get("engine_metadata", {}),
            "partial_failures": partial_failures
        }

    def replan_remaining(self, destination, profile, original_itinerary, from_day, reason, current_intel=None):
        """
        🔄 Live Replan Engine: Re-generates itinerary from a specific day onward.
        Keeps completed days intact and regenerates remaining days with new context.
        
        Args:
            destination: Trip destination
            profile: User profile dict
            original_itinerary: The current itinerary dict
            from_day: Day number to start replanning from (1-indexed)
            reason: Why we're replanning (e.g., "Heavy rain forecast", "Museum closed")
            current_intel: Optional fresh intel dict to incorporate
        """
        try:
            # Preserve completed days
            preserved = {}
            total_days = len([k for k in original_itinerary.keys() if k.startswith("day_")])
            
            for i in range(1, from_day):
                key = f"day_{i}"
                if key in original_itinerary:
                    preserved[key] = original_itinerary[key]
            
            remaining_days = total_days - from_day + 1
            
            if remaining_days <= 0:
                return original_itinerary
            
            # Build replan context
            replan_context = current_intel or {}
            replan_context["replan_reason"] = reason
            replan_context["replan_from_day"] = from_day
            replan_context["completed_days_summary"] = json.dumps(
                {k: v.get("title", "") for k, v in preserved.items()}
            ) if preserved else "None"
            
            # Generate new days for the remaining period
            new_days = self.itinerary_agent.generate_itinerary(
                destination, remaining_days, replan_context, profile
            )
            
            # Merge: preserved days + renumbered new days
            merged = dict(preserved)
            
            if new_days and not new_days.get("error"):
                new_day_keys = sorted([k for k in new_days.keys() if k.startswith("day_")])
                for idx, old_key in enumerate(new_day_keys):
                    new_key = f"day_{from_day + idx}"
                    merged[new_key] = new_days[old_key]
                    # Update title to reflect correct day number
                    if "title" in merged[new_key]:
                        merged[new_key]["title"] = merged[new_key]["title"].replace(
                            f"Day {idx + 1}", f"Day {from_day + idx}"
                        )
                    # Add replan badge
                    merged[new_key]["replanned"] = True
                    merged[new_key]["replan_reason"] = reason
            else:
                # If regeneration fails, keep original days
                for i in range(from_day, total_days + 1):
                    key = f"day_{i}"
                    if key in original_itinerary:
                        merged[key] = original_itinerary[key]
                        merged[key]["replan_failed"] = True
            
            return merged
            
        except Exception as e:
            logger.error(f"Replan Engine Error: {e}")
            return original_itinerary

    def deep_research(self, topic, profile):
        """
        Triggers the AutonomousResearchAgent to perform a deep dive into a specific topic.
        """
        profile_context = f"Going to {profile.get('destination', 'Unknown')} for {profile.get('duration', 'a few')} days. Budget: {profile.get('budget', 'Unknown')}. Interests: {profile.get('interests', 'Unknown')}."
        
        ctx = get_script_run_ctx() if get_script_run_ctx else None
        
        # We run this heavily IO-bound task in a thread pool so it doesn't block the main app loop entirely
        # (Though Streamlit blocks mostly on UI logic, running web searches in background threads is safer for timeouts)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            if ctx and add_script_run_ctx:
                def sync_ctx_wrapper():
                    add_script_run_ctx(ctx=ctx)
                    return self.research_agent.run_research(topic, profile_context)
                future = executor.submit(sync_ctx_wrapper)
            else:
                future = executor.submit(self.research_agent.run_research, topic, profile_context)
                
            return self._safe_result(future, "AutonomousResearchAgent", fallback={"error": "Deep research failed or timed out."})
