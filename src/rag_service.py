# rag_service.py
# Модуль, содержащий логику Нейропомощника на основе RAG (Retrieval-Augmented Generation).
# Использует HuggingFace Embeddings и Ollama LLM.

import os
import re
import json # Пока не используется, но может пригодиться

from loguru import logger # Для удобного логирования

# Импорты Langchain и других библиотек
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings # ИЗМЕНЕНО: Обновленный импорт
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama # Для работы с Ollama LLM
from langchain_core.messages import HumanMessage # Для формирования сообщения пользователя в Langchain

# --- Настройка логирования для этого модуля ---
# Логи будут писаться в файл rag_service.log
logger.add("log/rag_service.log", format="{time} {level} {message}", level="DEBUG", rotation="1 MB", compression="zip")
logger.info("Модуль rag_service загружен.") # Лог при загрузке модуля

# --- Константы и Настройки ---
# Папка, где лежат PDF документы для базы знаний (относительно места запуска скрипта)
# Убедитесь, что такая папка есть и в ней лежат ваши PDF файлы.
PDF_DOCUMENTS_DIR = '../pdf' # ✅ Имя папки с PDF документами
# Папка для хранения индекса FAISS
FAISS_INDEX_DIR = 'db/db_01' # ✅ Папка для сохранения/загрузки индекса FAISS

# Параметры для модели эмбеддингов HuggingFace
EMBEDDING_MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
EMBEDDING_MODEL_KWARGS = {'device': 'cpu'} # Используем CPU

# Параметры для модели Ollama LLM
OLLAMA_MODEL_NAME = "llama3:8b" # ✅ Проверьте доступность этой модели в Ollama

# Количество наиболее релевантных чанков, которые мы будем извлекать из базы для ответа
NUMBER_RELEVANT_CHUNKS = 3 # ✅ Можно настроить


# --- Функции RAG ---

