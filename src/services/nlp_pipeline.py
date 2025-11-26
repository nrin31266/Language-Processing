import json
from src.utils.chunk_utils import chunk_list
from src.services import ai_job_service
from src.services.batch_service import analyze_sentence_batch
from src.s3_storage.cloud_service import upload_json_content


async def process_nlp_sentences(ai_job_id: str, lesson_id: int, transcription_result):
    """
    transcription_result = {
        "segments": [
            {
                "start": 0.5,
                "end": 1.8,
                "text": "Hello everyone.",
                "words": [...]
            },
            ...
        ]
    }
    """

    segments = transcription_result["segments"]

    nlp_results = []

    for chunk in chunk_list(segments, 5):

        # Kiểm tra paused/cancelled
        if await ai_job_service.aiJobWasCancelled(ai_job_id):
            print(f"⚠️ AI Job {ai_job_id} bị hủy khi NLP processing")
            return None

        # Chuyển sang input format cho Gemini
        batch_input = [
            {"order_index": i, "text": s["text"]}
            for i, s in enumerate(chunk, start=chunk[0]["order_index"])
        ]

        batch_output = await analyze_sentence_batch(batch_input)
        nlp_results.extend(batch_output)

    # Upload metadata NLP
    nlp_data_json = json.dumps({"nlp_analyzed": nlp_results}, ensure_ascii=False)
    nlp_metadata_url = upload_json_content(
        nlp_data_json,
        public_id=f"lps/lessons/{lesson_id}/ai-metadata-nlp"
    )

    return nlp_results, nlp_metadata_url
