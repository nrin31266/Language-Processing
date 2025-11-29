# src/services/speech_to_text_service.py

import asyncio
import os
import json

import librosa
import torch
import whisperx

from src import dto
from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🔄 [WhisperX] Loading model... with device {device}")

whisper_model = whisperx.load_model(
    "base.en",
    device,
    compute_type="float16" if device == "cuda" else "float32",
)

print("✨ [WhisperX] Model loaded successfully!")


# =========================
#  SYNC IMPLEMENTATION
# =========================

def _get_audio_duration_sync(path: str) -> float:
    if not os.path.exists(path):
        raise BaseException(BaseErrorCode.NOT_FOUND, f"File not found: {path}")
    try:
        y, sr = librosa.load(path, sr=None)
        return librosa.get_duration(y=y, sr=sr)
    except Exception:
        raise BaseException(
            BaseErrorCode.INVALID_AUDIO_FILE,
            f"Invalid audio file: {path}",
        )


def _transcribe_sync(audio_path: str):
    """
    Hàm sync gọi WhisperX để transcribe + align.
    Dùng nội bộ, bọc bởi async transcribe().
    """
    # 1. WhisperX transcription
    result = whisper_model.transcribe(audio_path, batch_size=4)

    # 2. WhisperX alignment
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device,
    )
    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio_path,
        device,
    )

    # 🧹 Chỉ xóa đúng trường 'word_segments'
    if isinstance(aligned, dict):
        aligned.pop("word_segments", None)

    return aligned


# =========================
#  ASYNC WRAPPERS
# =========================

async def get_audio_duration(path: str) -> float:
    """
    Async wrapper cho việc lấy duration audio.
    Chạy trong thread pool để không block event loop.
    """
    return await asyncio.to_thread(_get_audio_duration_sync, path)


async def transcribe(audio_path: str):
    """
    Async wrapper cho WhisperX transcribe + align.
    Chạy trong thread pool để không block event loop.
    Trả về dict (aligned result).
    """
    return await asyncio.to_thread(_transcribe_sync, audio_path)
