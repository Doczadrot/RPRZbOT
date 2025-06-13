"""
Описание модуля  
Этот модуль реализует метод генерации ответа на заданную тему,
используя локальную GGUF‑модель "qwen2.5vl:3b" через Ollama.
Основные шаги: загрузка/обновление FAISS, поиск по схожести контекста,
и вызов модели для генерации.
"""

import os
from loguru import logger
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import torch # Импортируем библиотеку PyTorch для работы с тензорами и GPU/CPU

# Логирование: настройка записи событий программы в файл
logger.add(
    "log/02_Simple_RAG_QWEN.log", # Путь к файлу логов
    format="{time} {level} {message}", # Формат записи: время, уровень, сообщение
    level="DEBUG", # Уровень логирования: DEBUG означает запись всех сообщений
    rotation="100 KB", # Файл логов будет архивироваться каждые 100 КБ
    compression="zip" # Архивация старых логов в ZIP-архив
)

def get_index_db():
    logger.debug('Начало get_index_db') # Запись в лог о начале работы функции
    # Идентификатор модели для создания эмбеддингов (векторных представлений текста)
    model_id = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2' #модель  для имбедингов
    # Определение устройства для вычислений: 'cuda' (GPU) если доступно, иначе 'cpu'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # Инициализация модели для создания эмбеддингов
    embeddings = HuggingFaceEmbeddings(
        model_name=model_id,
        model_kwargs={'device': device} # Передача устройства для вычислений
    )

    db_folder = 'db_qwen' # Папка для хранения базы данных FAISS
    os.makedirs(db_folder, exist_ok=True) # Создание папки, если она не существует
    idx_path = os.path.join(db_folder, 'index.faiss') # Полный путь к файлу индекса FAISS

    # Проверка наличия существующей базы данных FAISS
    if os.path.exists(idx_path):
        logger.debug('Загрузка существующей FAISS базы') # Запись в лог
        # Загрузка существующей базы данных FAISS
        db = FAISS.load_local(db_folder, embeddings, allow_dangerous_deserialization=True)
    else:
        logger.debug('Создание новой FAISS базы из PDF') # Запись в лог
        # Импорт необходимых классов для загрузки и обработки PDF
        from langchain_community.document_loaders import PyPDFLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        # Сбор всех PDF-документов из папки 'pdf'
        docs = []
        for root, _, files in os.walk('pdf'):
            for fn in files:
                if fn.lower().endswith('.pdf'):
                    loader = PyPDFLoader(os.path.join(root, fn)) # Загрузчик PDF
                    docs.extend(loader.load()) # Загрузка документов

        # Разбиение документов на чанки (куски текста) для обработки
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100) # Размер чанка и перекрытие
        chunks = splitter.split_documents(docs) # Разбиение документов

        # Создание новой базы данных FAISS из чанков и сохранение ее локально
        db = FAISS.from_documents(chunks, embeddings)
        db.save_local(db_folder)

    return db # Возвращаем готовую базу данных

def get_relevant_context(question: str, db, top_k: int = 5) -> str:
    logger.debug(f'Поиск {top_k} самых релевантных чанков') # Запись в лог
    # Поиск наиболее релевантных документов (чанков) по вопросу
    docs = db.similarity_search(question, k=top_k)
    pieces = [] # Список для хранения отформатированных чанков
    for i, d in enumerate(docs):
        meta = d.metadata or {} # Метаданные документа (если есть)
        pieces.append(f"#### Chunk {i+1} ####\n{d.page_content}") # Форматирование чанка
    context = "\n\n".join(pieces) # Объединение чанков в единый контекст
    logger.debug('Контекст сформирован') # Запись в лог
    return context # Возвращаем сформированный контекст

def get_model_response(question: str, context: str) -> str:
    logger.debug('Генерация ответа от модели') # Запись в лог
    # Импорт необходимых классов для работы с моделью Ollama
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage

    # Инициализация модели ChatOllama с заданными параметрами
    llm = ChatOllama(
        model="qwen2.5vl:3b", # Имя модели
        temperature=0.0, # Температура генерации (0.0 делает ответы более детерминированными)
        num_gpu=1, # Разделим работу на видюху
        num_thread=4, # Количество потоков CPU для обработки (оптимизация производительности)
        stream=False # Отключение потоковой передачи ответа (получаем ответ целиком)
    )

    # Формирование промпта (запроса) для модели
    prompt = (
        "Ты являешься помощником для выполнения заданий по ответам на вопросы.Вот контекст, который нужно использовать для ответа на вопрос:\n\n" # Инструкция для модели
        f"{context}\n\n" # Вставляем найденный контекст
        f"Внимательно подумайте над приведенным контекстом.Теперь просмотрите вопрос пользователя: {question}\n" # Просим модель внимательно изучить контекст и вопрос
        "Дай ответ на этот вопрос, используя только вышеуказанный контекст." # Ограничение: отвечать только на основе контекста
         "Используйте не более трех предложений и будьте лаконичны в ответе.Ответ:") # Дополнительные инструкции по формату ответа

    resp = llm.invoke([HumanMessage(content=prompt)]) # Отправка промпта модели и получение ответа
    logger.debug(f"Ответ модели: {resp.content}") # Запись ответа модели в лог
    return resp.content # Возвращаем сгенерированный ответ

if __name__ == "__main__": # Этот блок выполняется только при прямом запуске файла
    db = get_index_db() # Получаем или создаем базу данных FAISS
    question = "Какой порядок оформления акта о браке?" # Пример вопроса
    # Получаем релевантный контекст из базы данных (3 самых релевантных чанка)
    ctx = get_relevant_context(question, db, top_k=3)
    answer = get_model_response(question, ctx) # Получаем ответ от модели
    print("Ответ:", answer) # Выводим ответ на консоль
