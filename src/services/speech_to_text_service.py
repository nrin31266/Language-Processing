# import whisperx
# import torch
# import os
# import librosa
# import json
# from src import dto
# from src.errors.base_exception import BaseException
# from src.errors.base_error_code import BaseErrorCode
# device = "cuda" if torch.cuda.is_available() else "cpu"

# print(f"🔄 [WhisperX] Loading model... with device {device}")

# whisper_model = whisperx.load_model(
#     "base.en",
#     device,
#     compute_type="float16" if device == "cuda" else "float32"
# )
# print("✨ [WhisperX] Model loaded successfully!")


# def get_audio_duration(audio_file):
#     if not os.path.exists(audio_file):
#         raise BaseException(BaseErrorCode.NOT_FOUND, f"File not found: {audio_file}")
#     try:
#         y, sr = librosa.load(audio_file, sr=None)
#         return librosa.get_duration(y=y, sr=sr)
#     except Exception:
#         raise BaseException(BaseErrorCode.INVALID_AUDIO_FILE, f"Invalid audio file: {audio_file}")




# def transcribe(audio_path: str):
#     # 1. WhisperX transcription
#     result = whisper_model.transcribe(audio_path, batch_size=4)

#     # 2. WhisperX alignment
#     align_model, metadata = whisperx.load_align_model(
#         language_code=result["language"], device=device
#     )
#     aligned = whisperx.align(
#         result["segments"], align_model, metadata, audio_path, device
#     )

#     return get_all_words(aligned)
# import re
# FILLER_WORDS = {"uh", "um", "hmm", "mmm", "uhh", "uhhuh", "erm", "ah"}
# def clean_word(word):
#     # Bỏ khoảng trắng
#     w = word.strip()

#     # Giữ các ký tự hợp lệ: chữ cái, số, dấu nháy ', dấu gạch -
#     w = re.sub(r"[^a-zA-Z0-9'\-]", "", w)

#     # Bỏ filler words
#     if w.lower() in FILLER_WORDS:
#         return None

#     # Không lowercase ở bước này
#     # để giữ tên riêng, brand, viết tắt (AI, NASA)
    
#     return w

# def get_all_words(aligned_result):
#     words = []
#     seen = set()

#     for segment in aligned_result["word_segments"]:
#         raw = segment["word"]
#         w = clean_word(raw)

#         # bỏ None, rỗng
#         if not w:
#             continue

#         # kiểm tra duplicate toàn list
#         wl = w.lower()  # so sánh theo lowercase
#         if wl in seen:
#             continue
        
#         seen.add(wl)
#         words.append(w)

#     return words
