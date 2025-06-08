"""
Этот модуль реализует функцию, которая запрашивает локальную языковую модель
Vikhr-Qwen-2.5-0.5B-instruct-GGUF через Ollama для получения ответов на вопросы.
Используется библиотека `loguru` для логирования процесса.
Основное предназначение — генерация лаконичных ответов (<=3 предложения) на русском языке.
"""

from loguru import logger

# Настройка логирования
logger.add(
    "log/Simple_Request_QWEN.log",
    format="{time} {level} {message}",
    level="DEBUG",
    rotation="100 KB",
    compression="zip"
)


def get_model_response(topic: str) -> str:
    """
    Функция для получения ответа от локальной модели Vikhr-Qwen-2.5-0.5B-instruct-GGUF.

    Параметры:
    - topic (str): Вопрос или тема, на которую нужно получить ответ.

    Возвращает:
    - str: Сгенерированный языковой моделью ответ.
    """

    logger.debug('Начало get_model_response')

    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage

    # Настройка LLM c оптимизированными параметрами
    llm = ChatOllama(
        model="hf.co/Vikhrmodels/Vikhr-Qwen-2.5-0.5B-instruct-GGUF:q4_K_M",
        temperature=0.0,
        num_gpu=0,
        num_thread=4,
        timeout=15,
        stream=False
    )

    # Формирование промпта
    prompt = (
        "Ты — ассистент по вопросам из документа. \
"        "Внимательно изучи вопрос:\n{question}\n"        "Ответь на русском языке, не более трех предложений.\n"    ).format(question=topic)

    logger.debug(f"Отправка промпта: {topic}")

    # Вызов модели
    generation = llm.invoke([HumanMessage(content=prompt)])
    response = generation.content

    logger.debug(f"Ответ модели: {response}")
    return response


if __name__ == "__main__":
    question = 'Объясни понятие RAG (Retrieval-Augmented Generation).'
    answer = get_model_response(question)
    print("Ответ:", answer)
