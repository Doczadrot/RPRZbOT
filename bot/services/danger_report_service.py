"""
Сервис для обработки сообщений об опасности
"""
from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.interfaces import IFileManager, ILogger
from bot.models.user_state import DangerReportData, IncidentData


class DangerReportService:
    """Сервис для обработки сообщений об опасности"""
    
    def __init__(self, file_manager: IFileManager, logger: ILogger):
        self.file_manager = file_manager
        self.logger = logger
    
    async def save_incident(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          data: DangerReportData) -> None:
        """Сохранить инцидент"""
        incident = IncidentData(
            timestamp=datetime.now().isoformat(),
            user_id=update.effective_user.id,
            username=update.effective_user.username,
            description=data.description,
            location=data.location,
            media_files=data.media_files
        )
        
        # Сохраняем в JSON файл
        self.file_manager.append_json_array('logs/incidents.json', incident.__dict__)
        
        # Логируем активность
        self.logger.log_activity(
            update.effective_user.id,
            update.effective_user.username,
            "incident_saved",
            f"Description: {data.description[:30]}..."
        )
    
    async def send_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          data: DangerReportData) -> None:
        """Отправить сообщение админу"""
        admin_chat_id = context.bot_data.get('admin_chat_id')
        
        if not admin_chat_id or admin_chat_id == 'ADMIN_ID_PLACEHOLDER':
            self.logger.log_activity(
                update.effective_user.id,
                update.effective_user.username,
                "admin_not_configured"
            )
            return
        
        try:
            # Формируем сообщение для админа
            admin_text = f"🚨 **НОВОЕ СООБЩЕНИЕ ОБ ОПАСНОСТИ**\n\n"
            admin_text += f"👤 **Пользователь:** @{update.effective_user.username} (ID: {update.effective_user.id})\n"
            admin_text += f"🕐 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            admin_text += f"📝 **Описание:** {data.description}\n\n"
            admin_text += f"📍 **Местоположение:** {data.location}\n\n"
            
            if data.media_files:
                admin_text += f"📎 **Медиафайлы:** {len(data.media_files)} файлов\n\n"
            
            # Отправляем текстовое сообщение
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=admin_text,
                parse_mode='Markdown'
            )
            
            # Отправляем медиафайлы
            for media in data.media_files:
                try:
                    if media['file_type'] == 'photo':
                        await context.bot.send_photo(
                            chat_id=admin_chat_id,
                            photo=media['file_id'],
                            caption=f"Фото от @{update.effective_user.username}"
                        )
                    else:  # video
                        await context.bot.send_video(
                            chat_id=admin_chat_id,
                            video=media['file_id'],
                            caption=f"Видео от @{update.effective_user.username}"
                        )
                except Exception as e:
                    print(f"Ошибка отправки медиафайла: {e}")
            
            self.logger.log_activity(
                update.effective_user.id,
                update.effective_user.username,
                "admin_notification_sent"
            )
            
        except Exception as e:
            print(f"Ошибка отправки в админ-чат: {e}")
    
    def validate_media_file(self, file_size: int, file_type: str) -> bool:
        """Валидировать размер медиафайла"""
        max_photo_size = 20 * 1024 * 1024  # 20 МБ
        max_video_size = 300 * 1024 * 1024  # 300 МБ
        
        if file_type == 'photo' and file_size > max_photo_size:
            return False
        elif file_type == 'video' and file_size > max_video_size:
            return False
        
        return True
