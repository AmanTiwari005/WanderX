from utils.model_registry import get_active_model_id
"""
Centralized LLM client wrapper for WanderX.
Provides retry logic, response cleaning, and JSON extraction
so individual agents don't need to duplicate this logic.
"""

import os
import json
import re
import time
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("wanderx.llm")


def clean_llm_response(text: str) -> str:
    """
    Clean raw LLM output:
      1. Strip <think>...</think> blocks (case insensitive)
      2. Remove markdown code fences
      3. Trim whitespace
      4. Handle multiple thinking blocks
    """
    if not text:
        return ""
    
    # Remove <think> blocks (case insensitive, handles nested/multiple)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Remove markdown code fences (multiple types)
    cleaned = cleaned.replace("```json", "").replace("```html", "").replace("```", "").strip()
    
    # Remove any remaining backticks at start/end
    cleaned = cleaned.strip('`').strip()
    
    return cleaned


def extract_json(text: str) -> Optional[Dict]:
    """
    Extract the first valid JSON object from a string.
    Returns None if no valid JSON is found.
    Handles multiple extraction strategies.
    """
    if not text:
        return None
    
    cleaned = clean_llm_response(text)
    
    if "{" not in cleaned:
        return None
    
    # Strategy 1: Try to parse the entire cleaned string
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Find outermost braces and extract
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    
    if end <= start:
        return None
    
    try:
        return json.loads(cleaned[start:end])
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM response")
        
        # Strategy 3: Try to find JSON array if present
        if "[" in cleaned and "]" in cleaned:
            arr_start = cleaned.find("[")
            arr_end = cleaned.rfind("]") + 1
            if arr_end > arr_start:
                try:
                    # If it's an array, wrap it in an object
                    return {"items": json.loads(cleaned[arr_start:arr_end])}
                except json.JSONDecodeError:
                    pass
    
    return None


def call_llm(
    client,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    json_mode: bool = False,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str:
    """
    Call the Groq LLM with automatic retry and exponential backoff.
    
    Args:
        client: Groq client instance
        messages: Chat messages
        model: Model name (defaults to env GROQ_MODEL)
        temperature: Sampling temperature
        max_tokens: Max response tokens
        json_mode: Whether to request JSON output format
        max_retries: Number of retry attempts
        base_delay: Initial delay between retries (doubles each time)
        
    Returns:
        Raw response text from the LLM
        
    Raises:
        Exception: If all retries are exhausted
    """
    model = model or get_active_model_id()
    
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    if json_mode:
        params["response_format"] = {"type": "json_object"}
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(**params)
            raw_text = res.choices[0].message.content
            logger.debug(f"LLM call succeeded (attempt {attempt + 1})")
            return raw_text
            
        except Exception as e:
            last_error = e
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    logger.error(f"LLM call failed after {max_retries} attempts: {last_error}")
    raise last_error


def call_llm_json(
    client,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    fallback: Optional[Dict] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Call the LLM and parse the response as JSON.
    
    Args:
        client: Groq client instance
        messages: Chat messages
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max response tokens
        fallback: Default dict to return if parsing fails
        max_retries: Number of retry attempts
        
    Returns:
        Parsed JSON dict, or fallback if parsing fails
    """
    try:
        raw = call_llm(
            client, messages, model=model,
            temperature=temperature, max_tokens=max_tokens,
            json_mode=True, max_retries=max_retries
        )
        
        logger.debug(f"Raw LLM response (first 200 chars): {raw[:200] if raw else 'None'}")
        
        result = extract_json(raw)
        if result is not None:
            logger.debug("Successfully parsed JSON in json_mode")
            return result
        
        logger.warning("JSON mode response could not be parsed, trying raw extraction")
        
    except Exception as e:
        logger.error(f"LLM JSON call failed: {e}")
    
    # If json_mode failed, try without it
    try:
        raw = call_llm(
            client, messages, model=model,
            temperature=temperature, max_tokens=max_tokens,
            json_mode=False, max_retries=1
        )
        
        logger.debug(f"Fallback raw response (first 200 chars): {raw[:200] if raw else 'None'}")
        
        result = extract_json(raw)
        if result is not None:
            logger.info("Successfully parsed JSON from fallback attempt")
            return result
    except Exception:
        pass
    
    if fallback is not None:
        logger.warning("Returning fallback response")
        return fallback
    
    return {"error": "Failed to get valid JSON from LLM"}
