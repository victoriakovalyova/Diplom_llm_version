import os
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from config import OCR_URL, LLM_URL, SEGMENT_URL


class OCRPipeline:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "original_image": None,
            "segmentation": None,
            "ocr_results": [],
            "llm_correction": None,
            "finished_at": None
        }
    
    def run_segmentation(self, image_path: str) -> dict:
        """Вызов сервиса сегментации"""
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            response = requests.post(SEGMENT_URL, files=files, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Ошибка сегментации: {response.text}")
        
        result = response.json()
        
        cells_info = []
        for cell in result.get("cells", []):
            cells_info.append({
                "row": cell["row"],
                "col_name": cell["col_name"],
                "col_name_rus": cell.get("col_name_rus", cell.get("col_name", "")),
                "url": cell.get("url", ""),
                "filename": cell["filename"]
            })
        
        # Сортируем ячейки по номеру строки
        cells_info.sort(key=lambda x: x["row"])
        
        segmented_url = result.get("segmented_image_url", "")
        if segmented_url:
            segmented_filename = segmented_url.split("/")[-1]
        else:
            segmented_filename = ""
        
        self.results["segmentation"] = {
            "cells_count": result.get("cells_count", 0),
            "cells": cells_info,
            "segmented_image_filename": segmented_filename
        }
        
        return cells_info
    
    def run_ocr_on_cell(self, cell: dict, session_id: str) -> dict:
        """OCR для одной ячейки"""
        cell_url = f"http://segment_service:8002{cell['url']}"
        
        base_result = {
            "row": cell["row"],
            "col_name": cell["col_name"],
            "col_name_rus": cell.get("col_name_rus", cell["col_name"]),
            "filename": cell["filename"],
            "text": "",
            "error": None,
            "confidence": None
        }
        
        try:
            # Скачиваем изображение ячейки
            response = requests.get(cell_url, timeout=30)
            if response.status_code != 200:
                base_result["error"] = f"Не удалось загрузить ячейку: HTTP {response.status_code}"
                return base_result
            
            # Отправляем в OCR сервис
            files = {"file": (cell["filename"], response.content, "image/png")}
            ocr_response = requests.post(OCR_URL, files=files, timeout=30)
            
            if ocr_response.status_code == 200:
                ocr_data = ocr_response.json()
                lines = ocr_data.get("lines", [])
                text = " ".join([line["text"] for line in lines])
                base_result["text"] = text
                base_result["confidence"] = ocr_data.get("num_blocks", 0)
            else:
                base_result["error"] = f"OCR ошибка: HTTP {ocr_response.status_code}"
                
        except requests.exceptions.Timeout:
            base_result["error"] = "Таймаут OCR сервиса"
        except Exception as e:
            base_result["error"] = str(e)
        
        return base_result
    
    def run_ocr(self, cells_info: list, session_id: str) -> list:
        """OCR для всех ячеек с сохранением порядка"""
        ocr_results = []
        total = len(cells_info)
        
        # Убеждаемся, что ячейки отсортированы
        cells_info = sorted(cells_info, key=lambda x: x.get("row", 0))
        
        print(f"\n📝 Начинаем OCR обработку {total} ячеек:")
        
        for idx, cell in enumerate(cells_info, 1):
            print(f"   [{idx}/{total}] Строка {cell['row']}: {cell['col_name_rus']}")
            result = self.run_ocr_on_cell(cell, session_id)
            ocr_results.append(result)
            time.sleep(0.2)
        
        self.results["ocr_results"] = ocr_results
        return ocr_results
    
    def run_llm(self, ocr_results: list) -> dict:
        """LLM постобработка - передаем структурированную таблицу"""
        try:
            # Группируем ячейки по строкам
            rows_data = {}
            for cell in ocr_results:
                row = cell.get('row')
                if row not in rows_data:
                    rows_data[row] = {}
                rows_data[row][cell.get('col_name_rus')] = cell.get('text', '—')
            
            # Отправляем в LLM
            payload = {
                "rows": rows_data
            }
            
            response = requests.post(LLM_URL, json=payload, timeout=120)
            
            if response.status_code == 200:
                llm_data = response.json()
                corrected_rows = llm_data.get("corrected_rows", {})
                
                # Преобразуем обратно в формат ячеек
                corrected_results = []
                for row_num, row_data in corrected_rows.items():
                    row_num = int(row_num)
                    for col_name, corrected_text in row_data.items():
                        for cell in ocr_results:
                            if cell['row'] == row_num and cell['col_name_rus'] == col_name:
                                corrected_results.append({
                                    "row": row_num,
                                    "col_name": cell.get('col_name', ''),
                                    "col_name_rus": col_name,
                                    "original_text": cell.get('text', ''),
                                    "corrected_text": corrected_text,
                                    "was_corrected": cell.get('text', '') != corrected_text
                                })
                                break
                
                self.results["llm_correction"] = {
                    "results": corrected_results,
                    "processed_at": datetime.now().isoformat()
                }
            else:
                self.results["llm_correction"] = {"error": f"HTTP {response.status_code}", "results": []}
                
        except Exception as e:
            self.results["llm_correction"] = {"error": str(e), "results": []}
        
        return self.results["llm_correction"]
    
    def run(self, image_path: str) -> dict:
        """Запуск полного пайплайна"""
        print(f"\n🚀 Запуск пайплайна для {image_path}")
        
        self.results["original_image"] = image_path
        
        # Шаг 1: Сегментация
        print("📐 Шаг 1/3: Сегментация изображения...")
        try:
            cells = self.run_segmentation(image_path)
            print(f"   ✅ Найдено {len(cells)} ячеек")
        except Exception as e:
            self.results["error"] = f"Ошибка сегментации: {str(e)}"
            print(f"   ❌ {self.results['error']}")
            return self.results
        
        if not cells:
            self.results["error"] = "Нет ячеек для обработки"
            return self.results
        
        # Шаг 2: OCR
        print("🔍 Шаг 2/3: Распознавание текста...")
        ocr_results = self.run_ocr(cells, self.session_id)
        successful_ocr = len([r for r in ocr_results if not r.get('error')])
        print(f"   ✅ Успешно распознано: {successful_ocr}/{len(ocr_results)} ячеек")
        
        # Шаг 3: LLM (если URL указан)
        if LLM_URL:
            print("🤖 Шаг 3/3: LLM постобработка...")
            self.run_llm(ocr_results)
        else:
            print("⚠️ LLM сервис не настроен, пропускаем")
        
        self.results["finished_at"] = datetime.now().isoformat()
        print(f"✅ Пайплайн завершен. Сессия: {self.session_id}\n")
        
        return self.results