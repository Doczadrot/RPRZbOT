
import os #Эта библиотека нужна для работы с файлами и папками на компьютере
import requests #Эта библиотека нужна для отправки запросов на сайт
import json #Эта библиотека нужна для работы с JSON-файлами


DEEPSEEK_API_KEY = "sk-2114a6d342c446479d351c46e412bbd0"
DEEPSEEK_API_URL = "https://api.deepseek.com/models"
DEEPSEEK_MODEL_NAME = 'deepseek-chat'
EMBEDDING_MODEL_NAME = 'ВАША_МОДЕЛЬ_ЭМБЕДДИНГОВ'
DOCUMENTS_DIR = './documents'
# Путь к папке, где будет сохраняться индекс базы знаний (векторы документов). 📊
# Это чтобы бот "помнил" обработанные документы между запусками.
INDEX_PERSIST_DIR = './vector_index'
ADMIN_USER_IDS = [ 898852116, ]


os.makedirs(DOCUMENTS_DIR, exist_ok=exist_ok) # Создание папки для документов.
os.makedirs(INDEX_PERSIST_DIR, exist_ok=exist_ok) # Создание папки для индекса базы знаний.