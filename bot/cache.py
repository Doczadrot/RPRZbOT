"""
Система кэширования для Telegram бота
Обеспечивает быстрый доступ к часто используемым данным
"""

import json
import os
import time
from functools import wraps
from typing import Any, Dict, Optional

from loguru import logger


class SimpleCache:
    """Простая система кэширования в памяти с возможностью сохранения на диск"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Args:
            max_size: Максимальное количество элементов в кэше
            ttl: Time to live в секундах (по умолчанию 1 час)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.cache_file = "logs/cache.json"

        # Загружаем кэш с диска при инициализации
        self._load_from_disk()

        logger.info(f"✅ SimpleCache инициализирован: max_size={max_size}, ttl={ttl}s")

    def _load_from_disk(self):
        """Загружает кэш с диска"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    current_time = time.time()

                    # Загружаем только неистекшие элементы
                    for key, value in data.items():
                        if current_time - value.get("timestamp", 0) < self.ttl:
                            self.cache[key] = value

                logger.info(f"📂 Загружен кэш с диска: {len(self.cache)} элементов")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки кэша: {e}")

    def _save_to_disk(self):
        """Сохраняет кэш на диск"""
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка сохранения кэша: {e}")

    def _clean_expired(self):
        """Удаляет истекшие элементы"""
        current_time = time.time()
        expired_keys = [
            key
            for key, value in self.cache.items()
            if current_time - value.get("timestamp", 0) >= self.ttl
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"🧹 Удалено истекших элементов кэша: {len(expired_keys)}")

    def _evict_oldest(self):
        """Удаляет самые старые элементы при превышении лимита"""
        if len(self.cache) >= self.max_size:
            # Сортируем по времени создания и удаляем самые старые
            sorted_items = sorted(
                self.cache.items(), key=lambda x: x[1].get("timestamp", 0)
            )

            # Удаляем 10% самых старых элементов
            to_remove = len(sorted_items) // 10
            for key, _ in sorted_items[:to_remove]:
                del self.cache[key]

            logger.debug(f"🗑️ Удалено старых элементов кэша: {to_remove}")

    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кэша"""
        self._clean_expired()

        if key in self.cache:
            value = self.cache[key]["value"]
            logger.debug(f"📥 Кэш HIT: {key}")
            return value

        logger.debug(f"📤 Кэш MISS: {key}")
        return None

    def set(self, key: str, value: Any, custom_ttl: Optional[int] = None) -> None:
        """Сохраняет значение в кэш"""
        ttl_to_use = custom_ttl if custom_ttl is not None else self.ttl

        self.cache[key] = {"value": value, "timestamp": time.time(), "ttl": ttl_to_use}

        # Проверяем лимиты
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        # Периодически сохраняем на диск
        if len(self.cache) % 10 == 0:
            self._save_to_disk()

        logger.debug(f"💾 Кэш SET: {key}")

    def delete(self, key: str) -> bool:
        """Удаляет значение из кэша"""
        if key in self.cache:
            del self.cache[key]
            self._save_to_disk()
            logger.debug(f"🗑️ Кэш DELETE: {key}")
            return True
        return False

    def clear(self) -> None:
        """Очищает весь кэш"""
        self.cache.clear()
        self._save_to_disk()
        logger.info("🧹 Кэш полностью очищен")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        current_time = time.time()
        valid_items = 0
        expired_items = 0

        for value in self.cache.values():
            if current_time - value.get("timestamp", 0) < value.get("ttl", self.ttl):
                valid_items += 1
            else:
                expired_items += 1

        return {
            "total_items": len(self.cache),
            "valid_items": valid_items,
            "expired_items": expired_items,
            "hit_rate": getattr(self, "_hit_count", 0)
            / max(getattr(self, "_request_count", 1), 1),
            "memory_usage": len(str(self.cache)),
        }


# Глобальный экземпляр кэша
cache = SimpleCache(max_size=500, ttl=1800)  # 30 минут TTL


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов функций

    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс для ключа кэша
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ кэша из аргументов функции
            cache_key = (
                f"{key_prefix}{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            )

            # Пытаемся получить из кэша
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def cache_user_data(user_id: int, data: Any, ttl: int = 3600):
    """Кэширует данные пользователя"""
    key = f"user:{user_id}:data"
    cache.set(key, data, ttl)


def get_cached_user_data(user_id: int) -> Optional[Any]:
    """Получает кэшированные данные пользователя"""
    key = f"user:{user_id}:data"
    return cache.get(key)


def cache_shelter_data(shelter_id: str, data: Any, ttl: int = 7200):
    """Кэширует данные убежища"""
    key = f"shelter:{shelter_id}"
    cache.set(key, data, ttl)


def get_cached_shelter_data(shelter_id: str) -> Optional[Any]:
    """Получает кэшированные данные убежища"""
    key = f"shelter:{shelter_id}"
    return cache.get(key)


def cache_incident_stats(stats: Dict[str, Any], ttl: int = 600):
    """Кэширует статистику инцидентов"""
    cache.set("incident_stats", stats, ttl)


def get_cached_incident_stats() -> Optional[Dict[str, Any]]:
    """Получает кэшированную статистику инцидентов"""
    return cache.get("incident_stats")


# Функция для очистки кэша по расписанию
def cleanup_cache():
    """Очищает истекшие элементы кэша"""
    cache._clean_expired()
    cache._save_to_disk()
    logger.debug("🧹 Плановое обслуживание кэша выполнено")
