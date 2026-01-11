
import re
import json
from typing import Any, List, Dict

from src.gemini.gemini_service import gemini_generate
from src.gemini.prompt_sentence_batch import SENTENCE_PROMPT_TEMPLATE


async def analyze_sentence_batch(sentences_chunk: List[Dict[str, Any]]):
    # TẠO PROMPT
    prompt = SENTENCE_PROMPT_TEMPLATE.substitute(
        max_sentences=len(sentences_chunk),
        sentences_json=json.dumps(sentences_chunk, ensure_ascii=False)
    )

    # GỌI GEMINI ASYNC
    resp = await gemini_generate(prompt)

    if not isinstance(resp, list):
        raise ValueError(f"Gemini response must be a JSON array: {resp}")

    return resp


def clean_json(text: str) -> str:
    """Remove Markdown ```json ... ``` wrapper."""
    text = re.sub(r"^```json", "", text.strip())
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()



# PROMPT_TEMPLATE = Template("""
# You are an English lexical validator and dictionary generator.

# Analyze the input EXACTLY as written: "$word"
# Do NOT correct spelling. Do NOT guess intended words. Keep the input as-is.

# Return JSON ONLY in this exact structure (NO markdown):

# {
#   "word": "$word",
#   "isValidWord": true,
#   "wordType": "normal | proper_noun | brand | abbreviation | symbol | filler | nonsense",
#   "cefrLevel": "A1 | A2 | B1 | B2 | C1 | C2 | unknown",
#   "phonetics": {
#     "us": "",
#     "uk": ""
#   },
#   "definitions": [
#     {
#       "type": "",
#       "definition": "",
#       "vietnamese": "",
#       "example": ""
#     }
#   ]
# }

# STRICT RULES:
# 1. Output MUST be valid JSON. No markdown, no commentary, no text before or after.
# 2. NEVER modify the input word. Keep it exactly as written.
# 3. If the input is NOT a valid English word:
#    - isValidWord = false
#    - wordType = "nonsense" or "symbol" or "abbreviation" as appropriate
#    - phonetics.us = ""
#    - phonetics.uk = ""
#    - cefrLevel = "unknown"
#    - definitions = []
# 4. If the input contains ONLY symbols (like @, #, !, %, ^, &, *):
#    - wordType = "symbol"
#    - isValidWord = false
# 5. If the input is random or nonsense ("zzzqqq", "tototo", "asdfgh"):
#    - wordType = "nonsense"
#    - isValidWord = false
# 6. If the input is a valid English word:
#    - isValidWord = true
#    - wordType SHOULD NOT be "noun" or "verb". Those belong inside definitions[].  
#      wordType is only: normal / proper_noun / brand / abbreviation / filler / symbol / nonsense
#    - definitions MUST include all relevant parts of speech.
# 7. Each definition object MUST contain ALL fields:
#    - type
#    - definition
#    - vietnamese
#    - example
#    (Never leave any field absent)
# 8. Vietnamese translation MUST be natural and correct. No machine-like or weird phrasing.
# 9. Do NOT fabricate phonetics if uncertain — leave as "".
# 10. NEVER autocorrect capitalization. Use the input exactly.
# """)


  

# async def analyze_word(word: str):
#     """
#     Phân tích 1 từ, gọi Gemini async.
#     Trả về dict JSON (đã parse) theo schema ở PROMPT_TEMPLATE.
#     """
#     prompt = PROMPT_TEMPLATE.substitute(word=word)

#     resp = await gemini_generate(prompt)

#     # gemini_generate đã json.loads → resp thường là dict
#     if isinstance(resp, dict):
#         return resp

#     # Fallback: nếu vì lý do gì đó Gemini trả string JSON
#     if isinstance(resp, str):
#         return json.loads(clean_json(resp))

#     # Nếu format lạ thì cố parse lại
#     return json.loads(clean_json(str(resp)))

