"""
Менеджер файлов для работы с JSON и другими файлами
"""
import json
import os
from typing import Dict, Any

from bot.interfaces import IFileManager


class FileManager(IFileManager):
    """Класс для работы с файлами"""
    
    def load_json(self, file_path: str) -> Dict[str, Any]:
        """Загрузить JSON файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"Ошибка загрузки JSON файла {file_path}: {e}")
            return {}
    
    def save_json(self, file_path: str, data: Dict[str, Any]) -> None:
        """Сохранить JSON файл"""
        try:
            # Создаем директорию, если не существует
            dir_path = os.path.dirname(file_path)
            if dir_path:  # Проверяем, что путь содержит директорию
                os.makedirs(dir_path, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения JSON файла {file_path}: {e}")
    
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла"""
        return os.path.exists(file_path)
    
    def append_json_array(self, file_path: str, new_item: Dict[str, Any]) -> None:
        """Добавить элемент в JSON массив"""
        try:
            # Читаем существующие данные
            existing_data = []
            if self.file_exists(file_path):
                existing_data = self.load_json(file_path)
                if not isinstance(existing_data, list):
                    existing_data = []
            
            # Добавляем новый элемент
            existing_data.append(new_item)
            
            # Сохраняем обновленные данные
            self.save_json(file_path, existing_data)
        except Exception as e:
            print(f"Ошибка добавления в JSON массив {file_path}: {e}")
