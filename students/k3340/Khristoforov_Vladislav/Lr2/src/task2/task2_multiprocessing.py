import time
import multiprocessing
import requests
from requests.exceptions import RequestException

from utils import load_urls, divide_into_chunks, extract_book_info
from db import save_to_db_sync

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

def parse_and_save(url: str):
    """
    Функция загрузки и обработки. 
    Исполняется в изолированном адресном пространстве дочернего процесса ОС.
    """
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            book_data = extract_book_info(response.text, url)
            if book_data["title"] == "Неизвестное название":
                return
                
            save_to_db_sync(book_data)
            print(f"[Process-{multiprocessing.current_process().name}] Сохранено: '{book_data['title']}'")
            return 
        except RequestException:
            time.sleep(1)
        except Exception as e:
            print(f"[Process-{multiprocessing.current_process().name}] Ошибка: {e}")
            return

def process_worker(urls_chunk: list[str]):
    """Точка входа для изолированного процесса."""
    for url in urls_chunk:
        parse_and_save(url)

def run_multiprocessing() -> float:
    """Оркестрация многопроцессного выполнения."""
    print("=== ЗАПУСК ПРОЦЕССОВ (MULTIPROCESSING) ===")
    start_time = time.time()
    
    urls = load_urls()
    num_processes = 8
    chunks = divide_into_chunks(urls, num_processes)
    processes = []
    
    # Создание изолированных процессов ОС. 
    # В отличие от потоков, процессы требуют больше ресурсов на инициализацию.
    for i, chunk in enumerate(chunks):
        p = multiprocessing.Process(target=process_worker, args=(chunk,), name=str(i+1))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    elapsed = time.time() - start_time
    print(f"=== [MULTIPROCESSING] Завершено за {elapsed:.4f} сек ===\n")
    return elapsed

if __name__ == "__main__":
    from db import clean_db_sync
    clean_db_sync()
    run_multiprocessing()