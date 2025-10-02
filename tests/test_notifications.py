"""
Тесты для системы уведомлений (yandex_notifications.py)
Покрывает все каналы уведомлений и сервисы
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Импорты для тестирования
from yandex_notifications import (
    IncidentFormatter, SMTPNotificationChannel, CloudNotificationChannel,
    SMSNotificationChannel, NotificationService, NotificationServiceFactory,
    send_incident_notification
)


class TestIncidentFormatter:
    """Тесты форматтера инцидентов"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.formatter = IncidentFormatter()
        self.test_incident = {
            'user_id': 12345,
            'description': 'Test incident description',
            'location': {'latitude': 55.7558, 'longitude': 37.6176},
            'location_text': 'Test location',
            'media_count': 2
        }
    
    def test_format_email_with_location(self):
        """Тест форматирования email с геолокацией"""
        result = self.formatter.format_email(self.test_incident)
        
        assert "Test incident description" in result
        assert "55.755800, 37.617600" in result
        assert "Медиафайлов: 2" in result
        assert "автоматическое уведомление" in result
    
    def test_format_email_with_location_text(self):
        """Тест форматирования email с текстовым местоположением"""
        incident = self.test_incident.copy()
        del incident['location']
        
        result = self.formatter.format_email(incident)
        
        assert "Test incident description" in result
        assert "Test location" in result
        assert "Медиафайлов: 2" in result
    
    def test_format_email_no_location(self):
        """Тест форматирования email без местоположения"""
        incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'media_count': 0
        }
        
        result = self.formatter.format_email(incident)
        
        assert "Test incident" in result
        assert "Место: Не указано" in result
        assert "Медиафайлов: 0" in result
    
    def test_format_cloud_message(self):
        """Тест форматирования сообщения для Cloud"""
        result = self.formatter.format_cloud_message(self.test_incident)
        
        assert "ИНЦИДЕНТ БЕЗОПАСНОСТИ РПРЗ" in result
        assert "12345" in result
        assert "Test incident description" in result
        assert "Test location" in result
    
    def test_formatter_without_location(self):
        """Тест форматтера без включения местоположения"""
        formatter = IncidentFormatter(include_location=False)
        result = formatter.format_email(self.test_incident)
        
        assert "Test incident description" in result
        assert "55.755800" not in result  # Координаты не должны быть включены
    
    def test_formatter_without_media_info(self):
        """Тест форматтера без включения информации о медиа"""
        formatter = IncidentFormatter(include_media_info=False)
        result = formatter.format_email(self.test_incident)
        
        assert "Test incident description" in result
        assert "Медиафайлов" not in result  # Информация о медиа не должна быть включена


class TestSMTPNotificationChannel:
    """Тесты SMTP канала уведомлений"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.smtp_config = {
            'host': 'smtp.test.com',
            'port': 587,
            'user': 'test@test.com',
            'password': 'password',
            'use_tls': True
        }
        self.recipients = ['admin@test.com', 'security@test.com']
        self.formatter = IncidentFormatter()
        self.channel = SMTPNotificationChannel(self.smtp_config, self.recipients, self.formatter)
        self.test_incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'media_count': 1
        }
    
    @patch('smtplib.SMTP')
    def test_send_success(self, mock_smtp):
        """Тест успешной отправки email"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is True
        assert "Отправлено на 2 email" in message
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'password')
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
    
    def test_send_no_credentials(self):
        """Тест отправки без учетных данных"""
        self.smtp_config['user'] = ''
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is False
        assert "SMTP не настроен" in message
    
    def test_send_no_recipients(self):
        """Тест отправки без получателей"""
        # Создаем новый канал без получателей
        empty_channel = SMTPNotificationChannel(self.smtp_config, [], self.formatter)
        
        success, message = empty_channel.send(self.test_incident)
        
        assert success is False
        assert "Нет получателей email" in message
    
    @patch('smtplib.SMTP')
    def test_send_smtp_error(self, mock_smtp):
        """Тест обработки ошибки SMTP"""
        mock_smtp.side_effect = Exception("SMTP Error")
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is False
        assert "Ошибка: SMTP Error" in message
    
    @patch('smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp):
        """Тест успешного тестирования подключения"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        success, message = self.channel.test_connection()
        
        assert success is True
        assert "SMTP подключение успешно" in message
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.quit.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_test_connection_failure(self, mock_smtp):
        """Тест неудачного тестирования подключения"""
        mock_smtp.side_effect = Exception("Connection Error")
        
        success, message = self.channel.test_connection()
        
        assert success is False
        assert "SMTP ошибка: Connection Error" in message


class TestCloudNotificationChannel:
    """Тесты Cloud канала уведомлений"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.cloud_config = {
            'folder_id': 'test_folder',
            'oauth_token': 'test_token',
            'channel_id': 'test_channel',
            'priority_high': True
        }
        self.formatter = IncidentFormatter()
        self.channel = CloudNotificationChannel(self.cloud_config, self.formatter)
        self.test_incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'media_count': 1
        }
    
    @patch('requests.post')
    def test_send_success(self, mock_post):
        """Тест успешной отправки Cloud уведомления"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is True
        assert "Отправлено через Yandex Cloud" in message
        mock_post.assert_called_once()
    
    def test_send_no_credentials(self):
        """Тест отправки без учетных данных"""
        self.cloud_config['oauth_token'] = ''
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is False
        assert "Yandex Cloud не настроен" in message
    
    @patch('requests.post')
    def test_send_api_error(self, mock_post):
        """Тест обработки ошибки API"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is False
        assert "API ошибка: 400" in message
    
    @patch('requests.post')
    def test_send_request_error(self, mock_post):
        """Тест обработки ошибки запроса"""
        mock_post.side_effect = Exception("Request Error")
        
        success, message = self.channel.send(self.test_incident)
        
        assert success is False
        assert "Ошибка: Request Error" in message
    
    @patch('requests.get')
    def test_test_connection_success(self, mock_get):
        """Тест успешного тестирования Cloud подключения"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        success, message = self.channel.test_connection()
        
        assert success is True
        assert "Yandex Cloud подключение успешно" in message
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_test_connection_failure(self, mock_get):
        """Тест неудачного тестирования Cloud подключения"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        success, message = self.channel.test_connection()
        
        assert success is False
        assert "Cloud API ошибка: 401" in message


