# src/gemini/gemini_service.py
import asyncio
import json
import google.generativeai as genai
from src.gemini.config import config

# Khởi tạo API key
genai.configure(api_key=config.api_key)

# Model dùng cho NLP 
model = genai.GenerativeModel(
    model_name=config.model,  # Ex: "gemini-2.5-flash"
    generation_config={
        "temperature": 0,
        "response_mime_type": "application/json",
    },
    system_instruction="Respond with valid JSON only. No markdown. No extra text.",
)


async def gemini_generate(prompt: str):
    """
    Async wrapper cho Gemini.
    Chạy generate_content ở thread pool để không block event loop,
    sau đó parse JSON và trả về dict.
    """
    # sync → đưa sang thread khác
    response = await asyncio.to_thread(model.generate_content, prompt)

    # response.text là chuỗi JSON (theo response_mime_type)
    return json.loads(response.text)  # Luôn trả về dict