# ШАГ 6 (упрощенный вариант из вашего кода): Получение или создание векторной базы данных
def get_or_create_vector_db():
    """
    Получает существующую векторную базу FAISS с диска или создает новую
    путем чтения PDF-документов, если база отсутствует.
    База данных сохраняется на диск после создания/обновления.
    Возвращает объект векторной базы FAISS.
    """
    logger.debug('Вызвана функция get_or_create_vector_db')

    # Инициализация модели эмбеддингов
    logger.debug(f'Инициализация модели эмбеддингов: {EMBEDDING_MODEL_ID}')
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_ID,
            model_kwargs=EMBEDDING_MODEL_KWARGS
        )
        logger.debug('Модель эмбеддингов успешно инициализирована.')
    except Exception as e:
        logger.error(f'Ошибка инициализации модели эмбеддингов {EMBEDDING_MODEL_ID}: {e}')
        # В реальном приложении здесь, возможно, стоит остановить работу или выдать критическое сообщение
        return None # Возвращаем None, если модель эмбеддингов не инициализирована


    # --- Попытка загрузки существующей базы ---
    index_file_path = os.path.join(FAISS_INDEX_DIR, "index.faiss")
    logger.debug(f'Проверка наличия файла индекса: {index_file_path}')

    if os.path.exists(index_file_path):
        logger.info('Найдена существующая векторная база данных. Загрузка...')
        try:
            # Загрузка существующей базы
            db = FAISS.load_local(FAISS_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
            logger.info('Векторная база данных успешно загружена.')
            return db # ✅ Возвращаем загруженную базу
        except Exception as e:
            logger.error(f'Ошибка при загрузке векторной базы данных: {e}')
            logger.warning('Не удалось загрузить существующую базу. Попробуем создать новую.')
            # Продолжаем выполнение, чтобы создать новую базу, если загрузка не удалась

    else:
        logger.info('Существующая векторная база данных не найдена. Создание новой...')
        # --- Создание новой базы, если она отсутствует ---
        # Проверка папки с документами
        if not os.path.exists(PDF_DOCUMENTS_DIR):
             logger.error(f'Папка с PDF документами не найдена: {PDF_DOCUMENTS_DIR}')
             logger.error('Невозможно создать базу знаний без документов.')
             return None # Возвращаем None, если нет папки с документами


        # Загрузка документов
        logger.debug(f'Загрузка документов из папки: {PDF_DOCUMENTS_DIR}')
        documents = []
        try:
            # Использование os.walk для обхода подпапок, если необходимо
            for root, dirs, files in os.walk(PDF_DOCUMENTS_DIR):
                for file in files:
                    # ✅ Убедитесь, что обрабатываются только нужные файлы (например, PDF)
                    if file.lower().endswith(".pdf"):
                        file_path = os.path.join(root, file)
                        logger.debug(f'Загрузка файла: {file_path}')
                        try:
                             loader = PyPDFLoader(file_path)
                             documents.extend(loader.load())
                             logger.debug(f'Успешно загружен файл: {file_path}')
                        except Exception as e:
                            logger.error(f'Ошибка загрузки PDF файла {file_path}: {e}')
                            # Продолжаем загружать другие файлы даже при ошибке с одним

            logger.info(f'Всего загружено страниц из PDF документов: {len(documents)}')

            if not documents:
                 logger.warning('Не найдено подходящих PDF документов для создания базы.')
                 return None # Возвращаем None, если нет загруженных документов

        except Exception as e:
            logger.error(f'Ошибка при обходе папки документов {PDF_DOCUMENTS_DIR} или загрузке: {e}')
            return None # Возвращаем None при ошибке загрузки документов


        # Разделение документов на чанки
        logger.debug('Разделение загруженных документов на чанки...')
        try:
            # Настройки RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=0) # Убрал комментарии про символы/токены для простоты
            source_chunks = text_splitter.split_documents(documents)
            logger.info(f'Всего получено чанков после разделения: {len(source_chunks)}')

            if not source_chunks:
                 logger.warning('Документы не удалось разделить на чанки.')
                 return None # Возвращаем None, если нет чанков

        except Exception as e:
             logger.error(f'Ошибка при разделении документов на чанки: {e}')
             return None # Возвращаем None при ошибке разделения на чанки


        # Создание векторной базы данных из чанков и эмбеддингов
        logger.debug('Создание векторной базы данных из чанков и эмбеддингов...')
        try:
            db = FAISS.from_documents(source_chunks, embeddings)
            logger.info('Векторная база данных успешно создана.')
        except Exception as e:
            logger.error(f'Ошибка при создании векторной базы данных FAISS: {e}')
            return None # Возвращаем None при ошибке создания базы


        # Сохранение созданной базы данных на диск
        logger.debug(f'Сохранение векторной базы данных в файл: {FAISS_INDEX_DIR}')
        try:
            # Убедимся, что папка для сохранения существует
            os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
            db.save_local(FAISS_INDEX_DIR)
            logger.info('Векторная база данных успешно сохранена.')
            return db # ✅ Возвращаем созданную и сохраненную базу
        except Exception as e:
            logger.error(f'Ошибка при сохранении векторной базы данных: {e}')
            # База данных создана в памяти (объект db), но не сохранена на диск.
            # Можно решить, что делать в этом случае: вернуть db (база будет только в памяти до остановки бота)
            # или вернуть None. Давайте пока вернем None, чтобы явно показать проблему сохранения.
            return None


# ШАГ 7: Поиск релевантных документов по запросу
def retrieve_relevant_chunks(topic: str, db: FAISS, k: int = NUMBER_RELEVANT_CHUNKS) -> str:
    """
    Выполняет поиск по векторной базе данных для нахождения наиболее релевантных
    кусочков текста (чанков) по заданному запросу (topic).
    Возвращает текст извлеченных чанков, объединенных в одну строку.
    """
    logger.debug(f'Вызвана функция retrieve_relevant_chunks. Запрос: "{topic}", количество чанков: {k}')
    if db is None:
        logger.error('Векторная база данных не инициализирована или не загружена. Невозможно выполнить поиск.')
        return "Ошибка: База знаний недоступна."

    try:
        # Similarity search - поиск наиболее похожих документов по вектору запроса
        # db.similarity_search_with_score может дать оценку схожести, но пока используем простую search
        docs = db.similarity_search(topic, k=k) # Выполняем поиск, получаем список Document объектов
        logger.debug(f'Найдено {len(docs)} релевантных чанков.')

        if not docs:
            logger.warning('Поиск не нашел релевантных чанков.')
            return "Не найдено релевантной информации по вашему запросу."


        # Форматирование извлеченных данных для передачи в LLM
        # Добавляем метаданные (например, источник) и содержимое чанка
        # Убрал регулярное выражение re.sub из вашего примера, оно здесь не нужно
        message_content_parts = []
        for i, doc in enumerate(docs):
            metadata_str = ', '.join([f'{key}: {value}' for key, value in doc.metadata.items()]) # Форматируем метаданные
            message_content_parts.append(f'\n#### Релевантный чанк {i+1} ####\nМетаданные: {metadata_str}\nСодержимое:\n{doc.page_content}\n')

        message_content = '\n---\n'.join(message_content_parts) # Объединяем все части с разделителем

        #logger.debug(f'Сформированный контекст для LLM:\n{message_content}') # Этот лог может быть очень длинным

        return message_content # ✅ Возвращаем собранный текст релевантных чанков

    except Exception as e:
        logger.error(f'Ошибка при поиске релевантных чанков: {e}')
        return f"Ошибка при поиске информации: {e}"


# ШАГ 8: Генерация ответа с использованием LLM
def generate_llm_response(topic: str, context: str):
    """
    Генерирует ответ на вопрос (topic) с использованием LLM, основываясь на предоставленном контексте.
    """
    logger.debug(f'Вызвана функция generate_llm_response. Вопрос: "{topic}"')
    # logger.debug(f'Контекст для LLM:\n{context}') # Лог контекста может быть длинным

    # Инициализация модели Ollama LLM (выполняется при каждом вызове, можно вынести выше, если нужно)
    # ✅ В вашем примере LLM инициализировался здесь, сохраним эту логику.
    logger.debug(f'Инициализация LLM: {OLLAMA_MODEL_NAME}')
    try:
        llm = ChatOllama(model=OLLAMA_MODEL_NAME, temperature=0)
        logger.debug('LLM успешно инициализирован.')
    except Exception as e:
        logger.error(f'Ошибка инициализации LLM {OLLAMA_MODEL_NAME}: {e}')
        return "Ошибка: Модель для генерации ответа недоступна."


    # Формирование промпта для LLM
    # ✅ Адаптированный промпт для RAG, с placeholders для контекста и вопроса
    rag_prompt_template = """Ты являешься помощником для выполнения заданий по ответам на вопросы.
Используй только предоставленный контекст для ответа на вопрос.
Если ответ не содержится в контексте, так и скажи, не пытайся придумать информацию.

Контекст:
{context}

Вопрос пользователя:
{question}

Ответ:"""

    # Форматирование промпта с учетом текущего контекста и вопроса
    rag_prompt_formatted = rag_prompt_template.format(context=context, question=topic)
    logger.debug('Сформирован финальный промпт для LLM.')

    # Вызов LLM для генерации ответа
    try:
        # Langchain LLM принимает список сообщений. Здесь у нас одно сообщение пользователя с промптом.
        generation = llm.invoke([HumanMessage(content=rag_prompt_formatted)])
        model_response = generation.content
        logger.info('LLM успешно сгенерировал ответ.')
        logger.debug(f'Сгенерированный ответ:\n{model_response}')

        return model_response # ✅ Возвращаем сгенерированный ответ

    except Exception as e:
        logger.error(f'Ошибка при генерации ответа LLM: {e}')
        return f"Ошибка при генерации ответа: {e}"


# --- Главная функция для RAG пайплайна (может вызываться из бота) ---
def process_user_query_with_rag(user_query: str, vector_db: FAISS | None) -> str:
    """
    Обрабатывает запрос пользователя, используя RAG пайплайн:
    1. Ищет релевантные чанки в векторной базе.
    2. Генерирует ответ с помощью LLM на основе запроса и релевантных чанков.
    Принимает запрос пользователя и объект векторной базы данных.
    Возвращает сгенерированный ответ LLM или сообщение об ошибке.
    """
    logger.info(f"Получен запрос пользователя для RAG обработки: \"{user_query}\"")

    if vector_db is None:
        logger.error("Векторная база данных недоступна для обработки запроса.")
        return "Ошибка: База знаний Нейропомощника недоступна."

    # ШАГ 7: Извлечение релевантных чанков
    context_from_db = retrieve_relevant_chunks(user_query, vector_db, NUMBER_RELEVANT_CHUNKS)

    # Проверяем, были ли найдены релевантные чанки или произошла ошибка поиска
    if context_from_db.startswith("Ошибка:") or context_from_db.startswith("Не найдено релевантной информации"):
         # Если поиск вернул ошибку или "не найдено", возвращаем это сообщение пользователю
         logger.warning(f"Поиск релевантных чанков завершился с результатом: {context_from_db}")
         # Можно либо вернуть это сообщение напрямую, либо все равно отправить в LLM
         # Давайте пока вернем напрямую, чтобы LLM не тратил время, если контекст пуст.
         #return context_from_db # Возвращаем сообщение об ошибке/отсутствии релевантных чанков

         # ✅ Альтернативно: отправить в LLM пустой или минимальный контекст и запрос, чтобы LLM сказал "не могу ответить"
         logger.debug("Релевантные чанки не найдены. Формируем минимальный контекст для LLM.")
         context_for_llm = f"Релевантная информация не найдена в базе знаний.\nВопрос пользователя: {user_query}"
         # или можно передать пустой контекст: context_for_llm = ""
         # В данном случае, если контекст пуст, LLM может сам сказать, что не может ответить по базе.

    else:
         logger.debug("Релевантные чанки успешно найдены и сформирован контекст.")
         context_for_llm = context_from_db # Используем найденный контекст


    # ШАГ 8: Генерация ответа LLM
    # Генерируем ответ, даже если релевантных чанков не было (LLM сам скажет, что не может ответить)
    final_answer = generate_llm_response(user_query, context_for_llm)

    # Проверяем, произошла ли ошибка при генерации ответа
    if final_answer.startswith("Ошибка:"):
        logger.error("Произошла ошибка при генерации ответа LLM.")
        return final_answer # Возвращаем сообщение об ошибке LLM
    else:
        logger.info("RAG пайплайн успешно завершен. Ответ сгенерирован.")
        return final_answer # ✅ Возвращаем финальный ответ пользователю

# --- (Блок if __name__ == "__main__": удален, так как теперь это модуль) ---