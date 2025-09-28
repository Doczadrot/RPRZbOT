"""
Сервис для работы с историей пользователей
"""
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

from bot.interfaces import IFileManager, ILogger


class HistoryService:
    """Сервис для работы с историей пользователей"""
    
    def __init__(self, file_manager: IFileManager, logger: ILogger):
        self.file_manager = file_manager
        self.logger = logger
    
    def get_user_activities(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить активность пользователя"""
        activity_file = 'logs/activity.csv'
        if not self.file_manager.file_exists(activity_file):
            return []
        
        user_activities = []
        try:
            with open(activity_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row['user_id']) == user_id:
                        user_activities.append(row)
        except Exception as e:
            print(f"Ошибка чтения истории пользователя {user_id}: {e}")
        
        return user_activities
    
    def format_activity_history(self, activities: List[Dict[str, Any]], limit: int = 10) -> str:
        """Форматировать историю активности"""
        if not activities:
            return "📊 **Ваша история**\n\nИстория активности пока пуста."
        
        text = "📊 **Ваша история активности**\n\n"
        
        # Показываем последние записи
        recent_activities = activities[-limit:]
        
        for activity in recent_activities:
            timestamp = datetime.fromisoformat(activity['timestamp'])
            time_str = timestamp.strftime('%d.%m.%Y %H:%M')
            
            action_name = self._get_action_name(activity['action'])
            
            text += f"• {time_str} - {action_name}\n"
            if activity['payload_summary']:
                text += f"  {activity['payload_summary']}\n"
            text += "\n"
        
        # Добавляем статистику
        text += f"📈 **Всего действий:** {len(activities)}\n"
        
        # Подсчитываем типы действий
        action_counts = {}
        for activity in activities:
            action = activity['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        text += "\n📊 **Статистика:**\n"
        for action, count in action_counts.items():
            action_name = self._get_action_name(action)
            text += f"• {action_name}: {count}\n"
        
        return text
    
    def _get_action_name(self, action: str) -> str:
        """Получить читаемое название действия"""
        action_names = {
            'start_command': '🚀 Запуск бота',
            'text_message': '💬 Сообщение',
            'danger_report_started': '🚨 Сообщение об опасности',
            'incident_saved': '✅ Инцидент сохранен',
            'shelter_finder_started': '🏠 Поиск убежищ',
            'safety_consultant_started': '🧑‍🏫 Консультант',
            'question_asked': '❓ Вопрос задан',
            'history_requested': '📊 Запрос истории',
            'admin_notification_sent': '📤 Уведомление админу',
            'admin_not_configured': '⚠️ Админ не настроен'
        }
        return action_names.get(action, action)
