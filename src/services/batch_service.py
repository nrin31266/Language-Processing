
import re
import json
from typing import Any, List, Dict


from src.gemini.gemini_service import gemini_generate
from src.gemini.prompt_sentence_batch import SENTENCE_PROMPT_TEMPLATE
from src.gemini.prompt_word_analysis_batch import WORD_PROMPT_TEMPLATE


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


async def analyze_word(word: str):
    prompt = WORD_PROMPT_TEMPLATE.substitute(word=word)
    resp = await gemini_generate(prompt)
    if not isinstance(resp, dict):
        raise ValueError(f"Gemini response must be a JSON object: {resp}")
    return resp
    


