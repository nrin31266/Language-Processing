from src.redis import redis_service

# Check in Radis
async def ai_job_was_cancelled(ai_job_id: str) -> bool:
    status = await redis_service.redis_get(f"aiJobStatus:{ai_job_id}")
    print(f"Checking AI Job {ai_job_id} status: {status}")
    if not status:
        return False  # Chưa có gì -> chưa bị hủy

    return status.strip('"') == "CANCELLED"


