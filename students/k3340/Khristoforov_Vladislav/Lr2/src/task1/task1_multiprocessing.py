import time
import argparse
import multiprocessing

def calculate_sum(args: tuple) -> int:
    """
    Вычисляет сумму в диапазоне.
    Принимает кортеж, так как метод pool.map передает единственный аргумент.
    """
    start, end = args
    total = 0
    for i in range(start, end + 1):
        total += i
    return total

def run_multiprocessing(target_number: int, num_tasks: int):
    """
    Многопроцессное выполнение задачи (модуль multiprocessing).
    """
    print(f"Считаем сумму от 1 до {target_number} (MULTIPROCESSING, {num_tasks} процессов)...")
    start_time = time.time()
    
    step = target_number // num_tasks
    tasks_args = []
    
    for i in range(num_tasks):
        start = i * step + 1
        end = (i + 1) * step if i != num_tasks - 1 else target_number
        tasks_args.append((start, end))
        
    with multiprocessing.Pool(processes=num_tasks) as pool:
        results = pool.map(calculate_sum, tasks_args)
            
    result = sum(results)
    elapsed = time.time() - start_time
    
    print(f"[Multiprocessing] Результат: {result}, Время: {elapsed:.4f} сек")
    return result, elapsed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Многопроцессное вычисление суммы")
    parser.add_argument("-n", "--number", type=int, default=10**8, help="Целевое число")
    parser.add_argument("-w", "--workers", type=int, default=8, help="Количество процессов")
    args = parser.parse_args()
    
    run_multiprocessing(args.number, args.workers)