import time
import argparse
import threading

def calculate_sum(start: int, end: int, results_list: list, index: int):
    """
    Вычисляет сумму в диапазоне.
    Использует общую память процесса для записи результата
    по заданному индексу, так как потоки работают в одном адресном пространстве.
    """
    total = 0
    for i in range(start, end + 1):
        total += i
    results_list[index] = total

def run_threading(target_number: int, num_tasks: int):
    """
    Многопоточное выполнение задачи (модуль threading).
    """
    print(f"Считаем сумму от 1 до {target_number} (THREADING, {num_tasks} потоков)...")
    start_time = time.time()
    
    step = target_number // num_tasks
    threads = []
    results = [0] * num_tasks 
    
    for i in range(num_tasks):
        start = i * step + 1
        end = (i + 1) * step if i != num_tasks - 1 else target_number
        
        thread = threading.Thread(target=calculate_sum, args=(start, end, results, i))
        threads.append(thread)
        thread.start()
        
    for thread in threads:
        thread.join()
            
    result = sum(results)
    elapsed = time.time() - start_time
    
    print(f"[Threading] Результат: {result}, Время: {elapsed:.4f} сек")
    return result, elapsed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Многопоточное вычисление суммы")
    parser.add_argument("-n", "--number", type=int, default=10**8, help="Целевое число")
    parser.add_argument("-w", "--workers", type=int, default=8, help="Количество потоков")
    args = parser.parse_args()
    
    run_threading(args.number, args.workers)