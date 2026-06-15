import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from orchestrator import OCRPipeline

# Создаём папки
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

app = FastAPI(
    title="Orchestrator Service",
    description="Оркестратор: сегментация → OCR → LLM для метрических книг",
    version="1.0.0"
)

# Разрешаем CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Orchestrator Service",
        "status": "running",
        "endpoints": {
            "/process": "POST - загрузить изображение, получить полный результат (сегментация + OCR + LLM)"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    """
    Полный пайплайн обработки метрической книги:
    1. Сегментация → ячейки
    2. OCR → распознавание текста
    3. LLM → постобработка
    
    Возвращает JSON с результатами всех этапов
    """
    allowed_formats = ["image/jpeg", "image/png", "image/tiff", "image/bmp"]
    if file.content_type not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат. Допустимые: {allowed_formats}"
        )
    
    try:
        # Сохраняем временный файл
        session_id = str(uuid.uuid4())[:8]
        temp_filename = f"{session_id}_{file.filename}"
        temp_path = os.path.join("input", temp_filename)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"📷 Получено изображение: {file.filename}")
        print(f"🆔 Сессия: {session_id}")
        
        # Запускаем пайплайн
        pipeline = OCRPipeline(session_id=session_id)
        result = pipeline.run(temp_path)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)