import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional


class ImageProcessor:
    """Класс для продвинутой предобработки изображений метрических книг"""
    
    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Исправление перекоса страницы"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            median_angle = np.median(angles)
            if abs(median_angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(image, rotation_matrix, (w, h),
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                return rotated
        
        return image
    
    @staticmethod
    def remove_noise(image: np.ndarray) -> np.ndarray:
        """Удаление шума"""
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    
    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """Улучшение контраста"""
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    
    @staticmethod
    def remove_background(image: np.ndarray) -> np.ndarray:
        """Удаление фона (для старых документов)"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    
    @staticmethod
    def full_preprocessing(image: np.ndarray) -> np.ndarray:
        """Полный цикл предобработки"""
        # Исправление перекоса
        deskewed = ImageProcessor.deskew(image)
        # Удаление шума
        denoised = ImageProcessor.remove_noise(deskewed)
        # Улучшение контраста
        contrasted = ImageProcessor.enhance_contrast(denoised)
        # Удаление фона
        background_removed = ImageProcessor.remove_background(contrasted)
        
        return background_removed