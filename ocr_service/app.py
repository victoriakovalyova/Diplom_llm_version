import io
import uvicorn
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

from ocr_engine import OCREngine

app = FastAPI(title="OCR Service for Metric Books")

ocr_engine = None

@app.on_event("startup")
async def load_model():
    global ocr_engine
    ocr_engine = OCREngine()

@app.get("/")
def root():
    return {"service": "OCR for Metric Books", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": ocr_engine is not None}

@app.post("/ocr")
async def recognize(file: UploadFile = File(...)):
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)