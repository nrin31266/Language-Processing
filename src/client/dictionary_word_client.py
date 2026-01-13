import os
import httpx

BASE_URL = "http://localhost:8082/api/internal/dictionary-words"
WORKER_KEY = os.getenv("WORKER_API_KEY", "")

async def save_data(data: dict):
    headers = {"X-Worker-Key": WORKER_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/result", json=data, headers=headers)
        r.raise_for_status()
