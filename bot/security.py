"""
Модуль безопасности для Telegram-бота РПРЗ
Обеспечивает защиту от спама, флуда и вредоносного контента
"""

import os
import re
import time
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, Tuple
from loguru import logger


class SecurityManager:
    """Централизованный менеджер безопасности"""

    def __init__(self):
        # Rate limiting: {user_id: [timestamp1, timestamp2, ...]}
        self.user_requests = defaultdict(list)

        # Флуд-контроль: {user_id: {action: last_timestamp}}
        self.user_last_action = defaultdict(dict)

        # Whitelist/Blacklist
        self.blacklist = set()
        self.whitelist = set()

        # Счетчик подозрительной активности: {user_id: count}
        self.suspicious_activity = defaultdict(int)

        # Конфигурация
        self.MAX_REQUESTS_PER_MINUTE = int(os.getenv("SPAM_LIMIT", "10"))
        self.FLOOD_INTERVAL_SECONDS = int(os.getenv("FLOOD_INTERVAL", "2"))
        self.MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "4096"))
        self.MAX_SUSPICIOUS_SCORE = 10

        # Админ чат ID
        admin_chat_id_str = os.getenv("ADMIN_CHAT_ID")
        self.ADMIN_CHAT_ID = int(admin_chat_id_str) if admin_chat_id_str else None

        # Добавляем админа в whitelist
        if self.ADMIN_CHAT_ID:
            self.whitelist.add(self.ADMIN_CHAT_ID)

        logger.info("✅ SecurityManager инициализирован")

    def check_rate_limit(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверяет rate limiting для пользователя

        Returns:
            (is_allowed, error_message)
        """
        # Whitelist пропускаем
        if user_id in self.whitelist:
            return True, None

        # Blacklist блокируем
        if user_id in self.blacklist:
            logger.warning(f"🚫 Заблокированный пользователь: {user_id}")
            return False, "❌ Вы заблокированы администратором"

        current_time = time.time()

        # Очищаем старые запросы (старше 1 минуты)
        self.user_requests[user_id] = [ts for ts in self.user_requests[user_id] if current_time - ts < 60]

        # Проверяем лимит
        if len(self.user_requests[user_id]) >= self.MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"⚠️ Rate limit для пользователя {user_id}")
            self._add_suspicious_activity(user_id, "rate_limit_exceeded")
            return False, "⏳ Слишком много запросов. Подождите 1 минуту."

        # Добавляем текущий запрос
        self.user_requests[user_id].append(current_time)
        return True, None

    def check_flood(self, user_id: int, action: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет флуд (частые повторяющиеся действия)

        Returns:
            (is_allowed, error_message)
        """
        # Whitelist пропускаем
        if user_id in self.whitelist:
            return True, None

        current_time = time.time()
        last_action_time = self.user_last_action[user_id].get(action, 0)

        if current_time - last_action_time < self.FLOOD_INTERVAL_SECONDS:
            logger.warning(f"⚠️ Флуд от пользователя {user_id}: {action}")
            self._add_suspicious_activity(user_id, "flood")
            return False, f"⏳ Подождите {self.FLOOD_INTERVAL_SECONDS} секунд"

        self.user_last_action[user_id][action] = current_time
        return True, None

    def validate_text(self, text: str, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Валидирует текст на безопасность

        Returns:
            (is_valid, error_message)
        """
        if not text:
            return True, None

        # Проверка длины
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.warning(f"⚠️ Превышение длины текста от {user_id}: {len(text)}")
            return (False, f"❌ Текст слишком длинный (макс {self.MAX_TEXT_LENGTH} символов)")

        # Проверка на спам-паттерны
        spam_patterns = [
            r"https?://[^\s]+",  # Подозрительные ссылки (можно смягчить)
            r"@\w+bot",  # Упоминания других ботов
            r"[\u0400-\u04FF]{50,}",  # Слишком длинные слова на кириллице
        ]

        suspicious_count = 0
        for pattern in spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                suspicious_count += 1

        if suspicious_count >= 2:
            logger.warning(f"⚠️ Подозрительный текст от {user_id}")
            self._add_suspicious_activity(user_id, "suspicious_text")
            return False, "⚠️ Обнаружен подозрительный контент"

        return True, None

    def validate_file(
        self, file_size: int, file_type: str, user_id: int, max_size_mb: int = 20
    ) -> Tuple[bool, Optional[str]]:
        """
        Валидирует файл на безопасность

        Returns:
            (is_valid, error_message)
        """
        # Проверка размера
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            logger.warning(f"⚠️ Превышение размера файла от {user_id}: {file_size}")
            return False, f"❌ Файл слишком большой (макс {max_size_mb} МБ)"

        # Проверка типа файла (whitelist)
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/mpeg",
            "video/quicktime",
            "audio/mpeg",
            "audio/ogg",
            "application/pdf",
        ]

        if file_type and not any(file_type.startswith(allowed) for allowed in allowed_types):
            logger.warning(f"⚠️ Недопустимый тип файла от {user_id}: {file_type}")
            self._add_suspicious_activity(user_id, "invalid_file_type")
            return False, "❌ Недопустимый тип файла"

        return True, None

    def _add_suspicious_activity(self, user_id: int, reason: str):
        """Добавляет подозрительную активность пользователя"""
        self.suspicious_activity[user_id] += 1

        logger.warning(
            f"🚨 Подозрительная активность: user={user_id}, "
            f"reason={reason}, score={self.suspicious_activity[user_id]}"
        )

        # Автоматическая блокировка при превышении порога
        if self.suspicious_activity[user_id] >= self.MAX_SUSPICIOUS_SCORE:
            self.add_to_blacklist(user_id)
            logger.critical(f"🚫 Пользователь {user_id} автоматически заблокирован")

            # Уведомляем админа
            if self.ADMIN_CHAT_ID:
                self._notify_admin_about_block(user_id, reason)

    def _notify_admin_about_block(self, user_id: int, reason: str):
        """Уведомляет админа о блокировке"""
        # Логируем для админа (бот отправит через main.py)
        log_file = "logs/admin_critical.log"
        try:
            os.makedirs("logs", exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | " f"AUTO_BLOCK | user_id={user_id} | reason={reason}\n")
        except Exception as e:
            logger.error(f"Ошибка записи в admin_critical.log: {e}")

    def add_to_blacklist(self, user_id: int):
        """Добавляет пользователя в черный список"""
        self.blacklist.add(user_id)
        logger.warning(f"🚫 Пользователь {user_id} добавлен в blacklist")

    def remove_from_blacklist(self, user_id: int):
        """Удаляет пользователя из черного списка"""
        self.blacklist.discard(user_id)
        self.suspicious_activity[user_id] = 0
        logger.info(f"✅ Пользователь {user_id} удален из blacklist")

    def add_to_whitelist(self, user_id: int):
        """Добавляет пользователя в белый список"""
        self.whitelist.add(user_id)
        logger.info(f"✅ Пользователь {user_id} добавлен в whitelist")

    def get_user_security_info(self, user_id: int) -> Dict:
        """Возвращает информацию о безопасности пользователя"""
        return {
            "user_id": user_id,
            "is_whitelisted": user_id in self.whitelist,
            "is_blacklisted": user_id in self.blacklist,
            "suspicious_score": self.suspicious_activity[user_id],
            "requests_last_minute": len(self.user_requests[user_id]),
            "last_actions": dict(self.user_last_action[user_id]),
        }

    def reset_user_limits(self, user_id: int):
        """Сбрасывает лимиты для пользователя"""
        self.user_requests[user_id].clear()
        self.user_last_action[user_id].clear()
        logger.info(f"🔄 Лимиты сброшены для пользователя {user_id}")

    def clean_old_data(self):
        """Очищает старые данные (вызывать периодически)"""
        current_time = time.time()

        # Очищаем старые запросы
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [ts for ts in self.user_requests[user_id] if current_time - ts < 60]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]

        # Очищаем старые действия (старше 1 часа)
        for user_id in list(self.user_last_action.keys()):
            old_actions = {
                action: ts for action, ts in self.user_last_action[user_id].items() if current_time - ts < 3600
            }
            if old_actions:
                self.user_last_action[user_id] = old_actions
            else:
                del self.user_last_action[user_id]

        logger.debug("🧹 Старые данные безопасности очищены")


# Глобальный экземпляр
security_manager = SecurityManager()


def check_user_security(user_id: int, action: str = "general") -> Tuple[bool, Optional[str]]:
    """
    Проверяет безопасность для пользователя

    Args:
        user_id: ID пользователя
        action: Тип действия для флуд-контроля

    Returns:
        (is_allowed, error_message)
    """
    # Проверяем rate limit
    is_allowed, error = security_manager.check_rate_limit(user_id)
    if not is_allowed:
        return False, error

    # Проверяем флуд
    is_allowed, error = security_manager.check_flood(user_id, action)
    if not is_allowed:
        return False, error

    return True, None


def validate_user_text(text: str, user_id: int) -> Tuple[bool, Optional[str]]:
    """Валидирует текст от пользователя"""
    return security_manager.validate_text(text, user_id)


def validate_user_file(
    file_size: int, file_type: str, user_id: int, max_size_mb: int = 20
) -> Tuple[bool, Optional[str]]:
    """Валидирует файл от пользователя"""
    return security_manager.validate_file(file_size, file_type, user_id, max_size_mb)


def security_check_decorator(func):
    """
    Декоратор для автоматической проверки безопасности в обработчиках

    Использование:
        @security_check_decorator
        def my_handler(message):
            ...
    """

    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Проверяем базовую безопасность
        is_allowed, error_msg = check_user_security(user_id, action=func.__name__)
        if not is_allowed:
            # Если есть bot в kwargs, отправляем сообщение об ошибке
            if "bot" in kwargs:
                kwargs["bot"].send_message(chat_id, error_msg)
            logger.warning(f"🚫 Заблокирован запрос от {user_id}: {error_msg}")
            return

        # Если есть текст, валидируем его
        if hasattr(message, "text") and message.text:
            is_valid, error_msg = validate_user_text(message.text, user_id)
            if not is_valid:
                if "bot" in kwargs:
                    kwargs["bot"].send_message(chat_id, error_msg)
                logger.warning(f"🚫 Невалидный текст от {user_id}: {error_msg}")
                return

        # Вызываем оригинальную функцию
        return func(message, *args, **kwargs)

    return wrapper
