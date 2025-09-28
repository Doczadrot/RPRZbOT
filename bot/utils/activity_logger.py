"""
Логирование активности пользователей
"""
import csv
import os
from datetime import datetime
from typing import Optional

from bot.interfaces import ILogger


class ActivityLogger(ILogger):
    """Класс для логирования активности пользователей в CSV файл"""
    
    def __init__(self, log_file: str = 'logs/activity.csv'):
        self.log_file = log_file
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Создать директорию для логов, если не существует"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def log_activity(self, user_id: int, username: Optional[str], action: str, payload_summary: str = "") -> None:
        """Логирует активность пользователя в CSV файл"""
        try:
            file_exists = os.path.exists(self.log_file)
            
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Записываем заголовки, если файл новый
                if not file_exists:
                    writer.writerow(['timestamp', 'user_id', 'username', 'action', 'payload_summary', 'response_ref'])
                
                # Записываем данные
                writer.writerow([
                    datetime.now().isoformat(),
                    user_id,
                    username or 'Unknown',
                    action,
                    payload_summary[:100],  # Ограничиваем длину
                    ""  # response_ref пока не используется
                ])
                
        except Exception as e:
            print(f"Ошибка логирования активности: {e}")  # Используем print вместо logger, чтобы избежать циклических зависимостей
