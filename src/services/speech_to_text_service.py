import whisperx
import torch
import os
import librosa
import json
from src import dto
from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🔄 [WhisperX] Loading model... with device {device}")

whisper_model = whisperx.load_model(
    "base.en",
    device,
    compute_type="float16" if device == "cuda" else "float32"
)
print("✨ [WhisperX] Model loaded successfully!")


def get_audio_duration(audio_file):
    if not os.path.exists(audio_file):
        raise BaseException(BaseErrorCode.NOT_FOUND, f"File not found: {audio_file}")
    try:
        y, sr = librosa.load(audio_file, sr=None)
        return librosa.get_duration(y=y, sr=sr)
    except Exception:
        raise BaseException(BaseErrorCode.INVALID_AUDIO_FILE, f"Invalid audio file: {audio_file}")




def transcribe(audio_path: str):
    # 1. WhisperX transcription
    result = whisper_model.transcribe(audio_path, batch_size=4)

    # 2. WhisperX alignment
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    aligned = whisperx.align(
        result["segments"], align_model, metadata, audio_path, device
    )

    # 🧹 Chỉ xóa đúng trường 'word_segments'
    if isinstance(aligned, dict):
        aligned.pop("word_segments", None)

    return aligned

