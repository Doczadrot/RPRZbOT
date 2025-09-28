# Телеграм-бот РПРЗ

MVP телеграм-бота для системы безопасности РПРЗ.

## Установка и запуск

1. Создайте виртуальное окружение:
```bash
python -m venv .venv
```

2. Активируйте окружение:
```bash
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Скопируйте env.example в .env и заполните переменные:
```bash
cp env.example .env
```

5. Запустите бота:
```bash
python bot/main.py
```

## Структура проекта

- `/bot` - основной код бота
- `/assets` - медиафайлы (PDF, изображения)
- `/configs` - конфигурационные файлы с заглушками
- `/logs` - логи приложения
- `/docs` - документация
