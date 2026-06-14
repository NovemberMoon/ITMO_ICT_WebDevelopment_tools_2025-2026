import argparse

from task1_sync import run_sync
from task1_threading import run_threading
from task1_multiprocessing import run_multiprocessing
from task1_async import run_asyncio

def main():
    """
    Оркестратор бенчмарка (CPU-bound).
    """
    parser = argparse.ArgumentParser(description="Бенчмарк подходов (Задача 1)")
    parser.add_argument("-n", "--number", type=int, default=10**8, help="Число для вычисления")
    parser.add_argument("-w", "--workers", type=int, default=8, help="Количество воркеров")
    parser.add_argument("--include-sync", action="store_true", help="Включить синхронный запуск")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"ТЕСТИРОВАНИЕ CPU-BOUND ЗАДАЧИ (N = {args.number}, Workers = {args.workers})")
    print(f"{'='*60}\n")

    results_time = {}
    results_math = {}

    if args.include_sync:
        results_math["Sync"], results_time["Sync"] = run_sync(args.number)
    else:
        print("[Sync] Пропущен (добавьте флаг --include-sync для запуска)")
    print("-" * 40)
    
    results_math["Threading"], results_time["Threading"] = run_threading(args.number, args.workers)
    print("-" * 40)
    
    results_math["Multiprocessing"], results_time["Multiprocessing"] = run_multiprocessing(args.number, args.workers)
    print("-" * 40)
    
    results_math["Asyncio"], results_time["Asyncio"] = run_asyncio(args.number, args.workers)
    print("-" * 40)

    print("\n" + "="*40)
    print(f"{'ПОДХОД':<20} | {'ВРЕМЯ (сек)':<15}")
    print("="*40)
    for approach, time_taken in sorted(results_time.items(), key=lambda item: item[1]):
        print(f"{approach:<20} | {time_taken:.4f} сек")
    print("="*40)

if __name__ == "__main__":
    main()