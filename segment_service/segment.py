import cv2
import numpy as np
import os
from cell_splitter import CellSplitter

class TableSegmenter:
    def __init__(self):
        print("✅ Сегментатор таблицы инициализирован")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 15, 5)
        return binary
    
    def detect_vertical_lines(self, image: np.ndarray) -> list:
        binary = self.preprocess_image(image)
        h, w = binary.shape
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
        
        contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        line_positions = []
        for contour in contours:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            if h_box > h * 0.3:
                line_center = x + w_box // 2
                line_positions.append(line_center)
        
        line_positions.sort()
        cleaned = []
        for pos in line_positions:
            if not cleaned or abs(pos - cleaned[-1]) > 10:
                cleaned.append(pos)
        
        print(f"📏 Найдено вертикальных линий: {len(cleaned)}")
        for i, x in enumerate(cleaned):
            print(f"   Линия {i+1}: x={x}")
        
        return cleaned
    
    def crop_header_and_edges(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        top_crop = int(h * 0.25)
        cropped = image[top_crop:, :]
        left_crop = int(w * 0.03)
        right_crop = int(w * 0.97)
        cropped = cropped[:, left_crop:right_crop]
        print(f"📐 Обрезано: сверху {top_crop} пикс, ширина с {w} до {cropped.shape[1]} пикс")
        return cropped
    
    def visualize_lines(self, image: np.ndarray, lines: list) -> np.ndarray:
        result = image.copy()
        h, w = result.shape[:2]
        for line_x in lines:
            if 0 <= line_x < w:
                cv2.line(result, (line_x, 0), (line_x, h), (0, 0, 255), 2)
        print(f"🎨 Нарисовано {len(lines)} красных вертикальных линий")
        return result
    
    def draw_columns(self, image: np.ndarray, lines: list) -> np.ndarray:
        if len(lines) < 7:
            print(f"⚠️ Найдено только {len(lines)} линий, нужно минимум 7 для 6 столбцов")
            return image
        
        h, w = image.shape[:2]
        result = image.copy()
        
        colors = [
            (255, 0, 0),
            (147, 20, 255),
            (0, 0, 255),
            (0, 255, 0),
            (0, 255, 255),
            (255, 0, 255)
        ]
        
        labels = ["Мужской №", "Женский №", "Рождение", "Крещение", "Имя", "Родители"]
        
        for i in range(min(len(lines) - 1, len(colors))):
            x1 = lines[i]
            x2 = lines[i + 1]
            color = colors[i]
            
            overlay = result.copy()
            cv2.rectangle(overlay, (x1, 0), (x2, h), color, -1)
            cv2.addWeighted(overlay, 0.3, result, 0.7, 0, result)
            
            cv2.line(result, (x1, 0), (x1, h), (0, 255, 0), 2)
            cv2.line(result, (x2, 0), (x2, h), (0, 255, 0), 2)
            cv2.putText(result, labels[i], (x1 + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return result
    
    def is_number(self, roi_binary) -> bool:
        white_pixels = np.sum(roi_binary == 255)
        total_pixels = roi_binary.shape[0] * roi_binary.shape[1]
        if total_pixels == 0:
            return False
        fill_ratio = white_pixels / total_pixels
        return 0.25 < fill_ratio < 0.75
    
    def draw_horizontal_lines(self, image: np.ndarray, lines: list) -> tuple:
        if len(lines) < 5:
            print("⚠️ Недостаточно вертикальных линий для 3-го столбца")
            return image, []
        
        result = image.copy()
        h, w = result.shape[:2]
        
        col3_x1 = lines[3]
        col3_x2 = lines[4]
        
        print(f"🔍 Анализируем 3-й столбец (день рождения): x={col3_x1} до {col3_x2}")
        
        roi = image[:, col3_x1:col3_x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for contour in contours:
            x, y, w_cont, h_cont = cv2.boundingRect(contour)
            if h_cont > 6 and h_cont < h * 0.12:
                if w_cont > 2:
                    digit_roi = binary[y:y+h_cont, x:x+w_cont]
                    is_num = self.is_number(digit_roi)
                    objects.append((y, w_cont, h_cont, is_num))
                    print(f"   Объект: y={y}, ширина={w_cont}, высота={h_cont}, число={is_num}")
        
        if not objects:
            print("⚠️ В 3-м столбце не найдено объектов")
            return result, []
        
        objects.sort(key=lambda obj: obj[0])
        
        line_positions = []
        i = 0
        while i < len(objects):
            y, w_cont, h_cont, is_num = objects[i]
            line_positions.append(y)
            print(f"   Линия на y={y} (число={is_num})")
            
            if not is_num:
                i += 1
                while i < len(objects) and not objects[i][3]:
                    print(f"      Пропускаем не число на y={objects[i][0]}")
                    i += 1
            else:
                i += 1
        
        line_positions.sort()
        unique_y = []
        for y in line_positions:
            if not unique_y or abs(y - unique_y[-1]) > 10:
                unique_y.append(y)
        
        print(f"📏 Итоговых горизонтальных линий: {len(unique_y)}")
        
        for y in unique_y:
            line_y = max(0, y - 8)
            cv2.line(result, (0, line_y), (w, line_y), (0, 255, 0), 2)
            print(f"   Горизонтальная линия на y={line_y} (по всей ширине {w}px)")
        
        return result, unique_y
    
    def segment(self, image_path: str) -> tuple:
        print(f"\n📷 Обработка: {image_path}")
        
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Не удалось загрузить: {image_path}")
        
        img = self.crop_header_and_edges(img)
        lines = self.detect_vertical_lines(img)
        
        img_with_red = self.visualize_lines(img, lines)
        img_with_horizontal, y_lines = self.draw_horizontal_lines(img_with_red, lines)
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        out_lines_path = f"{output_dir}/lines_{os.path.basename(image_path)}"
        cv2.imwrite(out_lines_path, img_with_red)
        print(f"✅ Сохранено (только красные линии): {out_lines_path}")
        
        out_final_path = f"{output_dir}/segmented_{os.path.basename(image_path)}"
        cv2.imwrite(out_final_path, img_with_horizontal)
        print(f"✅ Сохранено (красные + зелёные линии): {out_final_path}")
        
        # НАРЕЗКА ЯЧЕЕК
        if len(y_lines) > 0:
            splitter = CellSplitter()
            cells = splitter.split_cells(image_path, lines, y_lines, page_num=1)
            splitter.save_cells(cells, output_dir, os.path.basename(image_path))
            splitter.print_summary(cells)
        
        return img_with_horizontal, lines


if __name__ == "__main__":
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    print("=" * 50)
    print("СЕГМЕНТАЦИЯ МЕТРИЧЕСКОЙ КНИГИ")
    print("=" * 50)
    print("1. Положите изображение в папку 'input'")
    print("2. Запустите скрипт и введите путь к файлу")
    print("=" * 50)
    
    file_path = input("Введите путь к изображению: ").strip()
    
    segmenter = TableSegmenter()
    result, lines = segmenter.segment(file_path)
    
    print(f"\n🎉 Готово! Результат в папке 'output'")