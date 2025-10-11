"""
Модуль для отправки email уведомлений
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import resend
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Глобальная переменная для хранения экземпляра бота
bot_instance = None

def set_bot_instance(bot):
    """Устанавливает экземпляр бота для отправки уведомлений в Telegram"""
    global bot_instance
    bot_instance = bot
    logger.info("✅ Bot instance установлен для notifications")

def send_incident_notification(incident_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Отправляет уведомление об инциденте через email и Telegram
    
    Args:
        incident_data: Данные об инциденте
        
    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    logger.info("🔍 Начало send_incident_notification")
    try:
        # Отправляем в Telegram админу
        telegram_success = send_telegram_notification(incident_data)
        
        # Отправляем email уведомление
        email_success = send_email_notification(incident_data)
        
        if telegram_success and email_success:
            return True, "Уведомления отправлены в Telegram и Email"
        elif telegram_success:
            return True, "Уведомление отправлено в Telegram (Email недоступен)"
        elif email_success:
            return True, "Уведомление отправлено в Email (Telegram недоступен)"
        else:
            return False, "Не удалось отправить уведомления"
            
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {e}")
        return False, f"Ошибка: {str(e)}"

def send_telegram_notification(incident_data: Dict[str, Any]) -> bool:
    """Отправляет уведомление в Telegram админу"""
    try:
        if not bot_instance:
            logger.warning("⚠️ Bot instance не установлен для Telegram уведомлений")
            return False
            
        admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID не настроен")
            return False
            
        # Формируем сообщение
        message = format_incident_message(incident_data)
        
        # Отправляем сообщение
        bot_instance.send_message(
            chat_id=admin_chat_id,
            text=message,
            parse_mode='HTML'
        )
        
        logger.info("✅ Уведомление админу в Telegram отправлено")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram уведомления: {e}")
        return False

def send_email_notification(incident_data: Dict[str, Any]) -> bool:
    """Отправляет email уведомление через Resend API"""
    try:
        # Получаем настройки Resend
        resend_api_key = os.getenv('RESEND_API_KEY')
        email_from = os.getenv('RESEND_FROM_EMAIL') or os.getenv('ADMIN_EMAIL')
        email_to = os.getenv('ADMIN_EMAIL') or os.getenv('INCIDENT_NOTIFICATION_EMAILS')
        
        logger.info("🔍 Отладка Resend переменных:")
        logger.info(f"RESEND_API_KEY: {'ЕСТЬ' if resend_api_key else 'НЕТ'}")
        logger.info(f"RESEND_FROM_EMAIL: {email_from or 'НЕТ'}")
        logger.info(f"ADMIN_EMAIL: {email_to or 'НЕТ'}")
        
        if not all([resend_api_key, email_from, email_to]):
            missing = []
            if not resend_api_key: missing.append("RESEND_API_KEY")
            if not email_from: missing.append("RESEND_FROM_EMAIL или ADMIN_EMAIL")
            if not email_to: missing.append("ADMIN_EMAIL")
            logger.warning(f"⚠️ Resend настройки не полные. Отсутствуют: {', '.join(missing)}")
            return False
        
        # Настраиваем Resend
        resend.api_key = resend_api_key
        
        # Формируем письмо
        subject = f"🚨 Инцидент в RPRZ боте - {incident_data.get('type', 'Сообщение об опасности')}"
        body = format_incident_email(incident_data)
        
        # Отправляем через Resend API
        params = {
            "from": email_from,
            "to": [email_to],
            "subject": subject,
            "text": body,
        }
        
        email = resend.Emails.send(params)
        logger.info(f"✅ Email уведомление отправлено через Resend: {email}")
        logger.info(f"📧 Email ID: {email.get('id', 'N/A')}")
        logger.info(f"📧 Отправлено с: {email_from} на: {email_to}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки email через Resend: {e}")
        return False

def format_incident_message(incident_data: Dict[str, Any]) -> str:
    """Форматирует сообщение об инциденте для Telegram"""
    from datetime import datetime
    
    message = f"🚨 <b>Новый инцидент в RPRZ боте</b>\n\n"
    message += f"📋 <b>Тип:</b> {incident_data.get('type', 'Сообщение об опасности')}\n"
    message += f"👤 <b>Пользователь:</b> {incident_data.get('username', 'Неизвестно')}\n"
    message += f"🆔 <b>ID:</b> {incident_data.get('user_id', 'Неизвестно')}\n"
    message += f"⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} МСК\n"
    message += f"📝 <b>Описание:</b> {incident_data.get('description', 'Не указано')}\n"
    
    if incident_data.get('location'):
        lat = incident_data['location'].get('latitude', '')
        lon = incident_data['location'].get('longitude', '')
        message += f"📍 <b>Координаты:</b> {lat}, {lon}\n"
    elif incident_data.get('location_text'):
        message += f"📍 <b>Место:</b> {incident_data['location_text']}\n"
    else:
        message += f"📍 <b>Место:</b> Не указано\n"
        
    message += f"📷 <b>Медиафайлов:</b> {incident_data.get('media_count', 0)}\n"
        
    if incident_data.get('severity'):
        message += f"⚠️ <b>Критичность:</b> {incident_data['severity']}\n"
        
    return message

def format_incident_email(incident_data: Dict[str, Any]) -> str:
    """Форматирует текст письма об инциденте"""
    from datetime import datetime
    
    body = f"Новый инцидент в RPRZ боте\n\n"
    body += f"Тип: {incident_data.get('type', 'Сообщение об опасности')}\n"
    body += f"Пользователь: {incident_data.get('username', 'Неизвестно')}\n"
    body += f"ID: {incident_data.get('user_id', 'Неизвестно')}\n"
    body += f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} МСК\n"
    body += f"Описание: {incident_data.get('description', 'Не указано')}\n"
    
    if incident_data.get('location'):
        lat = incident_data['location'].get('latitude', '')
        lon = incident_data['location'].get('longitude', '')
        body += f"Координаты: {lat}, {lon}\n"
    elif incident_data.get('location_text'):
        body += f"Место: {incident_data['location_text']}\n"
    else:
        body += f"Место: Не указано\n"
        
    body += f"Медиафайлов: {incident_data.get('media_count', 0)}\n"
        
    if incident_data.get('severity'):
        body += f"Критичность: {incident_data['severity']}\n"
        
    body += f"\n\nЭто автоматическое уведомление от RPRZ бота."
    
    return body
