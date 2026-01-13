import os
import asyncio
from google.cloud import texttospeech
from .config import TTSConfig

tts_config = TTSConfig()


cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not cred:
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS chưa được set")
if not os.path.exists(cred):
    raise RuntimeError(f"Không thấy file credentials: {cred}")

client = texttospeech.TextToSpeechClient()

VOICE_MAP = {
    "uk": {"language": "en-GB", "voice": "en-GB-Wavenet-A"},
    "us": {"language": "en-US", "voice": "en-US-Wavenet-B"},
}

def _synthesize__text_sync(text: str, voice_key: str) -> bytes:
    key = voice_key if voice_key in VOICE_MAP else tts_config.default_voice
    if key not in VOICE_MAP:
        key = "us"

    selected = VOICE_MAP[key]

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=selected["language"],
        name=selected["voice"]
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content

async def synthesize_text(text: str, voice_key: str) -> bytes:
    # để async thật sự (không block), chạy sync code trong thread
    return await asyncio.to_thread(_synthesize__text_sync, text, voice_key)
