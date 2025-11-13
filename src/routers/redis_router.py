from fastapi import APIRouter
from src.redis.redis_service import redis_get, redis_set, redis_ping

router = APIRouter(prefix="/redis")

@router.get("/ping")
async def ping():
    return {"result": await redis_ping()}

@router.get("/set")
async def set():
    await redis_set("name", "Rin", 60)
    return {"msg": "saved"}

@router.get("/get")
async def get():
    return {"value": await redis_get("name")}
