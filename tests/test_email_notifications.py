"""
Unit-тесты для email-уведомлений с attachments
Проверка Resend API и SMTP fallback механизма
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from bot.notifications import (
    _format_incident_html,
    send_email_notification,
    send_email_via_smtp,
)


@pytest.fixture
def incident_data():
    """Тестовые данные инцидента"""
    return {
        "type": "Сообщение об опасности",
        "username": "test_user",
        "user_id": 12345,
        "description": "Тестовый инцидент для проверки email",
        "location_text": "Тестовая локация",
        "timestamp": "2024-01-01 12:00:00",
        "media_count": 2,
    }


@pytest.fixture
def media_files():
    """Тестовые медиафайлы"""
    return [
        {
            "data": b"fake_image_data_1",
            "type": "photo",
            "filename": "photo_abc123.jpg",
            "mime_type": "image/jpeg",
        },
        {
            "data": b"fake_video_data",
            "type": "video",
            "filename": "video_def456.mp4",
            "mime_type": "video/mp4",
        },
    ]


class TestFormatIncidentHTML:
    """Тесты для форматирования HTML письма"""

    def test_format_html_without_media(self, incident_data):
        """Тест форматирования без медиафайлов"""
        html = _format_incident_html(incident_data, None)

        assert "🚨 НОВЫЙ ИНЦИДЕНТ" in html
        assert "test_user" in html
        assert "Тестовый инцидент" in html
        assert "Тестовая локация" in html
        assert "📎 Прикрепленные файлы" not in html

    def test_format_html_with_photos(self, incident_data, media_files):
        """Тест форматирования с фото"""
        html = _format_incident_html(incident_data, [media_files[0]])

        assert "📎 Прикрепленные файлы (1)" in html
        assert "📷" in html
        assert "Фотография" in html
        assert "photo_abc123.jpg" in html

    def test_format_html_with_multiple_media_types(self, incident_data, media_files):
        """Тест форматирования с разными типами медиа"""
        html = _format_incident_html(incident_data, media_files)

        assert "📎 Прикрепленные файлы (2)" in html
        assert "📷" in html  # фото
        assert "🎥" in html  # видео
        assert "photo_abc123.jpg" in html
        assert "video_def456.mp4" in html

    def test_format_html_with_document(self, incident_data):
        """Тест форматирования с документом"""
        doc_media = [
            {
                "data": b"fake_doc_data",
                "type": "document",
                "filename": "document.pdf",
                "mime_type": "application/pdf",
            }
        ]

        html = _format_incident_html(incident_data, doc_media)

        assert "📄" in html
        assert "Документ" in html
        assert "document.pdf" in html


class TestResendEmailNotification:
    """Тесты для отправки через Resend API"""

    @patch("bot.notifications.resend")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_api_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_send_email_without_media(self, mock_resend, incident_data):
        """Тест отправки без медиафайлов"""
        mock_resend.Emails.send.return_value = {"id": "test_email_id"}

        result = send_email_notification(incident_data, None)

        assert result is True
        assert mock_resend.Emails.send.called

        # Проверяем что attachments не передавались
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "attachments" not in call_args

    @patch("bot.notifications.resend")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_api_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_send_email_with_attachments(self, mock_resend, incident_data, media_files):
        """Тест отправки с вложениями"""
        mock_resend.Emails.send.return_value = {"id": "test_email_id"}

        result = send_email_notification(incident_data, media_files)

        assert result is True
        assert mock_resend.Emails.send.called

        # Проверяем что attachments были переданы
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "attachments" in call_args
        assert len(call_args["attachments"]) == 2

        # Проверяем формат attachments
        attachment_1 = call_args["attachments"][0]
        assert "filename" in attachment_1
        assert "content" in attachment_1
        assert attachment_1["filename"] == "photo_abc123.jpg"

    @patch("bot.notifications.resend")
    @patch("bot.notifications.send_email_via_smtp")
    @patch.dict(os.environ, {})  # Пустые настройки
    def test_fallback_when_resend_not_configured(
        self, mock_smtp, mock_resend, incident_data, media_files
    ):
        """Тест fallback на SMTP когда Resend не настроен"""
        mock_smtp.return_value = True

        result = send_email_notification(incident_data, media_files)

        # Resend не должен вызываться
        assert not mock_resend.Emails.send.called

        # SMTP должен вызваться
        assert mock_smtp.called

    @patch("bot.notifications.resend")
    @patch("bot.notifications.send_email_via_smtp")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_api_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_fallback_when_resend_fails(
        self, mock_smtp, mock_resend, incident_data, media_files
    ):
        """Тест fallback на SMTP при ошибке Resend"""
        mock_resend.Emails.send.side_effect = Exception("Resend API error")
        mock_smtp.return_value = True

        result = send_email_notification(incident_data, media_files)

        # SMTP должен вызваться после ошибки Resend
        assert mock_smtp.called
        assert result is True


class TestSMTPFallback:
    """Тесты для SMTP fallback механизма"""

    @patch("bot.notifications.smtplib.SMTP")
    @patch.dict(
        os.environ,
        {
            "YANDEX_SMTP_HOST": "smtp.yandex.ru",
            "YANDEX_SMTP_PORT": "587",
            "YANDEX_SMTP_USER": "test@yandex.ru",
            "YANDEX_SMTP_PASSWORD": "test_password",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_smtp_send_without_media(self, mock_smtp_class, incident_data):
        """Тест SMTP отправки без медиа"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_email_via_smtp(incident_data, None)

        assert result is True
        assert mock_server.starttls.called
        assert mock_server.login.called
        assert mock_server.send_message.called

    @patch("bot.notifications.smtplib.SMTP")
    @patch.dict(
        os.environ,
        {
            "YANDEX_SMTP_HOST": "smtp.yandex.ru",
            "YANDEX_SMTP_PORT": "587",
            "YANDEX_SMTP_USER": "test@yandex.ru",
            "YANDEX_SMTP_PASSWORD": "test_password",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_smtp_send_with_attachments(
        self, mock_smtp_class, incident_data, media_files
    ):
        """Тест SMTP отправки с вложениями"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = send_email_via_smtp(incident_data, media_files)

        assert result is True
        assert mock_server.send_message.called

        # Проверяем что сообщение содержит attachments
        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message.is_multipart()

    @patch("bot.notifications.smtplib.SMTP")
    @patch.dict(os.environ, {})  # Пустые настройки
    def test_smtp_fails_without_credentials(self, mock_smtp_class, incident_data):
        """Тест что SMTP не работает без credentials"""
        result = send_email_via_smtp(incident_data, None)

        assert result is False
        assert not mock_smtp_class.called

    @patch("bot.notifications.smtplib.SMTP")
    @patch.dict(
        os.environ,
        {
            "YANDEX_SMTP_HOST": "smtp.yandex.ru",
            "YANDEX_SMTP_PORT": "587",
            "YANDEX_SMTP_USER": "test@yandex.ru",
            "YANDEX_SMTP_PASSWORD": "test_password",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_smtp_handles_connection_error(self, mock_smtp_class, incident_data):
        """Тест обработки ошибки подключения SMTP"""
        mock_smtp_class.side_effect = Exception("SMTP connection failed")

        result = send_email_via_smtp(incident_data, None)

        assert result is False


class TestEmailIntegration:
    """Интеграционные тесты email-системы"""

    @patch("bot.notifications.resend")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_edge_case_empty_media_list(self, mock_resend, incident_data):
        """Тест с пустым списком медиа"""
        mock_resend.Emails.send.return_value = {"id": "test_id"}

        result = send_email_notification(incident_data, [])

        assert result is True
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert (
            "attachments" not in call_args or len(call_args.get("attachments", [])) == 0
        )

    @patch("bot.notifications.resend")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_edge_case_three_photos(self, mock_resend, incident_data):
        """Тест с максимальным количеством фото (3)"""
        mock_resend.Emails.send.return_value = {"id": "test_id"}

        three_photos = [
            {
                "data": b"photo1",
                "type": "photo",
                "filename": "p1.jpg",
                "mime_type": "image/jpeg",
            },
            {
                "data": b"photo2",
                "type": "photo",
                "filename": "p2.jpg",
                "mime_type": "image/jpeg",
            },
            {
                "data": b"photo3",
                "type": "photo",
                "filename": "p3.jpg",
                "mime_type": "image/jpeg",
            },
        ]

        result = send_email_notification(incident_data, three_photos)

        assert result is True
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert len(call_args["attachments"]) == 3

    @patch("bot.notifications.resend")
    @patch.dict(
        os.environ,
        {
            "RESEND_API_KEY": "test_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    )
    def test_edge_case_large_file(self, mock_resend, incident_data):
        """Тест с большим файлом"""
        mock_resend.Emails.send.return_value = {"id": "test_id"}

        # Создаем "большой" файл (симуляция)
        large_file = [
            {
                "data": b"x" * (5 * 1024 * 1024),  # 5 MB
                "type": "photo",
                "filename": "large_photo.jpg",
                "mime_type": "image/jpeg",
            }
        ]

        result = send_email_notification(incident_data, large_file)

        assert result is True
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert len(call_args["attachments"]) == 1
        # Base64 увеличивает размер на ~33%
        assert len(call_args["attachments"][0]["content"]) > 5 * 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
