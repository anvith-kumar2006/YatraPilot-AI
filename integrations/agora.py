"""
Agora integration — Real RTC token generation + Conversational AI Agent
Uses agora-token-builder for genuine RTC tokens.
"""

import os
import logging
import base64
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

AGORA_API_BASE = "https://api.agora.io"


# ---------------------------------------------------------------------------
# Real RTC token generation using agora-token-builder
# ---------------------------------------------------------------------------

def _generate_real_rtc_token(app_id: str, app_certificate: str, channel: str, uid: int, expire_seconds: int = 3600) -> str:
    """
    Generate a genuine Agora RTC token.
    Requires agora-token-builder package (pip install agora-token-builder).
    """
    try:
        from agora_token_builder import RtcTokenBuilder
        import time

        # Role 1 = Publisher (broadcaster), Role 2 = Subscriber
        ROLE_PUBLISHER = 1

        privilege_expired_ts = int(time.time()) + expire_seconds

        token = RtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            channel,
            uid,
            ROLE_PUBLISHER,
            privilege_expired_ts
        )

        logger.info(f"✓ Generated real Agora RTC token for channel={channel} uid={uid}")
        return token

    except ImportError:
        raise RuntimeError(
            "agora-token-builder not installed. Run: pip install agora-token-builder"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate Agora RTC token: {e}")


class AgoraClient:

    def __init__(self, app_id: str, app_certificate: str, customer_id: str, customer_secret: str):
        self.app_id = app_id
        self.app_certificate = app_certificate
        self.customer_id = customer_id
        self.customer_secret = customer_secret

        if not all([app_id, customer_id, customer_secret]):
            raise ValueError("Missing Agora credentials (AGORA_APP_ID, AGORA_CUSTOMER_ID, AGORA_CUSTOMER_SECRET)")

    def _get_basic_auth(self) -> str:
        credentials = f"{self.customer_id}:{self.customer_secret}"
        return f"Basic {base64.b64encode(credentials.encode()).decode()}"

    def generate_rtc_token(self, channel: str, uid: int = 0, expire_seconds: int = 3600) -> str:
        """
        Generate a genuine Agora RTC token.
        Falls back gracefully with a clear error if APP_CERTIFICATE is missing.
        """
        if not self.app_certificate:
            raise ValueError(
                "AGORA_APP_CERTIFICATE is not set in .env. "
                "A real RTC token cannot be generated without it. "
                "Please add it from your Agora Console."
            )

        return _generate_real_rtc_token(
            app_id=self.app_id,
            app_certificate=self.app_certificate,
            channel=channel,
            uid=uid,
            expire_seconds=expire_seconds
        )

    def start_agent(
        self,
        channel: str,
        llm_api_key: str,
        llm_api_endpoint: str,
        murf_api_key: str,
        user_uid: int = 1000,
        voice_id: str = "Matthew"
    ) -> Dict[str, Any]:
        """
        Start an Agora Conversational AI agent.
        Uses real Agora v2 API schema.
        """
        # Generate real RTC token for the agent (agent uses uid = user_uid + 1 to avoid collision)
        agent_uid = user_uid + 1
        rtc_token = self.generate_rtc_token(channel, uid=agent_uid)

        headers = {
            "Authorization": self._get_basic_auth(),
            "Content-Type": "application/json"
        }

        import uuid as _uuid

        # Correct Agora Conversational AI Agent v2 payload schema
        payload = {
            "name": f"yatra-agent-{_uuid.uuid4().hex[:8]}",
            "properties": {
                "channel": channel,
                "token": rtc_token,
                "agent_rtc_uid": str(agent_uid),
                "remote_rtc_uids": [str(user_uid)],
                "asr": {
                    "vendor": "deepgram",
                    "params": {
                        "url": "wss://api.deepgram.com/v1/listen",
                        "model": "nova-3",
                        "language": "en-US"
                    }
                },
                "llm": {
                    "url": llm_api_endpoint,
                    "api_key": llm_api_key,
                    "system_messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are YatraPilot AI, a premium voice travel concierge. "
                                "Help users plan trips, check weather and find attractions. "
                                "Be concise, warm and conversational — you are speaking, not writing. "
                                "Keep responses to 2-3 sentences unless more detail is explicitly requested."
                            )
                        }
                    ],
                    "params": {
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                },
                "tts": {
                    "vendor": "murf",
                    "params": {
                        "key": murf_api_key,
                        "voice_id": voice_id,
                        "model": "FALCON",
                        "sample_rate": 24000,
                        "base_url": "wss://global.api.murf.ai/v1/speech/stream-input",
                        "locale": "en-US",
                        "rate": 0,
                        "pitch": 0
                    }
                },
                "idle_timeout": 180,
                "max_idle_time": 300
            }
        }

        url = f"{AGORA_API_BASE}/api/conversational-ai-agent/v2/projects/{self.app_id}/join"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            data = response.json()
            agent_id = data.get("agent_id")

            if not agent_id:
                raise ValueError(f"No agent_id in Agora response: {data}")

            logger.info(f"✓ Started Agora agent {agent_id} on channel {channel}")

            # Return the user's RTC token (not agent's) so the browser can join the same channel
            user_token = self.generate_rtc_token(channel, uid=user_uid)

            return {
                "app_id": self.app_id,
                "channel": channel,
                "token": user_token,
                "uid": user_uid,
                "agent_id": agent_id
            }

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            body = e.response.text if e.response is not None else ""
            logger.error(f"✗ Agora start_agent HTTP {status}: {body}")

            # Provide a helpful error message for the most common local dev blocker
            if "blocked network" in body or "127.0.0.1" in body or "localhost" in body:
                raise RuntimeError(
                    "VOICE_BLOCKED_LOCAL: Agora cannot reach the LLM endpoint at 127.0.0.1. "
                    "Voice AI requires a publicly accessible LLM URL. "
                    "To enable voice: deploy the app to a public server, or use ngrok to tunnel your local port."
                ) from e

            raise RuntimeError(f"Agora API error {status}: {body}") from e

        except requests.RequestException as e:
            logger.error(f"✗ Agora start_agent request failed: {e}")
            raise

    def stop_agent(self, agent_id: str) -> bool:
        """Stop an Agora Conversational AI agent."""
        headers = {
            "Authorization": self._get_basic_auth(),
            "Content-Type": "application/json"
        }

        url = f"{AGORA_API_BASE}/api/conversational-ai-agent/v2/projects/{self.app_id}/agents/{agent_id}/leave"

        try:
            response = requests.post(url, headers=headers, json={"mode": "manual"}, timeout=10)
            response.raise_for_status()
            logger.info(f"✓ Stopped Agora agent {agent_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"✗ Agora stop_agent failed: {e}")
            raise


def create_agora_client() -> AgoraClient:
    """Factory function — creates AgoraClient from environment variables."""
    return AgoraClient(
        app_id=os.getenv("AGORA_APP_ID"),
        app_certificate=os.getenv("AGORA_APP_CERTIFICATE"),
        customer_id=os.getenv("AGORA_CUSTOMER_ID"),
        customer_secret=os.getenv("AGORA_CUSTOMER_SECRET")
    )