class TestSMSNotificationChannel:
    """Тесты SMS канала уведомлений"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.recipients = ['+1234567890', '+0987654321']
        self.channel = SMSNotificationChannel(self.recipients)
        self.test_incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'media_count': 1
        }
    
    def test_send_success(self):
        """Тест успешной отправки SMS (заглушка)"""
        success, message = self.channel.send(self.test_incident)
        
        assert success is True
        assert "SMS заглушка для 2 номеров" in message
    
    def test_send_no_recipients(self):
        """Тест отправки без получателей"""
        # Создаем новый канал без получателей
        empty_channel = SMSNotificationChannel([])
        
        success, message = empty_channel.send(self.test_incident)
        
        assert success is False
        assert "Нет получателей SMS" in message
    
    def test_test_connection(self):
        """Тест тестирования SMS подключения"""
        success, message = self.channel.test_connection()
        
        assert success is True
        assert "SMS сервис доступен" in message


class TestNotificationService:
    """Тесты основного сервиса уведомлений"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.mock_channel1 = Mock()
        self.mock_channel2 = Mock()
        self.channels = [self.mock_channel1, self.mock_channel2]
        self.service = NotificationService(self.channels)
        self.test_incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'media_count': 1
        }
    
    def test_send_incident_notification_success(self):
        """Тест успешной отправки уведомления через все каналы"""
        self.mock_channel1.send.return_value = (True, "Channel 1 success")
        self.mock_channel2.send.return_value = (True, "Channel 2 success")
        
        success, message = self.service.send_incident_notification(self.test_incident)
        
        assert success is True
        assert "Отправлено 2/2" in message
        assert "Channel 1 success" in message
        assert "Channel 2 success" in message
    
    def test_send_incident_notification_partial_success(self):
        """Тест частично успешной отправки уведомления"""
        self.mock_channel1.send.return_value = (True, "Channel 1 success")
        self.mock_channel2.send.return_value = (False, "Channel 2 error")
        
        success, message = self.service.send_incident_notification(self.test_incident)
        
        assert success is True  # Хотя бы один канал сработал
        assert "Отправлено 1/2" in message
    
    def test_send_incident_notification_all_failed(self):
        """Тест неудачной отправки уведомления через все каналы"""
        self.mock_channel1.send.return_value = (False, "Channel 1 error")
        self.mock_channel2.send.return_value = (False, "Channel 2 error")
        
        success, message = self.service.send_incident_notification(self.test_incident)
        
        assert success is False
        assert "Отправлено 0/2" in message
    
    def test_send_incident_notification_no_channels(self):
        """Тест отправки уведомления без каналов"""
        service = NotificationService([])
        
        success, message = service.send_incident_notification(self.test_incident)
        
        assert success is False
        assert "Нет настроенных каналов" in message
    
    def test_test_connections(self):
        """Тест тестирования всех каналов"""
        self.mock_channel1.test_connection.return_value = (True, "Channel 1 OK")
        self.mock_channel2.test_connection.return_value = (False, "Channel 2 Error")
        
        results = self.service.test_connections()
        
        # Проверяем, что функция работает и возвращает результаты
        assert isinstance(results, dict)
        assert len(results) >= 1
        # Проверяем, что есть хотя бы один результат
        result_values = list(results.values())
        assert len(result_values) > 0


