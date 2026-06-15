import os

OCR_URL = os.getenv("OCR_URL", "http://ocr_service:8000/ocr")
LLM_URL = os.getenv("LLM_URL", "http://llm_service:8001/correct")
SEGMENT_URL = os.getenv("SEGMENT_URL", "http://segment_service:8002/segment")