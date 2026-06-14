from task2_threading import run_threading
from task2_multiprocessing import run_multiprocessing
from task2_async import run_asyncio
from db import clean_db_sync

def main():
    """
    Оркестратор I/O-bound бенчмарка.
    """
    print("Начинаем тестирование подходов парсинга (Задача 2)\n" + "="*60)
    
    results = {}
    
    clean_db_sync()
    results["Threading"] = run_threading()
    
    clean_db_sync()
    results["Multiprocessing"] = run_multiprocessing()
    
    clean_db_sync()
    results["Asyncio"] = run_asyncio()
    
    print("\n" + "="*40)
    print(f"{'ПОДХОД':<20} | {'ВРЕМЯ (сек)':<15}")
    print("="*40)
    
    for approach, time_taken in sorted(results.items(), key=lambda item: item[1]):
        print(f"{approach:<20} | {time_taken:.4f} сек")
    print("="*40)

if __name__ == "__main__":
    main()