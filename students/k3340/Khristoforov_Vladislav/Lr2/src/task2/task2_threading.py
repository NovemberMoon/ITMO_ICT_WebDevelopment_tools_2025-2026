import time
import threading
import requests
from requests.exceptions import RequestException

from utils import load_urls, divide_into_chunks, extract_book_info
from db import save_to_db_sync

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

def parse_and_save(url: str):
    """
    Синхронная функция загрузки и обработки веб-страницы.
    Содержит механизм Retry для отказоустойчивости при сетевых задержках или обрывах связи.
    """
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            book_data = extract_book_info(response.text, url)
            if book_data["title"] == "Неизвестное название":
                return
                
            save_to_db_sync(book_data)
            print(f"[Thread-{threading.current_thread().name}] Сохранено: '{book_data['title']}'")
            return 
        except RequestException:
            # При сетевом сбое (таймаут) поток засыпает перед повторной попыткой.
            # Благодаря GIL в этот момент управление передается другому потоку.
            time.sleep(1) 
        except Exception as e:
            print(f"[Thread-{threading.current_thread().name}] Ошибка: {e}")
            return

def thread_worker(urls_chunk: list[str]):
    """Точка входа для потока. Последовательно обрабатывает выделенный сегмент (чанк) ссылок."""
    for url in urls_chunk:
        parse_and_save(url)

def run_threading() -> float:
    """Оркестрация многопоточного выполнения."""
    print("=== ЗАПУСК ПОТОКОВ (THREADING) ===")
    start_time = time.time()
    
    urls = load_urls()
    num_threads = 8
    chunks = divide_into_chunks(urls, num_threads)
    threads = []
    
    # Инициализация и запуск потоков в адресном пространстве одного процесса ОС
    for i, chunk in enumerate(chunks):
        t = threading.Thread(target=thread_worker, args=(chunk,), name=str(i+1))
        threads.append(t)
        t.start()
        
    # Блокировка основного потока исполнения до завершения работы всех дочерних
    for t in threads:
        t.join()
        
    elapsed = time.time() - start_time
    print(f"=== [THREADING] Завершено за {elapsed:.4f} сек ===\n")
    return elapsed

if __name__ == "__main__":
    from db import clean_db_sync
    clean_db_sync()
    run_threading()