
import google.generativeai as genai
import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini():
    load_dotenv() # Загружаем переменные окружения из .env файла
    # Убедитесь, что ваш API-ключ установлен как переменная окружения
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if not GOOGLE_API_KEY:
        print("Ошибка: Переменная окружения GOOGLE_API_KEY не установлена.")
        print("Пожалуйста, установите ее перед запуском скрипта.")
        return

    genai.configure(api_key=GOOGLE_API_KEY)

    # Инициализируем модель Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')

    try:
        response = model.generate_content("Напиши короткий стих про кота.")
        print("\n--- Тест Gemini API ---")
        print(response.text)
        print("--- Конец теста Gemini API ---\n")
    except Exception as e:
        print(f"Произошла ошибка при вызове Gemini API: {e}")

# Вызываем функцию для выполнения теста
if __name__ == "__main__":
    test_gemini()
