import numpy as np
from PIL import Image
from manuscript import Pipeline

class OCREngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            print("Загрузка пайплайна manuscript-ocr...")
            # Инициализация с моделями по умолчанию (CPU)
            # Библиотека сама загрузит нужные веса детекции и распознавания
            self.pipeline = Pipeline()
            print("Пайплайн готов к работе.")
            self.initialized = True

    def predict(self, image: np.ndarray, preprocess: bool = True) -> list:
        """
        Распознавание текста на изображении.
        `preprocess` здесь игнорируется, т.к. у библиотеки свой пайплайн.
        """
        # Конвертируем numpy array в PIL Image, если нужно
        if isinstance(image, np.ndarray):
            pil_image = Image.fromarray(image)
        else:
            pil_image = image

        # Обработка изображения
        # Метод predict оживает путь к файлу или PIL Image
        result = self.pipeline.predict(pil_image)

        # Извлечение текста в виде строк
        # pipeline.get_text() возвращает объединенный текст для страницы
        text = self.pipeline.get_text(result["page"])
        
        # Разбиваем на строки для совместимости со старым API
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines if lines else [text]

    def parse_result(self, raw_lines: list) -> list:
        """Форматирование результата (оставляем как было)."""
        return [{"line_number": i+1, "text": line, "confidence": None, "bbox": []}
                for i, line in enumerate(raw_lines)]

    # Метод для совместимости с app.py (если вызывается)
    def predict_with_confidence(self, image: np.ndarray) -> list:
        return self.parse_result(self.predict(image))