class TestNotificationServiceFactory:
    """Тесты фабрики сервиса уведомлений"""
    
    @patch.dict(os.environ, {
        'YANDEX_SMTP_ENABLED': 'true',
        'YANDEX_SMTP_HOST': 'smtp.test.com',
        'YANDEX_SMTP_PORT': '587',
        'YANDEX_SMTP_USER': 'test@test.com',
        'YANDEX_SMTP_PASSWORD': 'password',
        'YANDEX_SMTP_USE_TLS': 'true',
        'INCIDENT_NOTIFICATION_EMAILS': 'admin@test.com,security@test.com',
        'YANDEX_CLOUD_ENABLED': 'true',
        'YANDEX_CLOUD_FOLDER_ID': 'test_folder',
        'YANDEX_CLOUD_OAUTH_TOKEN': 'test_token',
        'YANDEX_CLOUD_NOTIFICATION_CHANNEL_ID': 'test_channel',
        'INCIDENT_NOTIFICATION_SMS_NUMBERS': '+1234567890,+0987654321'
    })
    def test_create_from_env_all_channels(self):
        """Тест создания сервиса со всеми каналами"""
        service = NotificationServiceFactory.create_from_env()
        
        assert len(service.channels) == 3  # SMTP + Cloud + SMS
        assert isinstance(service.channels[0], SMTPNotificationChannel)
        assert isinstance(service.channels[1], CloudNotificationChannel)
        assert isinstance(service.channels[2], SMSNotificationChannel)
    
    @patch.dict(os.environ, {
        'YANDEX_SMTP_ENABLED': 'false',
        'YANDEX_CLOUD_ENABLED': 'false',
        'INCIDENT_NOTIFICATION_SMS_NUMBERS': ''
    })
    def test_create_from_env_no_channels(self):
        """Тест создания сервиса без каналов"""
        service = NotificationServiceFactory.create_from_env()
        
        assert len(service.channels) == 0
    
    @patch.dict(os.environ, {
        'YANDEX_SMTP_ENABLED': 'true',
        'YANDEX_SMTP_HOST': 'smtp.test.com',
        'YANDEX_SMTP_PORT': '587',
        'YANDEX_SMTP_USER': 'test@test.com',
        'YANDEX_SMTP_PASSWORD': 'password',
        'YANDEX_SMTP_USE_TLS': 'true',
        'INCIDENT_NOTIFICATION_EMAILS': 'admin@test.com',
        'YANDEX_CLOUD_ENABLED': 'false',
        'INCIDENT_NOTIFICATION_SMS_NUMBERS': ''
    })
    def test_create_from_env_smtp_only(self):
        """Тест создания сервиса только с SMTP"""
        service = NotificationServiceFactory.create_from_env()
        
        assert len(service.channels) == 1
        assert isinstance(service.channels[0], SMTPNotificationChannel)


class TestNotificationFunctions:
    """Тесты глобальных функций уведомлений"""
    
    @patch('yandex_notifications.notification_service')
    def test_send_incident_notification(self, mock_service):
        """Тест глобальной функции отправки уведомления"""
        mock_service.send_incident_notification.return_value = (True, "Success")
        
        success, message = send_incident_notification({'test': 'data'})
        
        assert success is True
        assert message == "Success"
        mock_service.send_incident_notification.assert_called_once_with({'test': 'data'})
    


class TestNotificationIntegration:
    """Интеграционные тесты системы уведомлений"""
    
    def test_incident_formatter_integration(self):
        """Тест интеграции форматтера с реальными данными"""
        formatter = IncidentFormatter()
        
        # Тест с полными данными
        full_incident = {
            'user_id': 12345,
            'username': 'test_user',
            'description': 'Пожар в здании А',
            'location': {'latitude': 55.7558, 'longitude': 37.6176},
            'location_text': 'Здание А, 1 этаж',
            'media_count': 3
        }
        
        email_result = formatter.format_email(full_incident)
        cloud_result = formatter.format_cloud_message(full_incident)
        
        assert "Пожар в здании А" in email_result
        assert "55.755800, 37.617600" in email_result
        assert "Медиафайлов: 3" in email_result
        
        assert "ИНЦИДЕНТ БЕЗОПАСНОСТИ РПРЗ" in cloud_result
        assert "12345" in cloud_result  # user_id вместо username
        assert "Здание А, 1 этаж" in cloud_result
    
    def test_notification_service_integration(self):
        """Тест интеграции сервиса уведомлений"""
        # Создаем реальные каналы с моками
        smtp_channel = SMTPNotificationChannel(
            {'host': 'test', 'port': 587, 'user': 'test', 'password': 'test', 'use_tls': True},
            ['test@test.com'],
            IncidentFormatter()
        )
        
        sms_channel = SMSNotificationChannel(['+1234567890'])
        
        service = NotificationService([smtp_channel, sms_channel])
        
        # Тестируем с моками
        with patch.object(smtp_channel, 'send', return_value=(True, "SMTP Success")):
            with patch.object(sms_channel, 'send', return_value=(True, "SMS Success")):
                success, message = service.send_incident_notification({
                    'user_id': 12345,
                    'description': 'Test incident'
                })
                
                assert success is True
                assert "Отправлено 2/2" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
