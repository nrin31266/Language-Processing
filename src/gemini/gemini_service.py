import google.generativeai as genai
from src.gemini.config import config
import json
# Khởi tạo API key
genai.configure(api_key=config.api_key)

# Model dùng cho NLP 5 câu/batch
model = genai.GenerativeModel(
    model_name=config.model,  # ví dụ: "gemini-2.5-flash"
    generation_config={
        "temperature": 0,
        "response_mime_type": "application/json"
    }
)

def gemini_generate(prompt: str):
    response = model.generate_content(prompt)
    return json.loads(response.text)   # ✔ luôn trả dict
