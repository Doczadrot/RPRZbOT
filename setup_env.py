#!/usr/bin/env python3
"""
Скрипт для настройки .env файла с токеном бота
"""
import os

def create_env_file():
    """Создать .env файл с настройками"""
    
    # Проверяем, существует ли уже .env файл
    if os.path.exists('.env'):
        print("⚠️ Файл .env уже существует!")
        response = input("Перезаписать? (y/N): ").lower()
        if response != 'y':
            print("❌ Отменено")
            return
    
    # Содержимое .env файла
    env_content = """BOT_TOKEN=YOUR_TOKEN
ADMIN_CHAT_ID=ADMIN_ID_PLACEHOLDER
EMAIL_USER=example@domain.com
EMAIL_PASS=password123
"""
    
    try:
        # Создаем .env файл
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Файл .env создан успешно!")
        print("\n📋 Следующие шаги:")
        print("1. Отредактируйте ADMIN_CHAT_ID в файле .env")
        print("2. Запустите бота: python bot/main_refactored.py")
        print("3. Протестируйте бота в Telegram")
        
    except Exception as e:
        print(f"❌ Ошибка создания .env файла: {e}")

def check_requirements():
    """Проверить установленные зависимости"""
    try:
        import telegram
        import dotenv
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False

def main():
    """Главная функция"""
    print("🤖 Настройка телеграм-бота РПРЗ")
    print("=" * 40)
    
    # Проверяем зависимости
    if not check_requirements():
        return
    
    # Создаем .env файл
    create_env_file()
    
    print("\n🎉 Настройка завершена!")
    print("Теперь вы можете запустить бота!")

if __name__ == "__main__":
    main()
