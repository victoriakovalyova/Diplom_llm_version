import cv2
import os
import json
from datetime import datetime
import numpy as np


class CellSplitter:
    def __init__(self):
        print("✅ Модуль нарезки ячеек инициализирован")
    
    def split_cells(self, image_path: str, lines: list, horizontal_lines: list, page_num: int = 1):
        """
        Разделяет изображение на ячейки по готовым горизонтальным и вертикальным линиям
        
        Args:
            image_path: путь к исходному изображению
            lines: список вертикальных линий (x-координаты)
            horizontal_lines: список горизонтальных линий (y-координаты) из сегментатора
            page_num: номер страницы
        """
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Не удалось загрузить изображение: {image_path}")
            return []
        
        # Обрезаем шапку и края
        img, top_offset, left_offset = self._crop_header_and_edges_with_offset(img)
        h, w = img.shape[:2]
        
        if len(lines) < 9:
            print(f"⚠️ Недостаточно вертикальных линий ({len(lines)}), нужно минимум 9")
            return []
        
        if len(horizontal_lines) < 2:
            print(f"⚠️ Недостаточно горизонтальных линий ({len(horizontal_lines)})")
            return []
        
        print(f"📏 Вертикальных линий: {len(lines)}")
        print(f"📏 Горизонтальных линий: {len(horizontal_lines)}")
        
        cells = []
        cell_id = 1
        
        # Столбцы и их названия (индексы вертикальных линий)
        columns = [
            (4, 5, "name", "Имя родившегося"),
            (5, 6, "parents", "Родители"),
            (6, 7, "godparents", "Восприемники (крестные)"),
            (7, 8, "priest", "Священник")
        ]
        
        # Проходим по строкам (горизонтальные линии образуют границы строк)
        for row_idx in range(len(horizontal_lines) - 1):
            y_top = int(horizontal_lines[row_idx])
            y_bottom = int(horizontal_lines[row_idx + 1])
            
            # Пропускаем слишком узкие строки
            if y_bottom - y_top < 8:
                continue
            
            for col_idx, (left_idx, right_idx, col_name, col_rus) in enumerate(columns):
                if left_idx >= len(lines) or right_idx >= len(lines):
                    continue
                
                x_left = int(lines[left_idx])
                x_right = int(lines[right_idx])
                
                # Пропускаем слишком узкие столбцы
                if x_right - x_left < 8:
                    continue
                
                # Вырезаем ячейку
                cell = img[y_top:y_bottom, x_left:x_right]
                
                if cell.size == 0:
                    continue
                
                # Формируем имя файла
                filename = f"page{page_num:03d}_row{row_idx+1:02d}_{col_name}.png"
                
                cells.append({
                    "id": cell_id,
                    "page": page_num,
                    "row": row_idx + 1,
                    "col": col_idx + 1,
                    "col_name": col_name,
                    "col_name_rus": col_rus,
                    "x": x_left,
                    "y": y_top,
                    "x_global": x_left + left_offset,
                    "y_global": y_top + top_offset,
                    "width": x_right - x_left,
                    "height": y_bottom - y_top,
                    "image": cell,
                    "filename": filename
                })
                cell_id += 1
        
        return cells
    
    def _crop_header_and_edges_with_offset(self, image: np.ndarray) -> tuple:
        """Обрезает шапку (25% сверху) и края (3% слева и справа)"""
        h, w = image.shape[:2]
        top_crop = int(h * 0.25)
        left_crop = int(w * 0.03)
        right_crop = int(w * 0.97)
        
        cropped = image[top_crop:, left_crop:right_crop]
        
        return cropped, top_crop, left_crop
    
    def save_cells(self, cells: list, output_dir: str, image_name: str = None) -> tuple:
        """Сохраняет ячейки и JSON"""
        full_output_dir = os.path.join(output_dir, "cells")
        os.makedirs(full_output_dir, exist_ok=True)
        
        saved_files = []
        json_data = {
            "created_at": datetime.now().isoformat(),
            "source_image": image_name,
            "total_cells": len(cells),
            "cells": []
        }
        
        for cell in cells:
            filepath = os.path.join(full_output_dir, cell["filename"])
            cv2.imwrite(filepath, cell["image"])
            saved_files.append(filepath)
            
            json_data["cells"].append({
                "id": cell["id"],
                "page": cell["page"],
                "row": cell["row"],
                "col": cell["col"],
                "col_name": cell["col_name"],
                "col_name_rus": cell["col_name_rus"],
                "x": cell["x"],
                "y": cell["y"],
                "x_global": cell["x_global"],
                "y_global": cell["y_global"],
                "width": cell["width"],
                "height": cell["height"],
                "filename": cell["filename"],
                "filepath": filepath
            })
            
            print(f"   ✅ Ячейка: строка {cell['row']}, {cell['col_name_rus']} → {cell['filename']}")
        
        json_filename = f"cells_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_path = os.path.join(full_output_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 JSON: {json_path}")
        
        return saved_files, json_path
    
    def print_summary(self, cells: list):
        """Сводка"""
        print("\n" + "=" * 60)
        print("📊 СВОДКА НАРЕЗКИ ЯЧЕЕК")
        print("=" * 60)
        
        rows = set(c["row"] for c in cells)
        
        print(f"   Всего строк: {len(rows)}")
        print(f"   Всего ячеек: {len(cells)}")
        print("\n   Распределение по типам:")
        
        col_names = {}
        for c in cells:
            col_names[c["col_name_rus"]] = col_names.get(c["col_name_rus"], 0) + 1
        
        for name, count in col_names.items():
            print(f"      {name}: {count}")