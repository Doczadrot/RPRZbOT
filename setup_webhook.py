#!/usr/bin/env python3
"""
Скрипт для установки webhook после деплоя на Railway
Используйте этот скрипт один раз после первого деплоя
"""

import os
import sys
from dotenv import load_dotenv
import telebot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

if not RAILWAY_PUBLIC_DOMAIN:
    print("❌ RAILWAY_PUBLIC_DOMAIN не найден!")
    print("💡 Убедитесь, что в Railway включен Public Domain для вашего сервиса")
    sys.exit(1)

# Формируем URL webhook
webhook_url = f"https://{RAILWAY_PUBLIC_DOMAIN}/webhook"

print(f"🔧 Установка webhook: {webhook_url}")

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    
    # Удаляем старый webhook
    bot.remove_webhook()
    print("✅ Старый webhook удален")
    
    # Устанавливаем новый webhook
    result = bot.set_webhook(url=webhook_url)
    
    if result:
        print(f"✅ Webhook успешно установлен!")
        print(f"📍 URL: {webhook_url}")
        
        # Проверяем информацию о webhook
        webhook_info = bot.get_webhook_info()
        print(f"\n📊 Информация о webhook:")
        print(f"   URL: {webhook_info.url}")
        print(f"   Ожидающих обновлений: {webhook_info.pending_update_count}")
    else:
        print("❌ Не удалось установить webhook")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

