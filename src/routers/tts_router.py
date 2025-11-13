from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from src.tts.tts_service import synthesize_text
import io

router = APIRouter(prefix="/tts", tags=["Text-To-Speech"])

@router.api_route("/", methods=["GET", "POST"])
def text_to_speech(
    text: str = Query(..., description="Nội dung cần đọc"),
    voice: str = Query("us", description="Chọn giọng: us (nữ US), uk (nam UK)")
):
    """
    API chuyển văn bản thành giọng nói.
    """

    audio_bytes = synthesize_text(text, voice)

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=tts.mp3"}
    )
