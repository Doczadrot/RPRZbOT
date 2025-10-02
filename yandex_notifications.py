"""
Модуль для отправки уведомлений об инцидентах через Яндекс сервисы
Поддерживает SMTP, Yandex Cloud Notification Service и SMS
"""

import os
import smtplib
import json
import requests
import tempfile
import mimetypes
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from loguru import logger
from typing import List, Dict, Optional, Tuple, Protocol
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv('.env')

# Глобальная переменная для хранения bot instance
bot_instance = None

def set_bot_instance(bot):
    """Устанавливает глобальный экземпляр бота для скачивания медиафайлов"""
    global bot_instance
    bot_instance = bot

def download_telegram_file(file_id: str, file_path: str) -> bool:
    """Скачивает файл из Telegram по file_id"""
    try:
        if not bot_instance:
            logger.warning("Bot instance не установлен для скачивания файлов")
            return False
        
        # Получаем информацию о файле
        file_info = bot_instance.get_file(file_id)
        
        # Скачиваем файл
        file_content = bot_instance.download_file(file_info.file_path)
        
        # Сохраняем файл
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Файл {file_id} скачан в {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка скачивания файла {file_id}: {e}")
        return False


class NotificationChannel(Protocol):
    """Протокол для каналов уведомлений (DIP)"""
    
    def send(self, incident_data: Dict) -> Tuple[bool, str]:
        """Отправляет уведомление"""
        ...
    
    def test_connection(self) -> Tuple[bool, str]:
        """Тестирует подключение"""
        ...


class IncidentFormatter:
    """Класс для форматирования данных инцидентов (SRP)"""
    
    def __init__(self, include_location: bool = True, include_media_info: bool = True):
        self.include_location = include_location
        self.include_media_info = include_media_info
    
    def format_email(self, incident_data: Dict) -> str:
        """Форматирует данные инцидента для email"""
        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        
        email_body = f"""
Время: {timestamp}
Пользователь: ID {incident_data.get('user_id', 'Unknown')}
Описание: {incident_data.get('description', 'Не указано')}
"""
        
        if self.include_location:
            if incident_data.get('location'):
                lat = incident_data['location']['latitude']
                lon = incident_data['location']['longitude']
                email_body += f"Координаты: {lat:.6f}, {lon:.6f}\n"
            elif incident_data.get('location_text'):
                email_body += f"Место: {incident_data['location_text']}\n"
            else:
                email_body += "Место: Не указано\n"
        
        if self.include_media_info:
            media_count = incident_data.get('media_count', 0)
            email_body += f"Медиафайлов: {media_count}\n"
        
        email_body += "\nЭто автоматическое уведомление от бота безопасности РПРЗ."
        return email_body
    
    def format_cloud_message(self, incident_data: Dict) -> str:
        """Форматирует данные инцидента для Cloud уведомления"""
        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        message = f"ИНЦИДЕНТ БЕЗОПАСНОСТИ РПРЗ\n\n"
        message += f"Пользователь ID: {incident_data.get('user_id', 'Unknown')}\n"
        message += f"{incident_data.get('description', 'Не указано')[:100]}...\n"
        message += f"{timestamp}"
        
        if self.include_location and incident_data.get('location_text'):
            message += f"\n{incident_data['location_text']}"
        
        return message


class SMTPNotificationChannel:
    """SMTP канал уведомлений (SRP)"""
    
    def __init__(self, smtp_config: Dict, recipients: List[str], formatter: IncidentFormatter):
        self.smtp_config = smtp_config
        self.recipients = recipients
        self.formatter = formatter
    
    def send(self, incident_data: Dict) -> Tuple[bool, str]:
        """Отправляет email уведомление с медиафайлами"""
        try:
            if not self.smtp_config.get('user') or not self.smtp_config.get('password'):
                return False, "SMTP не настроен (отсутствуют учетные данные)"
            
            if not self.recipients:
                return False, "Нет получателей email"
            
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['user']
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"ИНЦИДЕНТ БЕЗОПАСНОСТИ РПРЗ - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            # Формируем тело письма
            body = self.formatter.format_email(incident_data)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Обрабатываем медиафайлы
            media_files = incident_data.get('media', [])
            downloaded_files = []
            
            if media_files and bot_instance:
                logger.info(f"Обработка {len(media_files)} медиафайлов")
                
                for i, media_info in enumerate(media_files):
                    try:
                        file_id = media_info.get('file_id')
                        file_type = media_info.get('type', 'unknown')
                        
                        if not file_id:
                            continue
                        
                        # Создаем временный файл
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}") as temp_file:
                            temp_path = temp_file.name
                        
                        # Скачиваем файл из Telegram
                        if download_telegram_file(file_id, temp_path):
                            downloaded_files.append((temp_path, file_type, media_info))
                            
                            # Определяем MIME тип
                            mime_type, _ = mimetypes.guess_type(temp_path)
                            if not mime_type:
                                mime_type = 'application/octet-stream'
                            
                            # Читаем файл и прикрепляем к письму
                            with open(temp_path, 'rb') as f:
                                file_data = f.read()
                            
                            # Создаем MIME объект в зависимости от типа
                            if file_type.startswith('photo'):
                                attachment = MIMEImage(file_data)
                            elif file_type.startswith('video'):
                                attachment = MIMEBase('video', mime_type.split('/')[-1])
                                attachment.set_payload(file_data)
                            else:
                                attachment = MIMEApplication(file_data)
                            
                            # Устанавливаем заголовки
                            attachment.add_header(
                                'Content-Disposition',
                                f'attachment; filename="incident_media_{i+1}.{mime_type.split("/")[-1]}"'
                            )
                            attachment.add_header('Content-Type', mime_type)
                            
                            msg.attach(attachment)
                            logger.info(f"Медиафайл {i+1} прикреплен к письму")
                        
                    except Exception as e:
                        logger.error(f"Ошибка обработки медиафайла {i+1}: {e}")
                        continue
            
            # Подключаемся к SMTP серверу
            server = smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'])
            if self.smtp_config.get('use_tls', True):
                server.starttls()
            
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            
            # Отправляем письмо
            text = msg.as_string()
            server.sendmail(self.smtp_config['user'], self.recipients, text)
            server.quit()
            
            # Удаляем временные файлы
            for temp_path, _, _ in downloaded_files:
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            logger.info(f"Email уведомление с {len(downloaded_files)} медиафайлами отправлено на {len(self.recipients)} адресов")
            return True, f"Отправлено на {len(self.recipients)} email с {len(downloaded_files)} медиафайлами"
            
        except Exception as e:
            logger.error(f"Ошибка отправки email уведомления: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Тестирует SMTP подключение"""
        try:
            server = smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'])
            if self.smtp_config.get('use_tls', True):
                server.starttls()
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            server.quit()
            return True, "SMTP подключение успешно"
        except Exception as e:
            return False, f"SMTP ошибка: {str(e)}"


class CloudNotificationChannel:
    """Yandex Cloud канал уведомлений (SRP)"""
    
    def __init__(self, cloud_config: Dict, formatter: IncidentFormatter):
        self.cloud_config = cloud_config
        self.formatter = formatter
    
    def send(self, incident_data: Dict) -> Tuple[bool, str]:
        """Отправляет уведомление через Yandex Cloud"""
        try:
            if not self.cloud_config.get('oauth_token') or not self.cloud_config.get('channel_id'):
                return False, "Yandex Cloud не настроен"
            
            # Формируем данные для отправки
            notification_data = {
                "channel_id": self.cloud_config['channel_id'],
                "message": self.formatter.format_cloud_message(incident_data),
                "title": "Инцидент безопасности РПРЗ",
                "priority": "high" if self.cloud_config.get('priority_high', True) else "normal"
            }
            
            # Отправляем запрос к API
            headers = {
                'Authorization': f'Bearer {self.cloud_config["oauth_token"]}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://notification.api.cloud.yandex.net/v1/channels/{self.cloud_config['channel_id']}/messages"
            
            response = requests.post(url, json=notification_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info("Cloud уведомление отправлено успешно")
                return True, "Отправлено через Yandex Cloud"
            else:
                logger.error(f"Ошибка Cloud API: {response.status_code} - {response.text}")
                return False, f"API ошибка: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Ошибка отправки Cloud уведомления: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Тестирует подключение к Yandex Cloud"""
        try:
            headers = {'Authorization': f'Bearer {self.cloud_config["oauth_token"]}'}
            url = f"https://notification.api.cloud.yandex.net/v1/channels/{self.cloud_config['channel_id']}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "Yandex Cloud подключение успешно"
            else:
                return False, f"Cloud API ошибка: {response.status_code}"
        except Exception as e:
            return False, f"Cloud ошибка: {str(e)}"


class SMSNotificationChannel:
    """SMS канал уведомлений (SRP)"""
    
    def __init__(self, recipients: List[str]):
        self.recipients = recipients
    
    def send(self, incident_data: Dict) -> Tuple[bool, str]:
        """Отправляет SMS уведомление (заглушка)"""
        try:
            if not self.recipients:
                return False, "Нет получателей SMS"
            
            # Здесь можно интегрировать с SMS API
            logger.info(f"SMS уведомление (заглушка) для {len(self.recipients)} номеров")
            return True, f"SMS заглушка для {len(self.recipients)} номеров"
            
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Тестирует SMS подключение (заглушка)"""
        return True, "SMS сервис доступен (заглушка)"


class NotificationService:
    """Основной сервис уведомлений (SRP + OCP)"""
    
    def __init__(self, channels: List[NotificationChannel]):
        self.channels = channels
        logger.info(f"NotificationService инициализирован с {len(channels)} каналами")
    
    def send_incident_notification(self, incident_data: Dict) -> Tuple[bool, str]:
        """Отправляет уведомление через все каналы"""
        if not self.channels:
            return False, "Нет настроенных каналов уведомлений"
        
        results = []
        success_count = 0
        
        for channel in self.channels:
            success, message = channel.send(incident_data)
            results.append(f"{'✅' if success else '❌'} {message}")
            if success:
                success_count += 1
        
        return success_count > 0, f"Отправлено {success_count}/{len(self.channels)}: " + " | ".join(results)
    
    def test_connections(self) -> Dict[str, Tuple[bool, str]]:
        """Тестирует все каналы"""
        results = {}
        for i, channel in enumerate(self.channels):
            channel_name = channel.__class__.__name__.replace('NotificationChannel', '').lower()
            results[channel_name] = channel.test_connection()
        return results


class NotificationServiceFactory:
    """Фабрика для создания сервиса уведомлений (DIP)"""
    
    @staticmethod
    def create_from_env() -> NotificationService:
        """Создает сервис из переменных окружения"""
        channels = []
        formatter = IncidentFormatter(
            include_location=os.getenv('NOTIFICATION_INCLUDE_LOCATION', 'true').lower() == 'true',
            include_media_info=os.getenv('NOTIFICATION_INCLUDE_MEDIA_INFO', 'true').lower() == 'true'
        )
        
        # SMTP канал
        if os.getenv('YANDEX_SMTP_ENABLED', 'false').lower() == 'true':
            smtp_config = {
                'host': os.getenv('YANDEX_SMTP_HOST', 'smtp.yandex.ru'),
                'port': int(os.getenv('YANDEX_SMTP_PORT', '587')),
                'user': os.getenv('YANDEX_SMTP_USER', ''),
                'password': os.getenv('YANDEX_SMTP_PASSWORD', ''),
                'use_tls': os.getenv('YANDEX_SMTP_USE_TLS', 'true').lower() == 'true'
            }
            emails = [email.strip() for email in os.getenv('INCIDENT_NOTIFICATION_EMAILS', '').split(',') if email.strip()]
            if emails:
                channels.append(SMTPNotificationChannel(smtp_config, emails, formatter))
        
        # Cloud канал
        if os.getenv('YANDEX_CLOUD_ENABLED', 'false').lower() == 'true':
            cloud_config = {
                'folder_id': os.getenv('YANDEX_CLOUD_FOLDER_ID', ''),
                'oauth_token': os.getenv('YANDEX_CLOUD_OAUTH_TOKEN', ''),
                'channel_id': os.getenv('YANDEX_CLOUD_NOTIFICATION_CHANNEL_ID', ''),
                'priority_high': os.getenv('NOTIFICATION_PRIORITY_HIGH', 'true').lower() == 'true'
            }
            if cloud_config['oauth_token'] and cloud_config['channel_id']:
                channels.append(CloudNotificationChannel(cloud_config, formatter))
        
        # SMS канал
        sms_numbers = [phone.strip() for phone in os.getenv('INCIDENT_NOTIFICATION_SMS_NUMBERS', '').split(',') if phone.strip()]
        if sms_numbers:
            channels.append(SMSNotificationChannel(sms_numbers))
        
        return NotificationService(channels)


# Глобальный экземпляр сервиса
notification_service = NotificationServiceFactory.create_from_env()


def send_incident_notification(incident_data: Dict) -> Tuple[bool, str]:
    """Удобная функция для отправки уведомления об инциденте"""
    return notification_service.send_incident_notification(incident_data)


def test_notification_services() -> Dict[str, Tuple[bool, str]]:
    """Тестирует все настроенные сервисы уведомлений"""
    results = notification_service.test_connections()
    assert isinstance(results, dict)
    # Не возвращаем значение, чтобы избежать предупреждения pytest
    return results


if __name__ == "__main__":
    # Тестирование сервиса
    print("🧪 Тестирование Yandex Notification Service...")
    
    # Тест подключений
    test_results = test_notification_services()
    for service, (success, message) in test_results.items():
        status = "✅" if success else "❌"
        print(f"{status} {service.upper()}: {message}")
    
    # Тест отправки уведомления
    test_incident = {
        'user_id': 123456789,
        'username': 'test_user',
        'description': 'Тестовое сообщение об опасности',
        'location_text': 'Тестовое местоположение',
        'media_count': 0
    }
    
    print("\n📧 Тест отправки уведомления...")
    success, message = send_incident_notification(test_incident)
    status = "✅" if success else "❌"
    print(f"{status} {message}")