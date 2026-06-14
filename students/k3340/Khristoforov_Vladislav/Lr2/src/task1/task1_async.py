import time
import argparse
import asyncio

async def calculate_sum_async(start: int, end: int) -> int:
    """
    Асинхронная корутина вычисления суммы.
    """
    total = 0
    for i in range(start, end + 1):
        total += i
    return total

async def run_asyncio_logic(target_number: int, num_tasks: int):
    print(f"Считаем сумму от 1 до {target_number} (ASYNCIO, {num_tasks} корутин)...")
    start_time = time.time()
    
    step = target_number // num_tasks
    tasks = []
    
    for i in range(num_tasks):
        start = i * step + 1
        end = (i + 1) * step if i != num_tasks - 1 else target_number
        tasks.append(calculate_sum_async(start, end))
        
    results = await asyncio.gather(*tasks)
    
    total_result = sum(results)
    elapsed = time.time() - start_time
    print(f"[Asyncio] Результат: {total_result}, Время: {elapsed:.4f} сек")
    return total_result, elapsed

def run_asyncio(target_number: int, num_tasks: int):
    """Синхронная обертка для инициализации цикла событий (Event Loop)."""
    return asyncio.run(run_asyncio_logic(target_number, num_tasks))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Асинхронное вычисление суммы")
    parser.add_argument("-n", "--number", type=int, default=10**8, help="Целевое число")
    parser.add_argument("-w", "--workers", type=int, default=8, help="Количество корутин")
    args = parser.parse_args()
    
    run_asyncio(args.number, args.workers)