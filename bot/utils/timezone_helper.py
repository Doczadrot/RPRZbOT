"""
Утилита для работы с часовыми поясами и проверки рабочего времени
"""
import os
from datetime import datetime, time
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    # Fallback для Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
        HAS_ZONEINFO = True
    except ImportError:
        HAS_ZONEINFO = False


class TimezoneHelper:
    """Помощник для работы с временными зонами"""
    
    MSK_TIMEZONE = "Europe/Moscow"
    DEFAULT_WORK_START = time(7, 0)   # 07:00
    DEFAULT_WORK_END = time(20, 0)     # 20:00
    
    def __init__(self):
        """Инициализация"""
        self.test_mode = os.getenv('TEST_MODE', '0') == '1'
        self.disable_time_check = os.getenv('DISABLE_TIME_CHECK', '0') == '1'
        
    def get_moscow_time(self) -> datetime:
        """
        Получить текущее время в Москве
        
        Returns:
            datetime: Текущее время в часовом поясе МСК
        """
        if HAS_ZONEINFO:
            return datetime.now(ZoneInfo(self.MSK_TIMEZONE))
        else:
            # Fallback: используем UTC+3 (МСК)
            from datetime import timezone, timedelta
            msk_offset = timezone(timedelta(hours=3))
            return datetime.now(msk_offset)
    
    def is_working_hours(
        self, 
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> bool:
        """
        Проверить, находимся ли в рабочих часах
        
        Args:
            start_time: Время начала работы (по умолчанию 07:00)
            end_time: Время окончания работы (по умолчанию 20:00)
            
        Returns:
            bool: True если в рабочих часах или если проверка отключена
        """
        # Если TEST_MODE или DISABLE_TIME_CHECK, всегда возвращаем True
        if self.test_mode or self.disable_time_check:
            return True
        
        start_time = start_time or self.DEFAULT_WORK_START
        end_time = end_time or self.DEFAULT_WORK_END
        
        now_msk = self.get_moscow_time()
        current_time = now_msk.time()
        
        return start_time <= current_time <= end_time
    
    def get_time_status(
        self,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> dict:
        """
        Получить детальный статус времени
        
        Args:
            start_time: Время начала работы
            end_time: Время окончания работы
            
        Returns:
            dict: Словарь со статусом времени
        """
        start_time = start_time or self.DEFAULT_WORK_START
        end_time = end_time or self.DEFAULT_WORK_END
        
        now_msk = self.get_moscow_time()
        is_working = self.is_working_hours(start_time, end_time)
        
        return {
            'current_time_msk': now_msk,
            'current_time_str': now_msk.strftime('%H:%M:%S'),
            'is_working_hours': is_working,
            'work_start': start_time.strftime('%H:%M'),
            'work_end': end_time.strftime('%H:%M'),
            'test_mode': self.test_mode,
            'time_check_disabled': self.disable_time_check,
            'timezone': self.MSK_TIMEZONE,
            'has_zoneinfo': HAS_ZONEINFO
        }
    
    def format_work_hours(
        self,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> str:
        """
        Форматировать рабочие часы для вывода
        
        Args:
            start_time: Время начала работы
            end_time: Время окончания работы
            
        Returns:
            str: Форматированная строка рабочих часов
        """
        start_time = start_time or self.DEFAULT_WORK_START
        end_time = end_time or self.DEFAULT_WORK_END
        
        status = self.get_time_status(start_time, end_time)
        
        msg = f"🕐 Рабочие часы: {status['work_start']}-{status['work_end']} МСК\n"
        msg += f"🕐 Текущее время МСК: {status['current_time_str']}\n"
        
        if status['test_mode']:
            msg += "⚠️ ТЕСТОВЫЙ РЕЖИМ: Проверка времени отключена\n"
        elif status['time_check_disabled']:
            msg += "⚠️ Проверка рабочего времени отключена\n"
        
        if status['is_working_hours']:
            msg += "✅ Бот работает"
        else:
            msg += "❌ Вне рабочих часов"
        
        return msg

