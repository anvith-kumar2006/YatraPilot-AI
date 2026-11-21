"""
YatraPilot AI — Murf TTS Integration
Converts text into natural, high-quality speech using Murf Falcon 2.1 API.
"""

import os
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_STREAM_URL = "https://in.api.murf.ai/v1/speech/stream"
MURF_FALLBACK_URL = "https://api.murf.ai/v1/speech/stream"

# In-memory cache for common phrases like the initial greeting
_AUDIO_CACHE = {}

def clean_text_for_speech(text: str) -> str:
    """
    Strips markdown symbols, emojis, and URLs so Murf produces clear, natural speech.
    """
    if not text:
        return ""
    
    # Remove code blocks and inline code
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove markdown links, keep label: [Label](url) -> Label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove raw URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove markdown headers, bullets, bold, italics
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[*_~#>]', '', text)
    text = re.sub(r'^[\-\*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Clean multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length for voice output to keep it natural and conversational (approx 1200 chars)
    if len(text) > 1200:
        # Cut at the nearest sentence end
        truncated = text[:1200]
        last_punct = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        if last_punct > 400:
            text = truncated[:last_punct + 1]
        else:
            text = truncated + "..."
            
    return text


def generate_speech(text: str, voice_id: str = "en-US-natalie", model: str = "falcon-2.1") -> bytes:
    """
    Calls Murf Falcon API to generate MP3 speech bytes from input text.
    """
    api_key = os.getenv("MURF_API_KEY") or MURF_API_KEY
    if not api_key:
        raise ValueError("MURF_API_KEY is not configured in .env")

    cleaned = clean_text_for_speech(text)
    if not cleaned:
        raise ValueError("No speakable text provided")

    # Check cache
    cache_key = f"{voice_id}_{cleaned}"
    if cache_key in _AUDIO_CACHE:
        logger.info(f"✓ Returning cached Murf audio ({len(_AUDIO_CACHE[cache_key])} bytes)")
        return _AUDIO_CACHE[cache_key]

    payload = {
        "text": cleaned,
        "voiceId": voice_id,
        "model": model,
        "locale": "en-US",
        "format": "MP3",
        "channelType": "MONO",
        "sampleRate": 24000
    }

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    logger.info(f"Generating Murf speech for: '{cleaned[:60]}...'")

    # Try Indian endpoint first, then global fallback
    urls_to_try = [MURF_STREAM_URL, MURF_FALLBACK_URL]
    last_error = None

    for url in urls_to_try:
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=30) as resp:
                if resp.status_code == 200:
                    chunks = []
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            chunks.append(chunk)
                    audio_bytes = b"".join(chunks)
                    if len(audio_bytes) > 0:
                        logger.info(f"✓ Murf speech generated successfully ({len(audio_bytes)} bytes)")
                        _AUDIO_CACHE[cache_key] = audio_bytes
                        return audio_bytes
                else:
                    logger.warning(f"Murf API at {url} returned status {resp.status_code}: {resp.text[:300]}")
                    last_error = f"Status {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            logger.warning(f"Murf request to {url} failed: {e}")
            last_error = str(e)

    raise RuntimeError(f"Murf TTS failed: {last_error}")


def get_initial_greeting_audio() -> bytes:
    """
    Returns the pre-generated / cached initial greeting audio for YatraPilot AI.
    """
    greeting_text = (
        "Hi! I'm your YatraPilot AI travel agent. "
        "I'm here to help you plan your journeys, discover destinations, "
        "compare transportation options, check weather, and create your travel itinerary. "
        "Where would you like to go today?"
    )
    return generate_speech(greeting_text)
