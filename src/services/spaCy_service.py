
import spacy
import asyncio

from src.errors.base_error_code import BaseErrorCode


SPACY_MODEL_NAME = "en_core_web_sm"
# global model instance
_spacy_model = None

# LAZY LOAD MODEL
def _ensure_spacy_model_loaded():
    global _spacy_model

    if _spacy_model is None:
        print(f"[spaCy] Loading model '{SPACY_MODEL_NAME}'...")
        _spacy_model = spacy.load(SPACY_MODEL_NAME)
        print("✅ [spaCy] Model loaded successfully!")

def _word_analysis_sync(word: str, context: str | None = None) -> dict:
    if not word or not word.strip():
        raise BaseException(BaseErrorCode.INVALID_REQUEST, "Word must be a non-empty string.")
    _ensure_spacy_model_loaded()
    
    word = word.strip()
    text = context if context else word 
    
    try:
        doc = _spacy_model(text)
        for token in doc:
            if token.text.lower() == word.lower():
                return {
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_,
                    "ent_type": token.ent_type_,
                }
        token = _spacy_model(word)[0] # fallback to analyzing the word alone if not found in context
        return {
            "text": token.text,
            "lemma": token.lemma_,
            "pos": token.pos_,
            "tag": token.tag_,
            "dep": token.dep_,
            "ent_type": token.ent_type_,
        }
                
    except Exception as e:
        raise BaseException(BaseErrorCode.INTERNAL_ERROR, f"spaCy analysis failed: {str(e)}")

# ASYNC WRAPPER
async def analyze_word(word: str, context: str | None = None) -> dict:
    return await asyncio.to_thread(_word_analysis_sync, word, context)

# PRELOAD MODEL AT STARTUP
def preload_spacy_model():
    try:
        _ensure_spacy_model_loaded()
    except Exception as e:
        print(f"Failed to preload spaCy model: {e}")

# UNLOAD MODEL
def unload_spacy_model():
    global _spacy_model
    _spacy_model = None