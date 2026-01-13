# src/services/word_analysis_service.py
import os
import time
import asyncio
from src.redis.redis_client import redis_client as redis
from src.services.batch_service import analyze_word
from src.dto import WordAnalyzedDto
from src.s3_storage.cloud_service import upload_file
from src.tts.tts_service import synthesize_text
QUEUE = "queue:vocab"
PROC = "processing:vocab"
ENABLE = "enable_vocab_queue"

RUN_WORD_WORKER = os.getenv("RUN_WORD_WORKER", "0") == "1"
PAUSE_SLEEP = int(os.getenv("WORD_QUEUE_PAUSE_SLEEP", "5"))
POP_TIMEOUT = int(os.getenv("WORD_QUEUE_POP_TIMEOUT", "2"))
SLEEP_ON_EMPTY = int(os.getenv("WORD_QUEUE_SLEEP_ON_EMPTY", "2"))

def log(msg: str):
    print(f"[Vocab Queue][pid={os.getpid()}] {msg}")

async def enabled() -> bool:
    v = await redis.get(ENABLE)
    return (v is None) or (v == "1")

async def worker_loop():
    log("Worker loop started")
    while True:
        if not await enabled():
            log("Disabled, sleeping...")
            await asyncio.sleep(PAUSE_SLEEP)
            continue

        word = await redis.brpoplpush(QUEUE, PROC, timeout=POP_TIMEOUT)
        if word is None:
            await asyncio.sleep(SLEEP_ON_EMPTY)
            continue
        # conver word to str if bytes
        if isinstance(word, bytes):
            log(f"Got word (bytes): {word}")
            word = word.decode("utf-8")

        # double-check enable
        if not await enabled():
            await redis.lrem(PROC, 1, word)
            await redis.rpush(QUEUE, word)
            await asyncio.sleep(PAUSE_SLEEP)
            continue

        start_time = time.time()
        try:
            result = await analyze_word(word)   # result là dict hoặc object
            data = WordAnalyzedDto.model_validate(result)
            if not data.displayWord is None: 
                 # chay song song 
                audio_us, audio_uk = await asyncio.gather(
                    synthesize_text(data.displayWord, "us"),
                    synthesize_text(data.displayWord, "uk"),
                )
                #upload both 
                url_us, url_uk = await asyncio.gather(
                    upload_file(audio_us, f"vocab/{word}_us", resource_type="video"),
                    upload_file(audio_uk, f"vocab/{word}_uk", resource_type="video"),
                )
                log(f"Uploaded audio: {word} -> US: {url_us}, UK: {url_uk}")
                # attach audio urls
                data.phonetics.audioUs = url_us
                data.phonetics.audioUk = url_uk
            # TODO: gửi backend lưu data
            log(f"Final data for word {word}: {data}")
        except Exception as e:
            log(f"Error: {word} -> {e}")
        finally:
            await redis.lrem(PROC, 1, word)
            log(f"Done in {time.time() - start_time:.2f}s")

async def start_if_enabled_env():
    if RUN_WORD_WORKER:
        log("RUN_WORD_WORKER=1 -> starting worker task")
        return asyncio.create_task(worker_loop())
    else:
        log("RUN_WORD_WORKER!=1 -> worker not started")
        return None
        