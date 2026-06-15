import pytesseract
from PIL import Image
import numpy as np


class OCREngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def predict(self, image: np.ndarray):
        """Распознавание через Tesseract"""
        pil_image = Image.fromarray(image)
        
        # Настройки для русского языка + старых документов
        custom_config = r'--oem 3 --psm 6 -l rus'
        
        text = pytesseract.image_to_string(pil_image, config=custom_config)
        
        # Разбиваем на строки
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return lines
    
    def parse_result(self, raw_lines):
        """Форматирование результата"""
        result = []
        for idx, line in enumerate(raw_lines):
            result.append({
                "line_number": idx + 1,
                "text": line,
                "confidence": None,
                "bbox": []
            })
        return result