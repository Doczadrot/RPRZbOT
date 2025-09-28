"""
Обработчик сообщений об опасности
"""
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.base.base_handler import BaseHandler
from bot.interfaces import IStateManager, IKeyboardFactory
from bot.services.danger_report_service import DangerReportService
from bot.models.user_state import DangerReportData


class DangerReportHandler(BaseHandler):
    """Обработчик сообщений об опасности"""
    
    def __init__(self, logger, state_manager: IStateManager, 
                 keyboard_factory: IKeyboardFactory, danger_service: DangerReportService):
        super().__init__(logger, state_manager)
        self.keyboard_factory = keyboard_factory
        self.danger_service = danger_service
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать сообщение об опасности"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if text == "❗ Сообщите об опасности":
            await self._start_danger_report(update, context)
        else:
            await self._handle_danger_flow(update, context)
    
    async def _start_danger_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать процесс сообщения об опасности"""
        user_id = update.effective_user.id
        
        # Инициализируем состояние пользователя
        self.state_manager.set_user_state(user_id, {
            'state': 'danger_description',
            'data': {}
        })
        
        await update.message.reply_text(
            "🚨 **Сообщение об опасности**\n\n"
            "Опишите, что произошло. Будьте максимально конкретны:\n"
            "• Что именно случилось?\n"
            "• Когда это произошло?\n"
            "• Есть ли пострадавшие?",
            reply_markup=self.keyboard_factory.create_back_button(),
            parse_mode='Markdown'
        )
    
    async def _handle_danger_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать поток сообщения об опасности"""
        user_id = update.effective_user.id
        user_state = self.state_manager.get_user_state(user_id)
        
        if not user_state:
            return
        
        state = user_state['state']
        data = user_state['data']
        
        if state == 'danger_description':
            await self._handle_description(update, context, data)
        elif state == 'danger_location':
            await self._handle_location(update, context, data)
        elif state == 'danger_media':
            await self._handle_media(update, context, data)
        elif state == 'danger_confirm':
            await self._handle_confirmation(update, context, data)
    
    async def _handle_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Обработать описание опасности"""
        user_id = update.effective_user.id
        
        data['description'] = update.message.text
        self.state_manager.set_user_state(user_id, {
            'state': 'danger_location',
            'data': data
        })
        
        await update.message.reply_text(
            "📍 **Местоположение**\n\n"
            "Укажите, где именно произошла ситуация:\n"
            "• Адрес или номер корпуса\n"
            "• Этаж, кабинет, лаборатория\n"
            "• Любые ориентиры",
            reply_markup=self.keyboard_factory.create_back_button(),
            parse_mode='Markdown'
        )
    
    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Обработать местоположение"""
        user_id = update.effective_user.id
        
        data['location'] = update.message.text
        self.state_manager.set_user_state(user_id, {
            'state': 'danger_media',
            'data': data
        })
        
        await update.message.reply_text(
            "📎 **Медиафайлы**\n\n"
            "Можете прикрепить фото или видео, если это поможет понять ситуацию.\n"
            "Максимальный размер: фото до 20 МБ, видео до 300 МБ",
            reply_markup=self.keyboard_factory.create_media_buttons(),
            parse_mode='Markdown'
        )
    
    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Обработать медиафайлы"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if text == "⏭️ Пропустить":
            await self._show_confirmation(update, context, data)
        elif text == "📷 Прикрепить фото/видео":
            await update.message.reply_text(
                "Прикрепите фото или видео к следующему сообщению",
                reply_markup=self.keyboard_factory.create_media_buttons()
            )
        elif text == "📷 Прикрепить еще":
            await update.message.reply_text(
                "Прикрепите фото или видео к следующему сообщению",
                reply_markup=self.keyboard_factory.create_media_continue_buttons()
            )
        elif text == "⏭️ Продолжить":
            await self._show_confirmation(update, context, data)
    
    async def _handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Обработать подтверждение"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if text == "✅ Отправить сообщение":
            await self._send_incident(update, context, data)
        elif text == "✏️ Редактировать":
            # Возвращаемся к началу
            self.state_manager.set_user_state(user_id, {
                'state': 'danger_description',
                'data': {}
            })
            await self._start_danger_report(update, context)
        elif text == "❌ Отменить":
            self.state_manager.clear_user_state(user_id)
            await update.message.reply_text(
                "Сообщение об опасности отменено.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def _show_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Показать подтверждение"""
        user_id = update.effective_user.id
        
        self.state_manager.set_user_state(user_id, {
            'state': 'danger_confirm',
            'data': data
        })
        
        text = "📋 **Предварительный пакет**\n\n"
        text += f"**Описание:** {data['description']}\n\n"
        text += f"**Местоположение:** {data['location']}\n\n"
        
        if 'media_files' in data and data['media_files']:
            text += f"**Медиафайлы:** {len(data['media_files'])} файлов\n\n"
        
        text += "Проверьте информацию и подтвердите отправку."
        
        await update.message.reply_text(
            text,
            reply_markup=self.keyboard_factory.create_confirmation_buttons(),
            parse_mode='Markdown'
        )
    
    async def _send_incident(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
        """Отправить инцидент"""
        user_id = update.effective_user.id
        
        # Создаем объект данных
        danger_data = DangerReportData(
            description=data['description'],
            location=data['location'],
            media_files=data.get('media_files', [])
        )
        
        # Сохраняем инцидент
        await self.danger_service.save_incident(update, context, danger_data)
        
        # Отправляем админу
        await self.danger_service.send_to_admin(update, context, danger_data)
        
        # Показываем успех
        await update.message.reply_text(
            "✅ **Сообщение отправлено!**\n\n"
            "Ваше сообщение об опасности передано службе безопасности.\n"
            "При необходимости вы можете связаться с соответствующими службами:",
            reply_markup=self.keyboard_factory.create_success_buttons(),
            parse_mode='Markdown'
        )
        
        # Очищаем состояние
        self.state_manager.clear_user_state(user_id)
