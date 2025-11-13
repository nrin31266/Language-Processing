from typing import List
from fastapi import APIRouter, status, Depends
from src import dto
from src.dto import ApiResponse
from src.services import media_service
from src.auth.dto import UserPrincipal
from src.auth.dependencies import get_current_user, require_roles
import logging

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/media", tags=["media"])


# @router.post("/download/audio", response_model=ApiResponse[dto.MediaAudioResponse], status_code=status.HTTP_202_ACCEPTED)
# def download_youtube_audio(
#     rq: dto.MediaAudioCreateRequest,
#     # current_user: UserPrincipal = Depends(require_roles(["ROLE_ADMIN"])),
# ):
#     # logger.info(f"User {current_user.username} is downloading audio from {rq.input_url} with type {rq.input_type}")
#     media_audio = media_service.download_audio(rq)

#     return ApiResponse.success(data=media_audio)

@router.post("/download/audio_url", response_model=ApiResponse[dto.AudioInfo], status_code=status.HTTP_202_ACCEPTED)
def download_audio_url(
    audio_url: str,
    # current_user: UserPrincipal = Depends(require_roles(["ROLE_ADMIN"])),
):
    # logger.info(f"User {current_user.username} is downloading audio from {rq.input_url} with type {rq.input_type}")
    audio_info = media_service.download_audio_file(audio_url)

    return ApiResponse.success(data=audio_info)