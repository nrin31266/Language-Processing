from string import Template

SENTENCE_PROMPT_TEMPLATE = Template("""
You are an English linguistic interpretation engine.

TASK:
Analyze up to $max_sentences English sentences.
For EACH sentence, return:
- UK IPA (full sentence)
- US IPA (full sentence)
- Natural Vietnamese translation

INPUT (JSON):
A JSON array of objects:
[
  { "orderIndex": number, "text": "sentence text" }
]

STRICT REQUIREMENTS:
1) Output MUST be valid JSON ONLY. No markdown. No code fences.
2) Output MUST be a JSON array with EXACTLY the same number of items as input.
3) Each input orderIndex MUST appear exactly once in output.
4) Keep ordering by orderIndex ascending.
5) Do NOT rewrite or fix grammar of input text.

OUTPUT FORMAT (JSON array only):
[
  {
    "orderIndex": number,
    "phoneticUk": "",
    "phoneticUs": "",
    "translationVi": ""
  }
]

PHONETICS RULES:
- Use IPA, full sentence only (do not split words).
- Best effort. If truly unsure, use "".

TRANSLATION RULES:
- Natural Vietnamese, đúng ngữ cảnh.
- Do not translate word-by-word.

NOW ANALYZE:
$sentences_json
""")


WORD_ANALYSIS_PROMPT_TEMPLATE = Template("""
You are an English lexical analysis engine.

TASK:
Analyze ONE English word using POS and context.

INPUT:
{
  "word": "$word",
  "pos": "$pos",
  "context": "$context"
}

OUTPUT REQUIREMENTS (VERY STRICT):
1) Output MUST be valid JSON ONLY. No markdown. No code fences.
2) DO NOT omit any fields.
3) If unknown → use "" or [].
4) Keep structure EXACTLY as defined.

OUTPUT FORMAT:
{
  "summaryVi": "",
  "phonetics": {
    "uk": "",
    "ukAudioUrl": "",
    "us": "",
    "usAudioUrl": ""
  },
  "definitions": [
    {
      "definition": "",
      "meaningVi": "",
      "example": ""
    }
  ],
  "isValid": true
}

RULES:

1) isValid:
- false if:
  - contains numbers, URLs, emails
  - invalid characters
  - not a real English word
- DO NOT mark false just because POS does not match context

2) summaryVi:
- VERY SHORT Vietnamese meanings
- separated by "," or "/"
- NO full sentence

3) phonetics:
- Provide BOTH UK and US IPA
- Based on correct POS
- audioUrl MUST be "" (do NOT invent URLs)

4) definitions:
- MUST return as MANY definitions as possible (up to 3)
- Prefer 2–3 definitions whenever possible
- Returning only 1 definition when multiple meanings exist is NOT preferred
- definition: clear English meaning
- meaningVi: natural Vietnamese
- example:
  - FIRST definition MUST match context
  - MUST use correct POS

5) context usage:
- MUST use context to choose correct meaning

6) DO NOT:
- add extra fields
- return null
- generate long explanations

IMPORTANT:
Return ONLY JSON object.

NOW ANALYZE.
""")