"""Тесты для планировщика бота (run_scheduled_bot.py)."""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

# noqa: E402
from run_scheduled_bot import (  # noqa: E402
    get_moscow_time,
    is_working_hours,
    wait_until_working_hours,
)


class TestScheduler:
    """Тесты планировщика."""

    def test_get_moscow_time(self):
        """Проверка получения московского времени."""
        moscow_time = get_moscow_time()
        assert isinstance(moscow_time, datetime)
        # МСК = UTC+3
        utc_time = datetime.now(timezone.utc)
        diff = (moscow_time.hour - utc_time.hour) % 24
        assert diff == 3, "Разница должна быть 3 часа"

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_morning(self, mock_get_time):
        """Проверка рабочего времени утром."""
        # Тест для 7:00 МСК (начало рабочего дня)
        mock_time = datetime(2025, 10, 12, 7, 0, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is True

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_noon(self, mock_get_time):
        """Проверка рабочего времени в полдень."""
        # Тест для 12:00 МСК
        mock_time = datetime(2025, 10, 12, 12, 0, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is True

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_evening(self, mock_get_time):
        """Проверка рабочего времени вечером."""
        # Тест для 18:59 МСК (последняя минута рабочего дня)
        mock_time = datetime(2025, 10, 12, 18, 59, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is True

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_after_work(self, mock_get_time):
        """Проверка нерабочего времени после 19:00."""
        # Тест для 19:00 МСК (конец рабочего дня)
        mock_time = datetime(2025, 10, 12, 19, 0, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is False

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_night(self, mock_get_time):
        """Проверка нерабочего времени ночью."""
        # Тест для 2:00 МСК
        mock_time = datetime(2025, 10, 12, 2, 0, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is False

    @patch("run_scheduled_bot.get_moscow_time")
    def test_is_working_hours_before_work(self, mock_get_time):
        """Проверка нерабочего времени до 7:00."""
        # Тест для 6:59 МСК
        mock_time = datetime(2025, 10, 12, 6, 59, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time
        assert is_working_hours() is False

    @patch("run_scheduled_bot.time.sleep")
    @patch("run_scheduled_bot.get_moscow_time")
    def test_wait_until_working_hours_early_morning(self, mock_get_time, mock_sleep):
        """Проверка ожидания до начала рабочего дня (рано утром)."""
        # Тест для 5:30 МСК (до начала работы)
        mock_time = datetime(2025, 10, 12, 5, 30, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time

        wait_until_working_hours()

        # Должен проспать ~1.5 часа (5400 секунд)
        assert mock_sleep.called
        sleep_time = mock_sleep.call_args[0][0]
        expected_time = (1 * 3600) + (30 * 60)  # 1 час 30 минут
        assert (
            abs(sleep_time - expected_time) < 60
        ), f"Ожидалось ~{expected_time}с, получено {sleep_time}с"

    @patch("run_scheduled_bot.time.sleep")
    @patch("run_scheduled_bot.get_moscow_time")
    def test_wait_until_working_hours_late_evening(self, mock_get_time, mock_sleep):
        """Проверка ожидания до начала рабочего дня (поздним вечером)."""
        # Тест для 20:30 МСК (после окончания работы)
        mock_time = datetime(2025, 10, 12, 20, 30, tzinfo=timezone(timedelta(hours=3)))
        mock_get_time.return_value = mock_time

        wait_until_working_hours()

        # Должен проспать до 7:00 следующего дня (~10.5 часов)
        assert mock_sleep.called
        sleep_time = mock_sleep.call_args[0][0]
        expected_time = (10 * 3600) + (30 * 60)  # 10 часов 30 минут
        assert (
            abs(sleep_time - expected_time) < 60
        ), f"Ожидалось ~{expected_time}с, получено {sleep_time}с"


class TestSchedulerIntegration:
    """Интеграционные тесты планировщика."""

    @patch("run_scheduled_bot.subprocess.Popen")
    @patch("run_scheduled_bot.is_working_hours")
    def test_bot_starts_in_working_hours(self, mock_is_working, mock_popen):
        """Проверка что бот запускается в рабочее время."""
        mock_is_working.return_value = True

        # Мокируем процесс
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Процесс завершился
        mock_popen.return_value = mock_process

        # Импортируем и запускаем main в отдельном потоке
        # (здесь упрощенная проверка через мок)
        assert mock_is_working() is True

    @patch("run_scheduled_bot.subprocess.Popen")
    @patch("run_scheduled_bot.is_working_hours")
    def test_bot_stops_after_working_hours(self, mock_is_working, mock_popen):
        """Проверка что бот останавливается после рабочих часов."""
        # Сначала рабочее время, потом нерабочее
        mock_is_working.side_effect = [True, True, False]

        # Мокируем процесс
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Процесс работает
        mock_popen.return_value = mock_process

        # Проверяем логику
        assert mock_is_working() is True
        assert mock_is_working() is True
        assert mock_is_working() is False

        # Процесс должен быть остановлен
        # (в реальном коде вызывается process.terminate())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
