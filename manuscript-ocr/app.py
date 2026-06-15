import io
import uvicorn
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

from ocr_engine import OCREngine

app = FastAPI(
    title="Manuscript OCR Service for Metric Books",
    description="Распознавание рукописного текста с использованием manuscript-ocr",
    version="2.0.0"
)

ocr_engine = None

@app.on_event("startup")
async def load_model():
    global ocr_engine
    print("Инициализация OCR сервиса...")
    ocr_engine = OCREngine()
    print("OCR сервис готов к работе")

@app.get("/")
def root():
    return {
        "service": "Manuscript OCR for Metric Books",
        "status": "running",
        "engine": "manuscript-ocr"
    }

@app.get("/health")
def health():
    if ocr_engine is None:
        return {"status": "error", "message": "Model not loaded"}
    return {"status": "healthy", "engine": "manuscript-ocr"}

@app.post("/ocr")
async def recognize(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_np = np.array(image)

        raw = ocr_engine.predict(image_np)
        lines = ocr_engine.parse_result(raw)

        return JSONResponse(content={
            "status": "success",
            "file_name": file.filename,
            "num_blocks": len(lines),
            "lines": lines
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)