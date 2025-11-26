from typing import List
from fastapi import APIRouter, status, Depends
from src import dto
from src.dto import ApiResponse
from src.auth.dto import UserPrincipal
from src.auth.dependencies import get_current_user, require_roles
import logging
from datetime import datetime
import uuid 
router = APIRouter(prefix="/ai-jobs", tags=["ai-jobs"])

@router.post("/", response_model=ApiResponse[dto.AIJobResponse], status_code=status.HTTP_201_CREATED)
def create_ai_job(
):
    # Placeholder implementation
    ai_job = dto.AIJobResponse(
        id= str(uuid.uuid4()),
        user_id="example_user",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    return ApiResponse.success(data=ai_job)