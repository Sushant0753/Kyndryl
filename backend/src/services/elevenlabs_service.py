import requests
from typing import Optional
from configs.config import ElevenLabsSettings
from lib.logger import logger


class ElevenLabsService:
    """Service for ElevenLabs Text-to-Speech conversion"""

    def __init__(self):
        self.settings = ElevenLabsSettings()

        # Check if ElevenLabs is configured
        if not self.settings.ELEVENLABS_API_KEY:
            logger.warning("ElevenLabs API key not configured, TTS will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"ElevenLabs TTS Service initialized: Voice ID={self.settings.ELEVENLABS_VOICE_ID}")

    def text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs API

        Args:
            text: The text to convert to speech

        Returns:
            bytes: Audio content in MP3 format, or None if failed
        """
        if not self.enabled:
            logger.warning("ElevenLabs TTS is disabled - API key not configured")
            return None

        if not text or not text.strip():
            logger.warning("Empty text provided for TTS conversion")
            return None

        # Truncate text if too long (ElevenLabs has limits)
        max_length = 2500
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + "..."
            logger.info(f"Text truncated to {len(text)} characters for TTS")

        try:
            # Prepare the API request
            url = f"{self.settings.ELEVENLABS_API_URL}/text-to-speech/{self.settings.ELEVENLABS_VOICE_ID}"

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.settings.ELEVENLABS_API_KEY
            }

            payload = {
                "text": text,
                "model_id": self.settings.ELEVENLABS_MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            logger.info(f"Converting text to speech: {len(text)} characters")

            # Make the API request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60  # TTS can take longer than normal API calls
            )
            response.raise_for_status()

            # Return the audio content
            audio_content = response.content
            logger.info(f"TTS conversion successful: {len(audio_content)} bytes")

            return audio_content

        except requests.exceptions.RequestException as e:
            logger.error(f"ElevenLabs API request failed: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}", exc_info=True)
            return None

    def get_voice_info(self) -> Optional[dict]:
        """
        Get information about the configured voice

        Returns:
            dict: Voice information or None if failed
        """
        if not self.enabled:
            return None

        try:
            url = f"{self.settings.ELEVENLABS_API_URL}/voices/{self.settings.ELEVENLABS_VOICE_ID}"

            headers = {
                "Accept": "application/json",
                "xi-api-key": self.settings.ELEVENLABS_API_KEY
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            voice_info = response.json()
            logger.info(f"Voice info retrieved: {voice_info.get('name', 'Unknown')}")

            return voice_info

        except Exception as e:
            logger.error(f"Failed to get voice info: {e}", exc_info=True)
            return None

    def is_available(self) -> bool:
        """
        Check if ElevenLabs service is available

        Returns:
            bool: True if service is configured and available
        """
        return self.enabled