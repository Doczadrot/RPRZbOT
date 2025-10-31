"""
Тесты для модуля работы с часовыми поясами
"""
import os
import sys
from datetime import time, datetime
from unittest.mock import patch, MagicMock

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.utils.timezone_helper import TimezoneHelper

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False


def test_get_moscow_time():
    """Тест получения московского времени"""
    print("🧪 Тест: Получение московского времени...")
    
    helper = TimezoneHelper()
    msk_time = helper.get_moscow_time()
    
    assert isinstance(msk_time, datetime), "Должен вернуть datetime"
    print(f"✅ Московское время: {msk_time}")


def test_is_working_hours_in_range():
    """Тест проверки рабочих часов - внутри диапазона"""
    print("🧪 Тест: Проверка рабочих часов (внутри диапазона)...")
    
    helper = TimezoneHelper()
    
    # Мокаем московское время на 12:00 (середина дня)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(12, 0)
        mock_time.return_value = mock_dt
        
        # Без TEST_MODE
        helper.test_mode = False
        helper.disable_time_check = False
        
        result = helper.is_working_hours(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert result is True, "12:00 должно быть в диапазоне 07:00-20:00"
    
    print("✅ Проверка в диапазоне работает")


def test_is_working_hours_out_of_range():
    """Тест проверки рабочих часов - вне диапазона"""
    print("🧪 Тест: Проверка рабочих часов (вне диапазона)...")
    
    helper = TimezoneHelper()
    
    # Мокаем московское время на 22:00 (поздний вечер)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(22, 0)
        mock_time.return_value = mock_dt
        
        # Без TEST_MODE
        helper.test_mode = False
        helper.disable_time_check = False
        
        result = helper.is_working_hours(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert result is False, "22:00 не должно быть в диапазоне 07:00-20:00"
    
    print("✅ Проверка вне диапазона работает")


def test_test_mode_overrides():
    """Тест что TEST_MODE отключает проверку времени"""
    print("🧪 Тест: TEST_MODE отключает проверку...")
    
    # Устанавливаем TEST_MODE
    os.environ['TEST_MODE'] = '1'
    helper = TimezoneHelper()
    
    # Мокаем время вне рабочих часов (02:00)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(2, 0)
        mock_time.return_value = mock_dt
        
        result = helper.is_working_hours(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert result is True, "TEST_MODE должен игнорировать проверку времени"
    
    # Очищаем переменную окружения
    del os.environ['TEST_MODE']
    
    print("✅ TEST_MODE корректно отключает проверку")


def test_disable_time_check():
    """Тест что DISABLE_TIME_CHECK отключает проверку времени"""
    print("🧪 Тест: DISABLE_TIME_CHECK отключает проверку...")
    
    # Устанавливаем DISABLE_TIME_CHECK
    os.environ['DISABLE_TIME_CHECK'] = '1'
    helper = TimezoneHelper()
    
    # Мокаем время вне рабочих часов (03:00)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(3, 0)
        mock_time.return_value = mock_dt
        
        result = helper.is_working_hours(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert result is True, "DISABLE_TIME_CHECK должен игнорировать проверку времени"
    
    # Очищаем переменную окружения
    del os.environ['DISABLE_TIME_CHECK']
    
    print("✅ DISABLE_TIME_CHECK корректно отключает проверку")


def test_get_time_status():
    """Тест получения статуса времени"""
    print("🧪 Тест: Получение статуса времени...")
    
    helper = TimezoneHelper()
    
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(14, 30)
        mock_dt.strftime.return_value = "14:30:00"
        mock_time.return_value = mock_dt
        
        helper.test_mode = False
        helper.disable_time_check = False
        
        status = helper.get_time_status(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert status['current_time_str'] == "14:30:00"
        assert status['is_working_hours'] is True
        assert status['work_start'] == "07:00"
        assert status['work_end'] == "20:00"
        assert status['timezone'] == "Europe/Moscow"
        assert status['test_mode'] is False
        assert status['time_check_disabled'] is False
    
    print("✅ Статус времени корректный")


def test_format_work_hours():
    """Тест форматирования рабочих часов"""
    print("🧪 Тест: Форматирование рабочих часов...")
    
    helper = TimezoneHelper()
    
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(10, 0)
        mock_dt.strftime.return_value = "10:00:00"
        mock_time.return_value = mock_dt
        
        helper.test_mode = False
        helper.disable_time_check = False
        
        formatted = helper.format_work_hours(
            start_time=time(7, 0),
            end_time=time(20, 0)
        )
        
        assert "07:00-20:00" in formatted
        assert "10:00:00" in formatted
        assert "МСК" in formatted
        assert "✅ Бот работает" in formatted
    
    print("✅ Форматирование работает корректно")


def test_edge_cases():
    """Тест граничных случаев"""
    print("🧪 Тест: Граничные случаи...")
    
    helper = TimezoneHelper()
    helper.test_mode = False
    helper.disable_time_check = False
    
    # Тест на начало рабочего дня (07:00)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(7, 0)
        mock_time.return_value = mock_dt
        
        assert helper.is_working_hours(time(7, 0), time(20, 0)) is True
    
    # Тест на конец рабочего дня (20:00)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(20, 0)
        mock_time.return_value = mock_dt
        
        assert helper.is_working_hours(time(7, 0), time(20, 0)) is True
    
    # Тест на минуту до начала (06:59)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(6, 59)
        mock_time.return_value = mock_dt
        
        assert helper.is_working_hours(time(7, 0), time(20, 0)) is False
    
    # Тест на минуту после окончания (20:01)
    with patch.object(helper, 'get_moscow_time') as mock_time:
        mock_dt = MagicMock()
        mock_dt.time.return_value = time(20, 1)
        mock_time.return_value = mock_dt
        
        assert helper.is_working_hours(time(7, 0), time(20, 0)) is False
    
    print("✅ Граничные случаи обработаны корректно")


def run_all_tests():
    """Запустить все тесты"""
    print("\n🚀 Запуск тестов часовых поясов...\n")
    
    try:
        test_get_moscow_time()
        test_is_working_hours_in_range()
        test_is_working_hours_out_of_range()
        test_test_mode_overrides()
        test_disable_time_check()
        test_get_time_status()
        test_format_work_hours()
        test_edge_cases()
        
        print("\n🎉 Все тесты часовых поясов прошли успешно!")
        print("✅ Защита от проблем с часовыми поясами работает")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

