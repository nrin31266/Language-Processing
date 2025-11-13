from fastapi import APIRouter, Query
from src.services.dictionary_service import analyze_word
from src.dto import ApiResponse


router = APIRouter(prefix="/dictionary", tags=["Dictionary NLP"])



@router.get("/analyze")
def analyze(word: str = Query(..., description="Word to analyze")):
    result = analyze_word(word)
    return ApiResponse.success(data=result)
