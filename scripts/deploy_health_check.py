#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health check скрипт для проверки работоспособности бота после деплоя.

Используется в CI/CD для валидации успешного деплоя.
"""

import os
import sys
import time
from typing import Optional

import requests

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Конфигурация
TELEGRAM_API_BASE = "https://api.telegram.org/bot"
HEALTH_CHECK_TIMEOUT = 30  # секунд
MAX_RETRIES = 3
RETRY_DELAY = 5  # секунд


def get_bot_token() -> Optional[str]:
    """Получает токен бота из переменных окружения."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        return None
    return token


def check_bot_info(token: str) -> bool:
    """Проверяет информацию о боте через getMe API."""
    url = f"{TELEGRAM_API_BASE}{token}/getMe"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                username = bot_info.get("username", "unknown")
                first_name = bot_info.get("first_name", "unknown")
                print(f"✅ Бот подключен: @{username} ({first_name})")
                return True
            else:
                print(f"❌ API вернул ошибку: {data.get('description', 'unknown')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Таймаут при подключении к Telegram API")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False


def check_bot_updates(token: str) -> bool:
    """Проверяет возможность получения обновлений."""
    url = f"{TELEGRAM_API_BASE}{token}/getUpdates"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print("✅ Получение обновлений работает")
                return True
            else:
                print(
                    f"⚠️ Не удалось получить обновления: {data.get('description', 'unknown')}"
                )
                return False
        else:
            print(f"❌ HTTP ошибка при getUpdates: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка при проверке обновлений: {e}")
        return False


def check_webhook_info(token: str) -> bool:
    """Проверяет информацию о webhook (если используется)."""
    url = f"{TELEGRAM_API_BASE}{token}/getWebhookInfo"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                webhook_info = data.get("result", {})
                webhook_url = webhook_info.get("url", "")

                if webhook_url:
                    print(f"ℹ️ Webhook настроен: {webhook_url}")
                    pending = webhook_info.get("pending_update_count", 0)
                    print(f"ℹ️ Ожидает обработки: {pending} обновлений")
                else:
                    print("ℹ️ Webhook не настроен (используется polling)")

                return True
        return False
    except Exception as e:
        print(f"⚠️ Не удалось проверить webhook: {e}")
        return False


def run_health_check_with_retry() -> bool:
    """Запускает health check с повторными попытками."""
    token = get_bot_token()
    if not token:
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔍 Попытка {attempt}/{MAX_RETRIES}")
        print("-" * 60)

        # Основная проверка - getMe
        if check_bot_info(token):
            # Дополнительные проверки
            check_bot_updates(token)
            check_webhook_info(token)
            return True

        if attempt < MAX_RETRIES:
            print(f"⏳ Ожидание {RETRY_DELAY} секунд перед следующей попыткой...")
            time.sleep(RETRY_DELAY)

    return False


def print_header():
    """Выводит заголовок."""
    print("\n" + "=" * 60)
    print("🏥 HEALTH CHECK - Проверка работоспособности бота")
    print("=" * 60)


def print_footer(success: bool):
    """Выводит итоги."""
    print("\n" + "=" * 60)
    if success:
        print("✅ HEALTH CHECK PASSED - Бот работает нормально")
        print("🎉 Деплой успешен!")
    else:
        print("❌ HEALTH CHECK FAILED - Бот не отвечает")
        print("⚠️ Требуется проверка или rollback!")
    print("=" * 60 + "\n")


def main():
    """Главная функция."""
    print_header()

    # Запускаем проверку
    success = run_health_check_with_retry()

    # Выводим итоги
    print_footer(success)

    # Возвращаем код выхода
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
