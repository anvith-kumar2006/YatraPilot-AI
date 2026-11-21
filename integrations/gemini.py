"""
Working Gemini integration for hackathon
Uses gemini-2.5-flash via REST API
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class GeminiAgent:
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self.tools = {}
        self.tool_schemas = []
    
    def register_tool(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        self.tools[name] = func
        self.tool_schemas.append({"name": name, "description": description, "parameters": parameters})
        logger.info(f"✓ Registered tool: {name}")
    
    def chat_with_tools(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, max_iterations: int = 5) -> str:
        conversation = []
        
        if system_prompt:
            conversation.append({"role": "user", "parts": [{"text": system_prompt}]})
            conversation.append({"role": "model", "parts": [{"text": "Understood. I am YatraPilot AI, ready to assist with travel planning."}]})
        
        for msg in messages:
            content = msg.get("content", "")
            if not content or not str(content).strip():
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            conversation.append({"role": role, "parts": [{"text": str(content).strip()}]})

        if not conversation:
            return "Hello! Where would you like to travel next? I can help with itineraries, weather, and attractions."
        
        candidate_models = [
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash"
        ]

        last_error = None
        for model_name in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={self.api_key}"
                payload = {"contents": conversation, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}}
                
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 429:
                    logger.warning(f"Gemini model {model_name} rate-limited (429), attempting next candidate...")
                    continue
                response.raise_for_status()
                data = response.json()
                
                if not data.get("candidates"):
                    return "No response from AI"
                
                text = ""
                for part in data["candidates"][0].get("content", {}).get("parts", []):
                    text += part.get("text", "")
                
                logger.info(f"✓ Gemini response ready from {model_name}")
                return text
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                if response.status_code == 429:
                    continue
                break
            except Exception as e:
                last_error = e
                logger.error(f"✗ Gemini error with {model_name}: {e}")
                continue

        logger.error(f"✗ All Gemini models exhausted. Last error: {last_error}")
        raise RuntimeError(f"Gemini error: {last_error}")
    
    def stream_chat_with_tools(self, messages, system_prompt=None, max_iterations=5):
        try:
            yield self.chat_with_tools(messages, system_prompt, max_iterations)
        except Exception as e:
            yield f"Error: {e}"


def create_gemini_agent():
    return GeminiAgent()
