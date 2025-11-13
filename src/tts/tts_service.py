import os
from google.cloud import texttospeech
from .config import TTSConfig

tts_config = TTSConfig()

# Load GOOGLE_APPLICATION_CREDENTIALS từ .env
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Khởi tạo Google TTS Client
client = texttospeech.TextToSpeechClient()

# Mapping giọng đọc
VOICE_MAP = {
    "uk": {
        "language": "en-GB",
        "voice": "en-GB-Wavenet-B"  # Giọng nam UK
    },
    "us": {
        "language": "en-US",
        "voice": "en-US-Wavenet-A"  # Giọng nữ US
    }
}

def synthesize_text(text: str, voice_key: str) -> bytes:
    """
    Chuyển văn bản thành giọng nói.
    voice_key: "us" | "uk"
    """

    selected = VOICE_MAP.get(voice_key, VOICE_MAP[tts_config.default_voice])

    synthesis_input = texttospeech.SynthesisInput(text=text)

    # chọn giọng
    voice = texttospeech.VoiceSelectionParams(
        language_code=selected["language"],
        name=selected["voice"]
    )

    # định dạng âm thanh
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # gọi Google API
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content
