#!/usr/bin/env python3
"""
Serverless версия бота для Railway Free Plan
Использует webhook вместо polling для экономии ресурсов
"""

import os
import sys
import threading
import time
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from loguru import logger
import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения
load_dotenv()

# Импортируем обработчики
try:
    from bot.handlers import (
        finish_danger_report,
        get_back_keyboard,
        get_main_menu_keyboard,
        get_media_keyboard,
        handle_danger_report_location,
        handle_danger_report_media,
        handle_danger_report_text,
        handle_improvement_suggestion_text,
        handle_rprz_assistant_text,
        log_activity,
        set_bot_instance,
    )
except ImportError:
    from handlers import (
        finish_danger_report,
        get_back_keyboard,
        get_main_menu_keyboard,
        get_media_keyboard,
        handle_danger_report_location,
        handle_danger_report_media,
        handle_danger_report_text,
        handle_improvement_suggestion_text,
        handle_rprz_assistant_text,
        log_activity,
        set_bot_instance,
    )

# Импортируем модуль main.py для использования функций
# ВАЖНО: Импортируем после определения глобальных переменных
import bot.main as main_module

# Импортируем необходимые функции и классы
BOT_TOKEN = main_module.BOT_TOKEN
load_placeholders = main_module.load_placeholders
BotStates = main_module.BotStates

# Настройка логирования для serverless
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
    level="INFO",
    rotation="10 MB",
    compression="zip",
    encoding="utf-8",
    errors="replace",
)

logger.add(
    "logs/errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
    level="ERROR",
    rotation="10 MB",
    compression="zip",
    encoding="utf-8",
    errors="replace",
)

# Глобальные переменные
user_states = {}
user_data = {}
user_history = {}
placeholders = {}
bot = None

# Создаем Flask приложение для webhook
app = Flask(__name__)

# Флаг для keepalive механизма
_keepalive_running = False
_keepalive_thread = None


def keepalive_worker():
    """Периодически пингует /ping endpoint для предотвращения sleep mode на Railway"""
    global _keepalive_running
    
    # Интервал пинга (каждые 5 минут)
    ping_interval = int(os.getenv("KEEPALIVE_INTERVAL", 300))  # 5 минут по умолчанию
    
    # URL для пинга (Railway автоматически устанавливает эти переменные)
    # Приоритет: RAILWAY_PUBLIC_DOMAIN > RAILWAY_STATIC_URL > PUBLIC_URL
    base_url = (
        os.getenv("RAILWAY_PUBLIC_DOMAIN") or 
        os.getenv("RAILWAY_STATIC_URL") or 
        os.getenv("PUBLIC_URL")
    )
    
    if not base_url:
        logger.warning("⚠️ KEEPALIVE: PUBLIC_URL не установлен, keepalive отключен")
        logger.warning("   Railway автоматически устанавливает RAILWAY_PUBLIC_DOMAIN")
        logger.warning("   Или установите переменную окружения PUBLIC_URL вручную")
        return
    
    # Убираем протокол если есть
    base_url = base_url.replace("https://", "").replace("http://", "")
    ping_url = f"https://{base_url}/ping"
    
    logger.info(f"🔄 Keepalive активирован: пинг каждые {ping_interval} секунд")
    logger.info(f"   URL: {ping_url}")
    
    while _keepalive_running:
        try:
            response = requests.get(ping_url, timeout=10)
            if response.status_code == 200:
                logger.debug(f"✅ Keepalive ping успешен: {response.json()}")
            else:
                logger.warning(f"⚠️ Keepalive ping вернул код {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Ошибка keepalive ping: {e}")
        
        # Ждем перед следующим пингом
        for _ in range(ping_interval):
            if not _keepalive_running:
                break
            time.sleep(1)
    
    logger.info("🛑 Keepalive остановлен")


def start_keepalive():
    """Запускает keepalive механизм в отдельном потоке"""
    global _keepalive_running, _keepalive_thread
    
    # Проверяем, нужно ли включать keepalive
    enable_keepalive = os.getenv("ENABLE_KEEPALIVE", "true").lower() == "true"
    
    if not enable_keepalive:
        logger.info("ℹ️ Keepalive отключен через ENABLE_KEEPALIVE=false")
        return
    
    if _keepalive_running:
        logger.warning("⚠️ Keepalive уже запущен")
        return
    
    _keepalive_running = True
    _keepalive_thread = threading.Thread(target=keepalive_worker, daemon=True)
    _keepalive_thread.start()
    logger.info("🚀 Keepalive поток запущен")


