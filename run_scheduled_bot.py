#!/usr/bin/env python3
"""
Скрипт-обёртка для запуска бота по расписанию в Railway
Бот работает только с 7:00 до 19:00 МСК
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from loguru import logger


def get_moscow_time():
    """Получает текущее время в МСК"""
    moscow_offset = timedelta(hours=3)
    moscow_tz = timezone(moscow_offset)
    return datetime.now(moscow_tz)


def is_working_hours():
    """Проверяет рабочее время: 7:00-19:00 МСК"""
    moscow_time = get_moscow_time()
    current_hour = moscow_time.hour
    return 7 <= current_hour < 19


def wait_until_working_hours():
    """Ожидает начала рабочего дня"""
    moscow_time = get_moscow_time()
    current_hour = moscow_time.hour

    if current_hour < 7:
        # До 7:00 - ждём до 7:00
        hours_to_wait = 7 - current_hour
        minutes_to_wait = 60 - moscow_time.minute
        total_seconds = (hours_to_wait - 1) * 3600 + minutes_to_wait * 60
    else:
        # После 19:00 - ждём до 7:00 следующего дня
        hours_to_wait = 24 - current_hour + 7
        minutes_to_wait = 60 - moscow_time.minute
        total_seconds = (hours_to_wait - 1) * 3600 + minutes_to_wait * 60

    logger.info(
        f"⏰ Нерабочее время. Текущее время МСК: {moscow_time.strftime('%H:%M')}"
    )
    logger.info(
        f"💤 Бот будет запущен в 7:00 МСК (через {hours_to_wait}ч {minutes_to_wait}мин)"
    )

    # Спим до начала рабочего дня
    time.sleep(total_seconds)


def run_bot():
    """Запускает основной бот"""
    logger.info("🤖 Запуск основного бота...")

    # Запускаем бот как подпроцесс
    process = subprocess.Popen(
        [sys.executable, "bot/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    logger.info(f"✅ Бот запущен (PID: {process.pid})")

    # Мониторим рабочее время
    while True:
        # Проверяем каждые 60 секунд
        time.sleep(60)

        # Проверяем, работает ли процесс
        if process.poll() is not None:
            logger.warning("⚠️ Процесс бота завершился")
            break

        # Проверяем рабочее время
        if not is_working_hours():
            moscow_time = get_moscow_time()
            logger.info(f"⏰ Рабочий день окончен: {moscow_time.strftime('%H:%M')} МСК")
            logger.info("🛑 Останавливаем бота...")

            # Останавливаем процесс
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Принудительная остановка бота")
                process.kill()
                process.wait()

            logger.info("✅ Бот остановлен")
            break

    return process.returncode


def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("🚀 Запуск планировщика бота РПРЗ")
    logger.info("📅 Рабочие часы: 7:00-19:00 МСК")
    logger.info("=" * 60)
    
    while True:
        # Ждём начала рабочего дня, если сейчас нерабочее время
        if not is_working_hours():
            wait_until_working_hours()
        
        # Запускаем бота
        moscow_time = get_moscow_time()
        logger.info(f"✅ Начало рабочего дня: {moscow_time.strftime('%H:%M')} МСК")
        
        # В рабочее время - просто импортируем и запускаем бот напрямую
        logger.info("🚀 Запуск основного бота напрямую...")
        
        try:
            # Импортируем и запускаем main.py напрямую
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            # Запускаем бот
            from bot.main import main as bot_main
            bot_main()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Бот остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⏹️ Планировщик остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка планировщика: {e}")
        sys.exit(1)
