import asyncio
from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core import ApiError
from Sakura.Core.config import ELEVENLABS_API_KEY, VOICE_ID
from Sakura.Core.logging import logger

client = AsyncElevenLabs(api_key=ELEVENLABS_API_KEY)

async def generate_voice(text: str) -> bytes | None:
    """
    Generates voice from text using the ElevenLabs API.

    Args:
        text: The text to convert to speech.

    Returns:
        The audio data in bytes, or None if an error occurred.
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("ElevenLabs API key is not configured.")
        return None

    try:
        logger.info(f"Generating voice for text: '{text[:30]}...'")
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id="eleven_multilingual_v2"
        )

        audio_bytes = b""
        async for chunk in audio_stream:
            audio_bytes += chunk

        logger.info("Voice generation successful.")
        return audio_bytes

    except ApiError as e:
        logger.error(f"ElevenLabs API error: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during voice generation: {e}")
        return None