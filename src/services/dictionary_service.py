from src.gemini.gemini_service import gemini_generate
import re
import json
PROMPT = """
You are an English lexical validator and dictionary generator.

Analyze the input EXACTLY as written: "{word}"
Do NOT correct spelling. Do NOT guess intended words. Keep the input as-is.

Return JSON ONLY in this exact structure (NO markdown):

{{
  "word": "{word}",
  "isValidWord": true,
  "wordType": "noun | verb | adjective | adverb | phrasal_verb | idiom | proper_noun | abbreviation | symbol | filler | nonsense | multiple",
  "cefrLevel": "A1 | A2 | B1 | B2 | C1 | C2 | unknown",
  "phonetics": {{
    "us": "",
    "uk": ""
  }},
  "definitions": [
    {{
      "type": "",
      "definition": "",
      "vietnamese": "",
      "example": ""
    }}
  ]
}}

STRICT RULES:
1. The JSON MUST be valid JSON. NO markdown, NO extra text.
2. If the input is NOT a valid English word:
   - isValidWord = false
   - wordType = "nonsense" or "symbol"
   - phonetics.us = ""
   - phonetics.uk = ""
   - cefrLevel = "unknown"
   - definitions = []
3. If the input is only symbols (\\ / @ # ! % ^ & * …):
   - wordType = "symbol"
   - isValidWord = false
4. If the input is a nonsense or repeated sequence ("tototo", "zzzqqq"):
   - wordType = "nonsense"
   - isValidWord = false
5. If the input is a VALID English word:
   - definitions MUST include ALL applicable parts of speech.
   - EVERY definition object MUST contain ALL FOUR fields:
       - type
       - definition
       - vietnamese
       - example
     (Never omit any field)
6. NEVER invent Vietnamese that is unnatural. Use neutral, correct Vietnamese.
7. NEVER rewrite or autocorrect the input word.
"""

def clean_json(text: str) -> str:
    """Remove Markdown ```json ... ``` wrapper."""
    text = re.sub(r"^```json", "", text.strip())
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()

def analyze_word(word: str):
    prompt = PROMPT.format(word=word)
    response = gemini_generate(prompt)
    return json.loads(clean_json(response))