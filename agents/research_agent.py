from utils.model_registry import get_active_model_id
from utils.web_search import search_web
import json
import logging
from datetime import datetime

logger = logging.getLogger("wanderx.research_agent")

class AutonomousResearchAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.max_iterations = 5

    def _get_system_message(self):
        return f"""
        You are an Autonomous Research Agent functioning as a Senior Travel Analyst.
        Current Time: {datetime.now().strftime('%Y-%m-%d')}
        
        Your objective is to thoroughly answer the user's research query about travel.
        You have access to a single tool: `search_web`.
        
        You operate in a strict Reason-Act-Observe loop (ReAct).
        
        Whenever you need more information, you MUST output ONLY a JSON object exactly matching this format to call the tool:
        {{
            "thought": "I need to find out X by searching for Y",
            "action": "search_web",
            "action_input": {{"query": "your detailed search query here"}}
        }}
        
        I will then run the tool and provide you with the Observation.
        
        If you have gathered enough information from the observations to thoroughly and completely answer the user's original query, you MUST output ONLY a JSON object exactly matching this format:
        {{
            "thought": "I now have enough information to answer the core query.",
            "final_answer": "Your comprehensive, detailed, and well-structured markdown report synthesizing all findings."
        }}
        
        CRITICAL RULES:
        1. Embody the ReAct loop strictly. 
        2. NEVER output normal text, ONLY output one of the two JSON structures above.
        3. If your search_web results say "No results" or aren't helpful, change your search query and try again.
        4. Provide highly specific, actionable, and verified information in your final answer, not generic fluff.
        5. DO NOT stop until you are highly confident in the depth and accuracy of your final answer.
        """

    def run_research(self, topic, profile_context=""):
        """
        Executes the autonomous reasoning loop.
        Returns a dict with the thought sequence and final answer.
        """
        model = get_active_model_id()
        
        messages = [
            {"role": "system", "content": self._get_system_message()},
            {"role": "user", "content": f"User Profile Context: {profile_context}\n\nResearch Query: {topic}\n\nBegin your research loop."}
        ]
        
        thoughts = []
        final_answer = None
        
        for i in range(self.max_iterations):
            try:
                # 1. Ask the LLM what to do
                res = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                
                content = res.choices[0].message.content
                try:
                    state = json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from LLM: {content}")
                    state = {"thought": "Error parsing LLM output", "final_answer": "Agent encountered a formatting error."}
                    break
                    
                thought = state.get("thought", "Thinking...")
                thoughts.append(thought)
                
                # Yield / log thought for UI if needed
                logger.info(f"[Research Loop {i+1}] Thought: {thought}")
                
                # Check if it's the final answer
                if "final_answer" in state:
                    final_answer = state["final_answer"]
                    logger.info(f"[Research Loop {i+1}] Final Answer reached.")
                    break
                    
                # Check if it wants to act
                if state.get("action") == "search_web":
                    action_input = state.get("action_input", {})
                    query = action_input.get("query", "")
                    
                    if not query:
                        observation = "Error: Invalid tool call, missing query."
                    else:
                        logger.info(f"[Research Loop {i+1}] Action: search_web('{query}')")
                        
                        # Execute the tool
                        results = search_web(query, max_results=5)
                        
                        if results:
                            # Format results for the LLM
                            obs_text = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in results])
                            observation = f"Search Results for '{query}':\n{obs_text}"
                        else:
                            observation = f"No results found for '{query}'. Try a different phrasing."
                            
                    # Provide observation back to the LLM
                    logger.debug(f"[Research Loop {i+1}] Observation length: {len(observation)}")
                    
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"Observation:\n{observation}"})
                
                else:
                    # Invalid action
                    obs = "Error: Unrecognized action. You must use 'search_web' or return 'final_answer'."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"Observation:\n{obs}"})

            except Exception as e:
                logger.error(f"Research Loop Exception on iteration {i}: {e}")
                thoughts.append(f"System Error encountered: {str(e)}")
                break

        if not final_answer:
            final_answer = ("The agent reached its maximum research iterations without arriving at a final conclusion. "
                            "Here is its last thought process:\n\n" + "\n".join([f"- {t}" for t in thoughts]))

        return {
            "query": topic,
            "thoughts": thoughts,
            "report": final_answer,
            "iterations_used": i + 1
        }
