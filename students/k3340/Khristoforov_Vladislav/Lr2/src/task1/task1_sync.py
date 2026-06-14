import time
import argparse

def calculate_sum(start: int, end: int) -> int:
    """
    Вычисляет сумму чисел в заданном диапазоне.
    Имитирует тяжелую CPU-bound нагрузку (математические операции).
    """
    total = 0
    for i in range(start, end + 1):
        total += i
    return total

def run_sync(target_number: int):
    """
    Синхронное (последовательное) выполнение задачи в основном потоке.
    Служит эталоном (baseline) для оценки ускорения параллельных подходов.
    """
    print(f"Считаем сумму от 1 до {target_number} СИНХРОННО...")
    start_time = time.time()
    
    result = calculate_sum(1, target_number)
    
    elapsed = time.time() - start_time
    print(f"[Sync] Результат: {result}, Время: {elapsed:.4f} сек")
    return result, elapsed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Синхронное вычисление суммы")
    parser.add_argument("-n", "--number", type=int, default=10**8, help="Целевое число")
    args = parser.parse_args()
    
    run_sync(args.number)