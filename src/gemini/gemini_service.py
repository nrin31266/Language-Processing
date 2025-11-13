from google import genai
from google.genai.types import GenerateContentConfig
from src.gemini.config import config


# Tạo client sau khi cấu hình API key
client = genai.Client(api_key=config.api_key)

def gemini_generate(prompt: str):
    try:
        response = client.models.generate_content(
            model=config.model,
            contents=prompt
        )
        return response.text

    except Exception as e:
        raise RuntimeError(f"Gemini API Error: {str(e)}")
