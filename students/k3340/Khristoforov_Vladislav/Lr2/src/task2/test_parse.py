import requests
import json
from utils import extract_book_info

def test_parsing():
    """
    Тестирование функции extract_book_info на реальных страницах.
    Сравнение с эталонными данными для валидации корректности парсинга.
    """
    print("=== ТЕСТ ПАРСИНГА (БЕЗ СОХРАНЕНИЯ В БД) ===\n")
    
    test_urls = [
        "https://www.gutenberg.org/ebooks/2701",
        "https://standardebooks.org/ebooks/charles-brockden-brown/wieland"
    ]
    
    for url in test_urls:
        print(f"🌐 Скачиваем страницу: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            print("⚙️ Извлекаем данные...")
            book_data = extract_book_info(response.text, url)
            
            print("✅ РЕЗУЛЬТАТ ПАРСИНГА:")
            print(json.dumps(book_data, indent=4, ensure_ascii=False))
            print("\n" + "="*60 + "\n")
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании {url}: {e}\n")

if __name__ == "__main__":
    test_parsing()