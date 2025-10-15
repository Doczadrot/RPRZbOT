"""
Оптимизированная система обработки медиафайлов
Обеспечивает быструю обработку и валидацию медиафайлов
"""

import hashlib
import mimetypes
import os
import time
from typing import Any, Dict, Optional, Tuple

from loguru import logger


class MediaProcessor:
    """Класс для оптимизированной обработки медиафайлов"""

    def __init__(self):
        self.supported_types = {
            "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
            "video": ["video/mp4", "video/mpeg", "video/quicktime"],
            "audio": ["audio/mpeg", "audio/ogg", "audio/wav"],
            "document": ["application/pdf", "text/plain", "application/msword"],
        }

        self.max_sizes = {
            "image": 20 * 1024 * 1024,  # 20 MB
            "video": 300 * 1024 * 1024,  # 300 MB
            "audio": 50 * 1024 * 1024,  # 50 MB
            "document": 10 * 1024 * 1024,  # 10 MB
        }

        # Кэш для быстрого доступа к информации о файлах
        self.file_cache = {}

        logger.info("✅ MediaProcessor инициализирован")

    def get_file_type(self, mime_type: str) -> Optional[str]:
        """Определяет тип файла по MIME типу"""
        for file_type, mimes in self.supported_types.items():
            if mime_type in mimes:
                return file_type
        return None

    def validate_file(
        self, file_size: int, mime_type: str, user_id: int
    ) -> Tuple[bool, str]:
        """
        Быстрая валидация файла

        Returns:
            (is_valid, error_message)
        """
        # Проверяем кэш валидации
        cache_key = f"{file_size}_{mime_type}_{user_id}"
        if cache_key in self.file_cache:
            cached_result = self.file_cache[cache_key]
            # Кэш действует 5 минут
            if time.time() - cached_result["timestamp"] < 300:
                logger.debug(f"📥 Валидация файла из кэша: {mime_type}")
                return cached_result["is_valid"], cached_result["error"]

        # Определяем тип файла
        file_type = self.get_file_type(mime_type)
        if not file_type:
            error_msg = f"❌ Неподдерживаемый тип файла: {mime_type}"
            self._cache_validation_result(cache_key, False, error_msg)
            return False, error_msg

        # Проверяем размер
        max_size = self.max_sizes.get(file_type, self.max_sizes["document"])
        if file_size > max_size:
            size_mb = max_size // (1024 * 1024)
            error_msg = f"❌ Файл слишком большой (макс {size_mb} МБ для {file_type})"
            self._cache_validation_result(cache_key, False, error_msg)
            return False, error_msg

        # Кэшируем успешную валидацию
        self._cache_validation_result(cache_key, True, "")
        logger.debug(f"✅ Файл валидирован: {mime_type}, {file_size} байт")
        return True, ""

    def _cache_validation_result(self, cache_key: str, is_valid: bool, error: str):
        """Кэширует результат валидации"""
        self.file_cache[cache_key] = {
            "is_valid": is_valid,
            "error": error,
            "timestamp": time.time(),
        }

        # Очищаем старые записи кэша (больше 1000 записей)
        if len(self.file_cache) > 1000:
            current_time = time.time()
            expired_keys = [
                key
                for key, value in self.file_cache.items()
                if current_time - value["timestamp"] > 300  # 5 минут
            ]
            for key in expired_keys:
                del self.file_cache[key]
            logger.debug(f"🧹 Очищено записей кэша валидации: {len(expired_keys)}")

    def generate_file_hash(self, file_path: str) -> str:
        """Генерирует хэш файла для проверки целостности"""
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5()
                # Читаем файл блоками для экономии памяти
                for chunk in iter(lambda: f.read(8192), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Ошибка генерации хэша файла {file_path}: {e}")
            return ""

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получает информацию о файле"""
        try:
            file_stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            return {
                "size": file_stat.st_size,
                "mime_type": mime_type or "application/octet-stream",
                "created": file_stat.st_ctime,
                "modified": file_stat.st_mtime,
                "hash": self.generate_file_hash(file_path),
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о файле {file_path}: {e}")
            return {}

    def optimize_image_processing(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Оптимизирует обработку изображений"""
        # Добавляем специфичную для изображений информацию
        optimized_info = file_info.copy()

        # Для изображений можно добавить проверку EXIF данных
        # и другую оптимизацию
        optimized_info["processing_optimized"] = True

        return optimized_info

    def optimize_video_processing(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Оптимизирует обработку видео"""
        optimized_info = file_info.copy()

        # Для видео можно добавить проверку метаданных
        # и определение длительности
        optimized_info["processing_optimized"] = True

        return optimized_info

    def process_media_file(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """
        Обрабатывает медиафайл и возвращает оптимизированную информацию
        """
        start_time = time.time()

        try:
            # Получаем базовую информацию
            file_info = self.get_file_info(file_path)

            if not file_info:
                return {"error": "Не удалось получить информацию о файле"}

            # Определяем тип файла
            file_type = self.get_file_type(mime_type)

            # Применяем оптимизации в зависимости от типа
            if file_type == "image":
                file_info = self.optimize_image_processing(file_info)
            elif file_type == "video":
                file_info = self.optimize_video_processing(file_info)

            # Добавляем время обработки
            processing_time = time.time() - start_time
            file_info["processing_time"] = processing_time
            file_info["file_type"] = file_type

            logger.debug(f"📁 Файл обработан за {processing_time:.3f}s: {file_path}")

            return file_info

        except Exception as e:
            logger.error(f"Ошибка обработки файла {file_path}: {e}")
            return {"error": str(e)}

    def get_processing_stats(self) -> Dict[str, Any]:
        """Возвращает статистику обработки"""
        return {
            "cache_size": len(self.file_cache),
            "supported_types": sum(
                len(mimes) for mimes in self.supported_types.values()
            ),
            "max_sizes": self.max_sizes,
        }


# Глобальный экземпляр процессора
media_processor = MediaProcessor()


def validate_media_file(
    file_size: int, mime_type: str, user_id: int
) -> Tuple[bool, str]:
    """Быстрая валидация медиафайла"""
    return media_processor.validate_file(file_size, mime_type, user_id)


def process_media_file(file_path: str, mime_type: str) -> Dict[str, Any]:
    """Обработка медиафайла с оптимизацией"""
    return media_processor.process_media_file(file_path, mime_type)


def get_media_processing_stats() -> Dict[str, Any]:
    """Получение статистики обработки медиафайлов"""
    return media_processor.get_processing_stats()
