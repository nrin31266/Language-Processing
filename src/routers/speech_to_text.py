from fastapi import APIRouter, UploadFile, File
import uuid
import os
from fastapi import APIRouter, status, Depends
from typing import List

from src import dto
from src.dto import ApiResponse
from src.auth.dto import UserPrincipal
from src.auth.dependencies import get_current_user, require_roles
import logging
from src.services import speech_to_text_service

router = APIRouter(prefix="/stt", tags=["Speech To Text"])


@router.post("/transcribe")
async def stt_api(audio_path: str):
    result = speech_to_text_service.transcribe(audio_path)

    return ApiResponse.success(data=result)
