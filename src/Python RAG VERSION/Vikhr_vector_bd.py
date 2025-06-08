"""
Описание модуля  
Этот модуль реализует метод генерации ответа на заданную тему,
используя локальную GGUF‑модель Vikhr‑Qwen‑2.5‑0.5B-instruct через Ollama.
Основные шаги: загрузка/обновление FAISS, поиск по схожести контекста,
и вызов модели для генерации.
"""

import os
from loguru import logger
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import torch

# Логирование
logger.add(
    "log/02_Simple_RAG_QWEN.log",
    format="{time} {level} {message}",
    level="DEBUG",
    rotation="100 KB",
    compression="zip"
)

def get_index_db():
    logger.debug('Начало get_index_db')
    model_id = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    embeddings = HuggingFaceEmbeddings(
        model_name=model_id,
        model_kwargs={'device': device}
    )

    db_folder = 'db_qwen'
    os.makedirs(db_folder, exist_ok=True)
    idx_path = os.path.join(db_folder, 'index.faiss')

    if os.path.exists(idx_path):
        logger.debug('Загрузка существующей FAISS базы')
        db = FAISS.load_local(db_folder, embeddings, allow_dangerous_deserialization=True)
    else:
        logger.debug('Создание новой FAISS базы из PDF')
        from langchain_community.document_loaders import PyPDFLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        # Сбор всех PDF
        docs = []
        for root, _, files in os.walk('pdf'):
            for fn in files:
                if fn.lower().endswith('.pdf'):
                    loader = PyPDFLoader(os.path.join(root, fn))
                    docs.extend(loader.load())

        # Чанки по 500 токенов (немного больше, чем раньше)
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        # Создание и сохранение
        db = FAISS.from_documents(chunks, embeddings)
        db.save_local(db_folder)

    return db

def get_relevant_context(question: str, db, top_k: int = 5) -> str:
    logger.debug(f'Поиск {top_k} самых релевантных чанков')
    docs = db.similarity_search(question, k=top_k)
    pieces = []
    for i, d in enumerate(docs):
        meta = d.metadata or {}
        pieces.append(f"#### Chunk {i+1} ####\n{d.page_content}")
    context = "\n\n".join(pieces)
    logger.debug('Контекст сформирован')
    return context

def get_model_response(question: str, context: str) -> str:
    logger.debug('Генерация ответа от модели')
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage

    # Новая модель и оптимизированные параметры
    llm = ChatOllama(
        model="hf.co/Vikhrmodels/Vikhr-Qwen-2.5-0.5B-instruct-GGUF:q4_K_M",
        temperature=0.0,
        # Поскольку у вас нет крупной GPU, порежем потоки под CPU
        num_gpu=0,
        num_thread=4,           # не более 15 секунд
        stream=False          # отключим стриминг, чтобы гарантировать уклад в таймаут
    )

    prompt = (
        "Ты являешься помощником для выполнения заданий по ответам на вопросы.Вот контекст, который нужно использовать для ответа на вопрос:\n\n"
        f"{context}\n\n"
        f"Внимательно подумайте над приведенным контекстом.Теперь просмотрите вопрос пользователя: {question}\n"
        "Дай ответ на этот вопрос, используя только вышеуказанный контекст."
         "Используйте не более трех предложений и будьте лаконичны в ответе.Ответ:")

    resp = llm.invoke([HumanMessage(content=prompt)])
    logger.debug(f"Ответ модели: {resp.content}")
    return resp.content

if __name__ == "__main__":
    db = get_index_db()
    question = "Порядок действий при выявлении НП?"
    # Т.е. передаём в RAG не более 3 чанков, чтобы уложиться в 15 секунд
    ctx = get_relevant_context(question, db, top_k=3)
    answer = get_model_response(question, ctx)
    print("Ответ:", answer)
