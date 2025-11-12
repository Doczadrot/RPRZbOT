FROM python:3.11-slim

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs

# Запускаем бота в webhook режиме (serverless)
CMD ["python", "bot/main_webhook.py"]

