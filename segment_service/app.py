import os
import cv2
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from segment import TableSegmenter
from cell_splitter import CellSplitter

app = FastAPI(
    title="Segmentation API for Metric Books",
    description="Сегментация метрических книг: поиск вертикальных/горизонтальных линий и нарезка ячеек",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём папки
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Глобальные экземпляры
segmenter = TableSegmenter()
splitter = CellSplitter()


@app.get("/")
async def root():
    return {
        "service": "Segmentation API for Metric Books",
        "status": "running",
        "endpoints": {
            "/segment": "POST - загрузить изображение",
            "/get_image/{filename}": "GET - получить изображение по имени файла"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/get_image/{filename}")
async def get_image(filename: str):
    """Безопасное получение изображения по имени файла"""
    # Защита от path traversal
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="Некорректное имя файла")
    
    # Проверяем разные возможные папки
    possible_paths = [
        os.path.join("output", filename),
        os.path.join("output", "cells", filename),
    ]
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail=f"Файл {filename} не найден")


@app.post("/segment")
async def segment_image(file: UploadFile = File(...)):
    allowed_formats = ["image/jpeg", "image/png", "image/tiff", "image/bmp"]
    if file.content_type not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат. Допустимые: {allowed_formats}"
        )
    
    try:
        session_id = str(uuid.uuid4())[:8]
        base_name = f"{session_id}_{file.filename}"
        
        input_path = os.path.join("input", base_name)
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"📷 Получено изображение: {file.filename}")
        
        result_img, lines = segmenter.segment(input_path)
        
        # Сохраняем сегментированное изображение
        segmented_filename = f"segmented_{base_name}"
        output_img_path = os.path.join("output", segmented_filename)
        cv2.imwrite(output_img_path, result_img)
        
        # Получаем горизонтальные линии
        img_cropped = segmenter.crop_header_and_edges(cv2.imread(input_path))
        _, y_lines = segmenter.draw_horizontal_lines(img_cropped, lines)
        
        # Нарезаем ячейки
        cells = splitter.split_cells(input_path, lines, y_lines, page_num=1)
        saved_files, json_path = splitter.save_cells(cells, "output", base_name)
        
        response_data = {
            "status": "success",
            "session_id": session_id,
            "original_filename": file.filename,
            "segmented_image_url": f"/get_image/{segmented_filename}",
            "vertical_lines_count": len(lines),
            "horizontal_lines_count": len(y_lines),
            "cells_count": len(cells),
            "metadata_json": json_path,
            "cells": [
                {
                    "row": cell["row"],
                    "col_name": cell["col_name_rus"],
                    "filename": cell["filename"],
                    "url": f"/get_image/{cell['filename']}"
                }
                for cell in cells
            ]
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)