def stop_keepalive():
    """Останавливает keepalive механизм"""
    global _keepalive_running, _keepalive_thread
    
    if not _keepalive_running:
        return
    
    _keepalive_running = False
    if _keepalive_thread:
        _keepalive_thread.join(timeout=5)
    logger.info("🛑 Keepalive остановлен")


def init_bot():
    """Инициализация бота и регистрация обработчиков"""
    global bot, placeholders
    
    if not BOT_TOKEN or len(BOT_TOKEN) < 10:
        logger.error("❌ BOT_TOKEN не найден!")
        return False
    
    try:
        # Инициализация бота
        state_storage = StateMemoryStorage()
        bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
        
        # Устанавливаем глобальный экземпляр бота для handlers
        set_bot_instance(bot)
        
        # Загружаем данные
        placeholders = load_placeholders()
        logger.info("✅ Данные убежищ загружены")
        
        # Инициализируем глобальные переменные в main.py модуле
        main_module.user_states = user_states
        main_module.user_data = user_data
        main_module.user_history = user_history
        main_module.bot = bot
        main_module.placeholders = placeholders
        
        # Регистрируем обработчики из main.py
        bot.message_handler(
            func=lambda message: message.chat.id not in user_states
            and message.content_type == "text"
            and not message.text.startswith("/")
        )(main_module.handle_uninitialized_user)
        bot.message_handler(commands=["start"])(main_module.start_command)
        bot.message_handler(commands=["help"])(main_module.help_command)
        bot.message_handler(commands=["my_history"])(main_module.history_command)
        bot.message_handler(content_types=["text"])(main_module.handle_text)
        bot.message_handler(content_types=["location"])(main_module.handle_location)
        bot.message_handler(content_types=["photo", "video", "document"])(main_module.handle_media)
        bot.callback_query_handler(func=lambda call: True)(main_module.handle_callback)
        
        # Проверяем подключение
        bot_info = bot.get_me()
        logger.info(f"✅ Бот подключен: @{bot_info.username}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


@app.route("/", methods=["GET"])
def index():
    """Главная страница"""
    return jsonify({
        "status": "online",
        "service": "RPRZ Safety Bot",
        "mode": "serverless",
        "webhook": "configured" if bot else "not_configured"
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint для Railway"""
    try:
        webhook_info = None
        if bot:
            try:
                webhook_info = bot.get_webhook_info()
            except Exception:
                pass
        
        return jsonify({
            "status": "healthy",
            "service": "telegram-bot",
            "mode": "serverless",
            "webhook_configured": bot is not None,
            "bot_token_set": bool(BOT_TOKEN),
            "webhook_info": str(webhook_info) if webhook_info else None
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/ping", methods=["GET"])
def ping():
    """Простой ping endpoint для keepalive механизма Railway"""
    return jsonify({"status": "pong", "timestamp": time.time()}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint для получения обновлений от Telegram"""
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        try:
            bot.process_new_updates([update])
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"ok": False, "error": str(e)}), 500
    else:
        return jsonify({"error": "Invalid content type"}), 400


@app.route("/set_webhook", methods=["POST"])
def set_webhook_route():
    """Установка webhook URL (для инициализации)"""
    try:
        webhook_url = request.json.get("url")
        if not webhook_url:
            return jsonify({"error": "URL required"}), 400
        
        if not bot:
            return jsonify({"error": "Bot not initialized"}), 500
        
        # Устанавливаем webhook
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ Webhook установлен: {webhook_url}")
        webhook_info = bot.get_webhook_info()
        
        return jsonify({
            "ok": result,
            "webhook_url": webhook_url,
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count
            }
        }), 200
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# Инициализация бота при импорте модуля (для gunicorn)
# Это нужно чтобы бот инициализировался даже когда gunicorn импортирует модуль
logger.info("🚀 Инициализация serverless версии бота для Railway Free Plan")

# Инициализация бота
if not init_bot():
    logger.error("❌ Не удалось инициализировать бота")
    # Не выходим здесь, чтобы gunicorn мог запуститься и показать ошибку в логах
else:
    # Запускаем keepalive механизм для предотвращения sleep mode на Railway
    start_keepalive()

if __name__ == "__main__":
    # Локальная разработка - используем Flask dev server
    logger.info("💻 Local development mode - using Flask dev server")
    
    # Получаем порт из переменной окружения
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🌐 Запуск Flask сервера на порту {port}")
    logger.info("📡 Webhook endpoint: /webhook")
    logger.info("❤️ Health check: /health")
    logger.info("🏓 Ping endpoint: /ping (для keepalive)")
    logger.info("🔧 Set webhook: POST /set_webhook")
    
    app.run(host="0.0.0.0", port=port, debug=False)
