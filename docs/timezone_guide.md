# Руководство по работе с часовыми поясами

## Проблема

Бот может быть недоступен, если системное время не соответствует МСК (Europe/Moscow). Это происходит потому, что проверка рабочих часов использует локальное время системы.

## Решение

Добавлен модуль `bot/utils/timezone_helper.py`, который:
- ✅ Всегда использует строго московское время (МСК)
- ✅ Поддерживает тестовый режим
- ✅ Позволяет отключить проверку времени
- ✅ Покрыт автотестами

## Использование

### 1. В коде бота

```python
from bot.utils.timezone_helper import TimezoneHelper

# Создать экземпляр
tz_helper = TimezoneHelper()

# Получить московское время
msk_time = tz_helper.get_moscow_time()
print(f"Время в Москве: {msk_time}")

# Проверить рабочие часы (07:00-20:00 МСК по умолчанию)
if tz_helper.is_working_hours():
    print("Бот работает")
else:
    print("Вне рабочих часов")

# Проверить с custom временем
from datetime import time

if tz_helper.is_working_hours(
    start_time=time(8, 0),   # 08:00
    end_time=time(22, 0)      # 22:00
):
    print("Бот работает в расширенном режиме")

# Получить детальный статус
status = tz_helper.get_time_status()
print(status)
# {
#     'current_time_msk': datetime(...),
#     'current_time_str': '14:30:00',
#     'is_working_hours': True,
#     'work_start': '07:00',
#     'work_end': '20:00',
#     'test_mode': False,
#     'time_check_disabled': False,
#     'timezone': 'Europe/Moscow',
#     'has_zoneinfo': True
# }

# Форматированный вывод
print(tz_helper.format_work_hours())
# 🕐 Рабочие часы: 07:00-20:00 МСК
# 🕐 Текущее время МСК: 14:30:00
# ✅ Бот работает
```

### 2. Переменные окружения

#### TEST_MODE
Отключает **все** ограничения безопасности (время, лимиты, и т.д.)

```bash
# Linux/Mac
export TEST_MODE=1
python bot/main_refactored.py

# Windows PowerShell
$env:TEST_MODE=1
python bot/main_refactored.py

# В .env файле
TEST_MODE=1
```

#### DISABLE_TIME_CHECK
Отключает **только** проверку рабочего времени (бот работает 24/7)

```bash
# Linux/Mac
export DISABLE_TIME_CHECK=1
python bot/main_refactored.py

# Windows PowerShell
$env:DISABLE_TIME_CHECK=1
python bot/main_refactored.py

# В .env файле
DISABLE_TIME_CHECK=1
```

### 3. Конфигурация рабочих часов

По умолчанию: **07:00 - 20:00 МСК**

Изменить в коде:

```python
from bot.utils.timezone_helper import TimezoneHelper
from datetime import time

tz_helper = TimezoneHelper()

# Пример: 06:00 - 23:00
if tz_helper.is_working_hours(
    start_time=time(6, 0),
    end_time=time(23, 0)
):
    # Бот работает
    pass
```

Или отредактировать константы в `bot/utils/timezone_helper.py`:

```python
class TimezoneHelper:
    DEFAULT_WORK_START = time(6, 0)   # 06:00
    DEFAULT_WORK_END = time(23, 0)    # 23:00
```

## Тестирование

Запустить тесты:

```bash
python tests/test_timezone.py
```

Тесты проверяют:
- ✅ Получение московского времени
- ✅ Проверку рабочих часов (внутри диапазона)
- ✅ Проверку рабочих часов (вне диапазона)
- ✅ Работу TEST_MODE
- ✅ Работу DISABLE_TIME_CHECK
- ✅ Получение статуса времени
- ✅ Форматирование
- ✅ Граничные случаи (07:00, 20:00, 06:59, 20:01)

## Диагностика проблем

### Бот недоступен в рабочие часы

1. **Проверить время на сервере**:
```bash
# Системное время
date

# Время в Москве
TZ=Europe/Moscow date

# Python проверка
python -c "from bot.utils.timezone_helper import TimezoneHelper; print(TimezoneHelper().format_work_hours())"
```

2. **Временно отключить проверку**:
```bash
# Для диагностики
TEST_MODE=1 python bot/main_refactored.py
```

3. **Проверить логи**:
Ищите строки типа:
- `🕐 Рабочие часы бота: 7:00-20:00 МСК`
- `🕐 Текущее время МСК: XX:XX:XX`
- `✅ Бот работает` или `❌ Вне рабочих часов`

### Бот работает в неправильном часовом поясе

Проблема решена автоматически — модуль всегда использует `Europe/Moscow`, независимо от системных настроек.

### Нужен режим 24/7

Добавьте в `.env`:
```env
DISABLE_TIME_CHECK=1
```

Или запустите с флагом:
```bash
DISABLE_TIME_CHECK=1 python bot/main_refactored.py
```

## Требования

- Python 3.9+ (с `zoneinfo`)
- Или Python 3.7-3.8 с установленным `backports.zoneinfo`

Для старых версий Python:
```bash
pip install backports.zoneinfo
```

## Примеры сценариев

### Сценарий 1: Разработка и тестирование
```bash
# Отключить все ограничения
TEST_MODE=1 python bot/main_refactored.py
```

### Сценарий 2: Продакшн с расширенными часами
```python
# В коде бота
if tz_helper.is_working_hours(
    start_time=time(6, 0),   # 06:00
    end_time=time(23, 0)      # 23:00
):
    # Обработка сообщений
    pass
```

### Сценарий 3: Режим 24/7
```bash
# В .env
DISABLE_TIME_CHECK=1
```

### Сценарий 4: Диагностика часового пояса
```python
from bot.utils.timezone_helper import TimezoneHelper

tz = TimezoneHelper()
status = tz.get_time_status()

print(f"Московское время: {status['current_time_str']}")
print(f"Рабочие часы: {status['work_start']}-{status['work_end']}")
print(f"Статус: {'Работает' if status['is_working_hours'] else 'Не работает'}")
print(f"Часовой пояс: {status['timezone']}")
print(f"zoneinfo доступен: {status['has_zoneinfo']}")
```

## FAQ

**Q: Почему бот не работает вечером/ночью?**  
A: По умолчанию бот работает 07:00-20:00 МСК. Используйте `DISABLE_TIME_CHECK=1` для режима 24/7.

**Q: Время на сервере не московское, что делать?**  
A: Ничего, модуль автоматически конвертирует в МСК.

**Q: Как проверить текущее время бота?**  
A: `python -c "from bot.utils.timezone_helper import TimezoneHelper; print(TimezoneHelper().format_work_hours())"`

**Q: Можно ли изменить рабочие часы без изменения кода?**  
A: Сейчас нет, но можно добавить переменные `WORK_START` и `WORK_END` в `.env`. Создайте issue если нужно.

**Q: Что делать при ошибке "No module named 'zoneinfo'"?**  
A: Установите `pip install backports.zoneinfo` для Python < 3.9.

---

**Версия**: 1.0.0  
**Дата**: 30.10.2025  
**Статус**: ✅ Готово к использованию

